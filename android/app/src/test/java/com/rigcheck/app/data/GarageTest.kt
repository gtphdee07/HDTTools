package com.rigcheck.app.data

import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

// The Garage is the signed-in account's saved Rigs, the same on every device, with the plan's cap enforced by
// the server (ADR-0005). What a user sees: the Rigs they saved on another device are here, a Rig saved here is
// there, a full Garage says so and the check still goes ahead, and a flaky connection never saves a Rig twice.
// The server (Supabase's add_rig) is faked with its documented behaviour: the cap by plan, one Rig per
// nickname, and one Rig per idempotency key.
@OptIn(ExperimentalCoroutinesApi::class)
class GarageTest {

    private val alice = Account(id = "11111111-aaaa", email = "alice@example.com")
    private val bob = Account(id = "22222222-bbbb", email = "bob@example.com")
    private val truck = TruckTag(description = "F-450", gvwrLb = 14_000.0)
    private val trailer = TrailerTag(description = "Brinkley", gvwrLb = 16_000.0)

    private fun rig(nickname: String, lastUsedAt: String = "2026-10-01T00:00:00Z", id: String? = null) =
        RecentRig(nickname = nickname, truck = truck, trailer = trailer, lastUsedAt = lastUsedAt, id = id)

    // The account Garages on the server, by account id.
    private class FakeServer(val freeCap: Int = 2, val proCap: Int = 4) {
        val garages = mutableMapOf<String, MutableList<RecentRig>>()
        val keys = mutableMapOf<String, MutableMap<String, String>>() // account -> key -> rig id
        private var nextId = 1

        fun seed(account: Account, vararg rigs: RecentRig) {
            garages.getOrPut(account.id) { mutableListOf() }
                .addAll(rigs.map { it.copy(id = it.id ?: "seed-${nextId++}") })
        }

        fun nicknames(account: Account) = garages[account.id].orEmpty().map { it.nickname }

        fun add(account: String, key: String, rig: RecentRig, isPro: Boolean?) {
            val garage = garages.getOrPut(account) { mutableListOf() }
            val seen = keys.getOrPut(account) { mutableMapOf() }
            if (key in seen) return
            val sameName = garage.indexOfFirst { it.nickname.trim().lowercase() == rig.nickname.trim().lowercase() }
            if (sameName >= 0) {
                garage[sameName] = garage[sameName].copy(truck = rig.truck, trailer = rig.trailer, lastUsedAt = rig.lastUsedAt)
                return
            }
            val cap = if (isPro == true) proCap else freeCap
            if (garage.size >= cap) throw GarageFullException(cap)
            val id = "rig-${nextId++}"
            garage.add(rig.copy(id = id))
            seen[key] = id
        }
    }

    private class FakeBackend(val server: FakeServer, val account: () -> String?) : GarageBackend {
        var listFailure: Exception? = null
        var addFailures = 0 // the next N adds are lost on the way and fail without reaching the server
        var addRepliesLost = 0 // the next N adds reach the server, but the reply is lost
        var updateFailure: Exception? = null
        var listGate: CompletableDeferred<Unit>? = null
        val addKeys = mutableListOf<String>()
        val addPlans = mutableListOf<Boolean?>()
        var lists = 0

        override suspend fun list(): List<RecentRig> {
            lists++
            val forAccount = account() ?: error("not signed in")
            val snapshot = server.garages[forAccount].orEmpty().sortedByDescending { it.lastUsedAt }
            listGate?.await()
            listFailure?.let { throw it }
            return snapshot
        }

        override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) {
            addKeys += idempotencyKey
            addPlans += isPro
            if (addFailures > 0) {
                addFailures--
                throw java.io.IOException("connection lost")
            }
            server.add(account() ?: error("not signed in"), idempotencyKey, rig, isPro)
            if (addRepliesLost > 0) {
                addRepliesLost--
                throw java.io.IOException("reply lost")
            }
        }

