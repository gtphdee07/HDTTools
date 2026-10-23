package com.rigcheck.app.data

import com.rigcheck.app.domain.VerdictStatus
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// History is the signed-in account's past checks, the same on every device, with the plan's cap enforced by the
// server (ADR-0005). What a user sees: checks made on Web are here, a check made here is there, only the newest
// few are kept, and a flaky connection never records a check twice. The server (Supabase's add_history_entry) is
// faked with its documented behaviour: newest first, the cap by plan (an unknown plan gets the Pro count, so a
// failed plan read never prunes), and one entry per idempotency key.
@OptIn(ExperimentalCoroutinesApi::class)
class HistoryTest {

    private val alice = Account(id = "11111111-aaaa", email = "alice@example.com")
    private val bob = Account(id = "22222222-bbbb", email = "bob@example.com")

    private class FakeServer(val freeCap: Int = 2, val proCap: Int = 4) {
        // Each account's entries, newest first.
        val histories = mutableMapOf<String, MutableList<HistoryEntry>>()
        val keys = mutableMapOf<String, MutableSet<String>>()
        private var nextId = 1

        fun seed(account: Account, nickname: String, verdict: VerdictStatus = VerdictStatus.PASS) {
            histories.getOrPut(account.id) { mutableListOf() }
                .add(0, HistoryEntry("seed-${nextId++}", "2026-10-20T00:00:00Z", nickname, verdict))
        }

        fun nicknames(account: Account) = histories[account.id].orEmpty().map { it.rigNickname }

        fun add(account: String, key: String, nickname: String, verdict: VerdictStatus, isPro: Boolean?) {
            val seen = keys.getOrPut(account) { mutableSetOf() }
            if (!seen.add(key)) return
            val history = histories.getOrPut(account) { mutableListOf() }
            history.add(0, HistoryEntry("entry-${nextId++}", "2026-10-22T00:00:00Z", nickname, verdict))
            val cap = if (isPro == false) freeCap else proCap
            while (history.size > cap) history.removeAt(history.lastIndex)
        }
    }

    private class FakeBackend(val server: FakeServer, val account: () -> String?) : HistoryBackend {
        var listFailure: Exception? = null
        var addFailures = 0 // the next N adds are lost on the way and fail without reaching the server
        var addRepliesLost = 0 // the next N adds reach the server, but the reply is lost
        var capsFailure: Exception? = null
        var listGate: CompletableDeferred<Unit>? = null
        val addKeys = mutableListOf<String>()
        val addPlans = mutableListOf<Boolean?>()
        var lists = 0

        override suspend fun list(): List<HistoryEntry> {
            lists++
            val forAccount = account() ?: error("not signed in")
            val snapshot = server.histories[forAccount].orEmpty().toList()
            listGate?.await()
            listFailure?.let { throw it }
            return snapshot
        }

        override suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?) {
            addKeys += idempotencyKey
            addPlans += isPro
            if (addFailures > 0) {
                addFailures--
                throw java.io.IOException("connection lost")
            }
            server.add(account() ?: error("not signed in"), idempotencyKey, rigNickname, verdict, isPro)
            if (addRepliesLost > 0) {
                addRepliesLost--
                throw java.io.IOException("reply lost")
            }
        }

        override suspend fun caps(): HistoryCaps {
            capsFailure?.let { throw it }
            return HistoryCaps(server.freeCap, server.proCap)
        }
    }

    private class Fixture(scope: TestScope, freeCap: Int = 2, proCap: Int = 4) {
        val server = FakeServer(freeCap, proCap)
        val accountState = MutableStateFlow<AccountState>(AccountState.SignedOut)
        val plan = MutableStateFlow<Boolean?>(false)
        private var signedInAs: String? = null
        val backend = FakeBackend(server) { signedInAs }
        private var keyCount = 0
        val history = History(
            accountState = accountState,
            backend = backend,
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

        fun nicknames() = history.entries.value.map { it.rigNickname }
    }

    // --- Reading --------------------------------------------------------------------------------------

    @Test
    fun `checks made on another device are here after signing in, newest first`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Older")
        f.server.seed(alice, "Newer", VerdictStatus.FAIL)

        f.signIn(alice)

        assertEquals(listOf("Newer", "Older"), f.nicknames())
        assertEquals(VerdictStatus.FAIL, f.history.entries.value.first().verdict)
    }

    @Test
    fun `a check made on Web after sign-in shows up on refresh`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)
        assertEquals(emptyList<String>(), f.nicknames())

        f.server.seed(alice, "Made on Web")
        f.history.refresh()

        assertEquals(listOf("Made on Web"), f.nicknames())
    }

    @Test
    fun `the next account never sees the previous one's checks`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Alice's rig")
        f.server.seed(bob, "Bob's rig")

        f.signIn(alice)
        f.signOut()
        f.signIn(bob)

        assertEquals(listOf("Bob's rig"), f.nicknames())
    }

    @Test
    fun `a read that answers after sign-out is dropped`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Alice's rig")
        f.backend.listGate = CompletableDeferred()

        f.signIn(alice)
        f.signOut()
        f.backend.listGate!!.complete(Unit)

        assertEquals(emptyList<String>(), f.nicknames())
    }

    @Test
    fun `a refresh that answers after sign-out is dropped`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Alice's rig")
        f.signIn(alice)
        f.backend.listGate = CompletableDeferred()

        f.history.refresh()
        f.signOut()
        f.backend.listGate!!.complete(Unit)

        assertEquals(emptyList<String>(), f.nicknames())
    }

    @Test
    fun `a read that fails keeps what is shown`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Kept")
        f.signIn(alice)

        f.backend.listFailure = java.io.IOException("offline")
        f.history.refresh()

        assertEquals(listOf("Kept"), f.nicknames())
    }

    // --- Signed out -----------------------------------------------------------------------------------

    @Test
    fun `signed out, a check lasts for the session and nothing is sent to the account`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        val saved = f.history.recordCheck("Visitor rig", VerdictStatus.PASS)

        assertTrue(saved)
        assertEquals(listOf("Visitor rig"), f.nicknames())
        assertEquals(emptyList<String>(), f.backend.addKeys)
    }

    @Test
    fun `signing in swaps to the account's checks and signing out brings the session's back`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "In the account")
        f.history.recordCheck("Visitor rig", VerdictStatus.PASS)

        f.signIn(alice)
        assertEquals(listOf("In the account"), f.nicknames())

        f.signOut()
        assertEquals(listOf("Visitor rig"), f.nicknames())
        assertEquals(listOf("In the account"), f.server.nicknames(alice))
    }

    // --- Recording ------------------------------------------------------------------------------------

    @Test
    fun `a check made here is saved to the account and listed`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)

        val saved = f.history.recordCheck("  Big Blue ", VerdictStatus.PARTIAL)

        assertTrue(saved)
        assertEquals(listOf("Big Blue"), f.server.nicknames(alice))
        assertEquals(listOf("Big Blue"), f.nicknames())
        assertEquals(VerdictStatus.PARTIAL, f.history.entries.value.single().verdict)
    }

    @Test
    fun `only the newest checks are kept and the oldest drops off, as on Web`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 2)
        f.signIn(alice)

        f.history.recordCheck("One", VerdictStatus.PASS)
        f.history.recordCheck("Two", VerdictStatus.PASS)
        f.history.recordCheck("Three", VerdictStatus.PASS)

        assertEquals(listOf("Three", "Two"), f.nicknames())
    }

    @Test
    fun `a Pro account keeps the Pro count`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 2, proCap = 4)
        f.plan.value = true
        f.signIn(alice)

        listOf("One", "Two", "Three", "Four", "Five").forEach { f.history.recordCheck(it, VerdictStatus.PASS) }

        assertEquals(listOf("Five", "Four", "Three", "Two"), f.nicknames())
    }

    @Test
    fun `the Pro, Free and unknown plan reach add_history_entry as true, false and null`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)

        f.plan.value = true
        f.history.recordCheck("A", VerdictStatus.PASS)
        f.plan.value = false
        f.history.recordCheck("B", VerdictStatus.PASS)
        f.plan.value = null
        f.history.recordCheck("C", VerdictStatus.PASS)

        assertEquals(listOf<Boolean?>(true, false, null), f.backend.addPlans)
    }

    @Test
    fun `a plan that could not be read does not prune a Pro account's History`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 2, proCap = 4)
        f.plan.value = null
        f.signIn(alice)

        listOf("One", "Two", "Three").forEach { f.history.recordCheck(it, VerdictStatus.PASS) }

        assertEquals(3, f.server.nicknames(alice).size)
    }

    @Test
    fun `a retried add carries one key and records one check, even when the first reply was lost`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)
        f.backend.addRepliesLost = 1

        val saved = f.history.recordCheck("Big Blue", VerdictStatus.PASS)

        assertTrue(saved)
        assertEquals(listOf("key-1", "key-1"), f.backend.addKeys)
        assertEquals(listOf("Big Blue"), f.server.nicknames(alice))
    }

    @Test
    fun `an add that fails twice says the check was not saved, and the list is unchanged`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Kept")
        f.signIn(alice)
        f.backend.addFailures = 2

        val saved = f.history.recordCheck("Lost", VerdictStatus.PASS)

        assertFalse(saved)
        assertEquals(2, f.backend.addKeys.size)
        assertEquals(listOf("Kept"), f.nicknames())
    }

    @Test
    fun `two checks get two keys`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)

        f.history.recordCheck("One", VerdictStatus.PASS)
        f.history.recordCheck("Two", VerdictStatus.PASS)

        assertEquals(listOf("key-1", "key-2"), f.backend.addKeys)
    }

    // --- Caps -----------------------------------------------------------------------------------------

    @Test
    fun `the caps are read once signed in and gone once signed out`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this, freeCap = 7, proCap = 70)
        assertNull(f.history.caps.value)

        f.signIn(alice)
        assertEquals(HistoryCaps(7, 70), f.history.caps.value)

        f.signOut()
        assertNull(f.history.caps.value)
    }

    @Test
    fun `caps that cannot be read leave the checks listed`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.server.seed(alice, "Still here")
        f.backend.capsFailure = java.io.IOException("offline")

        f.signIn(alice)

        assertNull(f.history.caps.value)
        assertEquals(listOf("Still here"), f.nicknames())
    }
}