        override suspend fun updateRig(rig: RecentRig) {
            updateFailure?.let { throw it }
            val garage = server.garages.getValue(account() ?: error("not signed in"))
            val at = garage.indexOfFirst { it.id == rig.id }
            if (at < 0) throw IllegalStateException("rig_not_found")
            garage[at] = rig
        }
    }

    private class FakeLocalRigs : LocalRigs {
        private val stored = MutableStateFlow<List<RecentRig>>(emptyList())
        override val recentRigs: Flow<List<RecentRig>> = stored
        val saves = mutableListOf<String>()

        override suspend fun saveRecentRig(nickname: String, truck: TruckTag, trailer: TrailerTag): List<RecentRig> {
            saves += nickname
            stored.value = listOf(RecentRig(nickname, truck, trailer, "2026-10-02T00:00:00Z")) + stored.value
            return stored.value
        }

        fun seed(vararg rigs: RecentRig) {
            stored.value = rigs.toList()
        }
    }

    private class Fixture(scope: TestScope, freeCap: Int = 2, proCap: Int = 4) {
        val server = FakeServer(freeCap, proCap)
        val accountState = MutableStateFlow<AccountState>(AccountState.SignedOut)
        val plan = MutableStateFlow<Boolean?>(false)
        val local = FakeLocalRigs()
        private var signedInAs: String? = null
        val backend = FakeBackend(server) { signedInAs }
        private var keyCount = 0
        val garage = Garage(
            accountState = accountState,
            backend = backend,
            local = local,
            isPro = { plan.value },
            scope = scope.backgroundScope,
            newKey = { "key-${++keyCount}" },
            now = { "2026-10-22T00:00:00Z" },
        )

        fun signIn(account: Account) {
            signedInAs = account.id
            accountState.value = AccountState.SignedIn(account, billingLinked = true)
        }

        fun signOut() {
            signedInAs = null
            accountState.value = AccountState.SignedOut
        }
    }

    // --- Reading --------------------------------------------------------------------------------------

    @Test
    fun `a Rig saved on another device is here after signing in`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, rig("Goose + Addie"))

        f.signIn(alice)

        assertEquals(listOf("Goose + Addie"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `the most recently used Rig comes first`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, rig("Old", "2026-09-01T00:00:00Z"), rig("New", "2026-10-15T00:00:00Z"))

        f.signIn(alice)

        assertEquals(listOf("New", "Old"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `a Rig added on Web after sign-in shows up on refresh`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)
        assertEquals(emptyList<String>(), f.garage.rigs.value.map { it.nickname })

        f.server.seed(alice, rig("Added on Web"))
        f.garage.refresh()

        assertEquals(listOf("Added on Web"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `signed out, the Garage is the Rigs kept on this phone`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.local.seed(rig("On this phone"))

        assertEquals(listOf("On this phone"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `signed in, the Rigs kept on this phone are not mixed into the account's`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.local.seed(rig("On this phone"))
        f.server.seed(alice, rig("In the account"))

        f.signIn(alice)

        assertEquals(listOf("In the account"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `signing out goes back to this phone's Rigs and never shows the account's`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.local.seed(rig("On this phone"))
        f.server.seed(alice, rig("In the account"))
        f.signIn(alice)

        f.signOut()

        assertEquals(listOf("On this phone"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `the next account never sees the previous account's Rigs, not even while its own load`() =
        runTest(UnconfinedTestDispatcher()) {
            val f = Fixture(this)
            f.server.seed(alice, rig("Alice's"))
            f.server.seed(bob, rig("Bob's"))
            f.signIn(alice)
            f.backend.listGate = CompletableDeferred()

            f.signIn(bob)

            assertEquals(emptyList<String>(), f.garage.rigs.value.map { it.nickname })
            f.backend.listGate!!.complete(Unit)
            assertEquals(listOf("Bob's"), f.garage.rigs.value.map { it.nickname })
        }

    @Test
    fun `an answer for an account that has since signed out is dropped`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.local.seed(rig("On this phone"))
        f.server.seed(alice, rig("In the account"))
        f.backend.listGate = CompletableDeferred()
        f.signIn(alice)

        f.signOut()
        f.backend.listGate!!.complete(Unit)

        assertEquals(listOf("On this phone"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `an older refresh that answers late does not overwrite a newer list`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, rig("Before"))
        f.signIn(alice)
        val slow = CompletableDeferred<Unit>()
        f.backend.listGate = slow
        f.garage.refresh() // reads "Before" and waits
        f.server.seed(alice, rig("After"))
        f.backend.listGate = null
        f.garage.refresh() // reads both at once

        slow.complete(Unit)

        assertEquals(setOf("Before", "After"), f.garage.rigs.value.map { it.nickname }.toSet())
    }

    @Test
    fun `a failed read keeps what is shown`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, rig("Goose"))
        f.signIn(alice)

        f.backend.listFailure = java.io.IOException("offline")
        f.garage.refresh()

        assertEquals(listOf("Goose"), f.garage.rigs.value.map { it.nickname })
    }

    // --- Saving ---------------------------------------------------------------------------------------

    @Test
    fun `a new Rig is saved to the account and shows in the Garage`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)

        val outcome = f.garage.saveRig("Goose", truck, trailer)

        assertEquals(SaveRigOutcome.Saved, outcome)
        assertEquals(listOf("Goose"), f.server.nicknames(alice))
        assertEquals(listOf("Goose"), f.garage.rigs.value.map { it.nickname })
        assertEquals(emptyList<String>(), f.local.saves)
    }

    @Test
    fun `signed out, a Rig is kept on this phone and the account is not touched`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        val outcome = f.garage.saveRig("Goose", truck, trailer)

        assertEquals(SaveRigOutcome.Saved, outcome)
        assertEquals(listOf("Goose"), f.local.saves)
        assertEquals(emptyList<String>(), f.backend.addKeys)
    }

    @Test
    fun `a Rig saved on Android is in the account that Web reads`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)

        f.garage.saveRig("Goose", truck, trailer)

        val stored = f.server.garages.getValue(alice.id).single()
        assertEquals(truck, stored.truck)
        assertEquals(trailer, stored.trailer)
    }

    @Test
    fun `a request retried after a lost connection creates one Rig`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)
        f.backend.addFailures = 1

        val outcome = f.garage.saveRig("Goose", truck, trailer)

        assertEquals(SaveRigOutcome.Saved, outcome)
        assertEquals(listOf("Goose"), f.server.nicknames(alice))
        assertEquals(2, f.backend.addKeys.size)
        assertEquals("both attempts carry the same idempotency key", 1, f.backend.addKeys.toSet().size)
    }

    @Test
    fun `an add that landed but whose reply was lost is not counted twice, even at the cap`() =
        runTest(UnconfinedTestDispatcher()) {
            val f = Fixture(this, freeCap = 1)
            f.signIn(alice)
            f.backend.addRepliesLost = 1

            val outcome = f.garage.saveRig("Goose", truck, trailer)

            assertEquals("the retry finds the first add, not a full Garage", SaveRigOutcome.Saved, outcome)
            assertEquals(listOf("Goose"), f.server.nicknames(alice))
        }

    @Test
    fun `two separate saves use two separate keys`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)

        f.garage.saveRig("Goose", truck, trailer)
        f.garage.saveRig("Addie", truck, trailer)

        assertEquals(2, f.backend.addKeys.toSet().size)
    }

    @Test
    fun `a connection that stays down fails the save and says so`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)
        f.backend.addFailures = 2

        val outcome = f.garage.saveRig("Goose", truck, trailer)

        assertEquals(SaveRigOutcome.Failed, outcome)
        assertEquals(emptyList<String>(), f.server.nicknames(alice))
    }

    // --- The cap --------------------------------------------------------------------------------------

    @Test
    fun `a full Garage refuses the next Rig and names the cap`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 2)
        f.server.seed(alice, rig("One"), rig("Two"))
        f.signIn(alice)

        val outcome = f.garage.saveRig("Three", truck, trailer)

        assertEquals(SaveRigOutcome.Full(cap = 2), outcome)
        assertEquals(listOf("One", "Two"), f.server.nicknames(alice))
    }

    @Test
    fun `a full Garage is an answer, so the add is not retried`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 1)
        f.server.seed(alice, rig("One"))
        f.signIn(alice)

        f.garage.saveRig("Two", truck, trailer)

        assertEquals(1, f.backend.addKeys.size)
    }

    @Test
    fun `a Rig already in a full Garage is used again, updating it, not added`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 2)
        f.server.seed(alice, rig("One"), rig("Two"))
        f.signIn(alice)
        val newTruck = truck.copy(gvwrLb = 15_000.0)

        val outcome = f.garage.saveRig("two", newTruck, trailer) // a different letter case is the same Rig

        assertEquals(SaveRigOutcome.Saved, outcome)
        assertEquals(emptyList<String>(), f.backend.addKeys)
        assertEquals(listOf("One", "Two"), f.server.nicknames(alice))
        val updated = f.server.garages.getValue(alice.id).first { it.nickname == "Two" }
        assertEquals(newTruck, updated.truck)
        assertEquals("2026-10-22T00:00:00Z", updated.lastUsedAt)
    }

    @Test
    fun `using a Rig moves it to the front of the Garage`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, rig("Old", "2026-09-01T00:00:00Z"), rig("Newer", "2026-10-15T00:00:00Z"))
        f.signIn(alice)

        f.garage.saveRig("Old", truck, trailer)

        assertEquals(listOf("Old", "Newer"), f.garage.rigs.value.map { it.nickname })
    }

    @Test
    fun `a Rig deleted on another device since the list was read is added back, not lost`() =
        runTest(UnconfinedTestDispatcher()) {
            val f = Fixture(this)
            f.server.seed(alice, rig("Goose"))
            f.signIn(alice)
            f.server.garages.getValue(alice.id).clear() // removed elsewhere; this phone still lists it

            val outcome = f.garage.saveRig("Goose", truck, trailer)

            assertEquals(SaveRigOutcome.Saved, outcome)
            assertEquals(listOf("Goose"), f.server.nicknames(alice))
        }

    @Test
    fun `a Pro account's save asks for the Pro cap`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 1, proCap = 3)
        f.plan.value = true
        f.server.seed(alice, rig("One"))
        f.signIn(alice)

        val outcome = f.garage.saveRig("Two", truck, trailer)

        assertEquals(SaveRigOutcome.Saved, outcome)
        assertEquals(listOf(true), f.backend.addPlans)
    }

    @Test
    fun `a Free account's save asks for the Free cap`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 1, proCap = 3)
        f.server.seed(alice, rig("One"))
        f.signIn(alice)

        val outcome = f.garage.saveRig("Two", truck, trailer)

        assertEquals(SaveRigOutcome.Full(cap = 1), outcome)
        assertEquals(listOf<Boolean?>(false), f.backend.addPlans)
    }

    @Test
    fun `when the plan cannot be read the save says so and gets the Free cap`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 1, proCap = 3)
        f.plan.value = null
        f.server.seed(alice, rig("One"))
        f.signIn(alice)

        val outcome = f.garage.saveRig("Two", truck, trailer)

        assertEquals(SaveRigOutcome.Full(cap = 1), outcome)
        assertEquals(listOf<Boolean?>(null), f.backend.addPlans)
    }

    // --- Keeping what Web saved -------------------------------------------------------------------------

    @Test
    fun `using a Rig that Web saved keeps the fields only Web keeps`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        val vin = kotlinx.serialization.json.JsonPrimitive("1FT8W4DT0NEC00000")
        f.server.seed(
            alice,
            rig("Goose").copy(truckExtra = kotlinx.serialization.json.JsonObject(mapOf("vin" to vin))),
        )
        f.signIn(alice)

        f.garage.saveRig("Goose", truck.copy(gvwrLb = 14_500.0), trailer)

        val stored = f.server.garages.getValue(alice.id).single()
        assertEquals(vin, stored.truckExtra["vin"])
        assertEquals(14_500.0, stored.truck.gvwrLb)
    }
}
