package com.rigcheck.app.data

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

// Pro is one entitlement per account, bought on Android or Web (#27). What a
// user sees is "Pro", "Free", or nothing yet; the one thing that must never
// happen is one account being shown another account's plan. RevenueCat is
// faked at its narrow interface, and every assertion is on what the user
// would see.
@OptIn(ExperimentalCoroutinesApi::class)
class AccountPlanTest {

    private val alice = Account(id = "11111111-aaaa", email = "alice@example.com")
    private val bob = Account(id = "22222222-bbbb", email = "bob@example.com")

    private class FakePlanSource : PlanSource {
        // Which accounts own Pro on RevenueCat's side, whichever platform bought it.
        val proAccounts = mutableSetOf<String>()

        // The account RevenueCat is logged in as; the real source answers for this one.
        var loggedInAs: String? = null
        var failure: Exception? = null
        var gate: CompletableDeferred<Unit>? = null
        var reads = 0

        override suspend fun isPro(): Boolean {
            reads++
            val account = loggedInAs
            gate?.await()
            failure?.let { throw it }
            return account in proAccounts
        }
    }

    private class Fixture(scope: TestScope, source: FakePlanSource = FakePlanSource()) {
        val source = source
        val accountState = MutableStateFlow<AccountState>(AccountState.Loading)
        val plan = AccountPlan(accountState, source, scope.backgroundScope)

        fun signIn(account: Account, billingLinked: Boolean = true) {
            source.loggedInAs = account.id
            accountState.value = AccountState.SignedIn(account, billingLinked)
        }

        fun signOut() {
            source.loggedInAs = null
            accountState.value = AccountState.SignedOut
        }
    }

    @Test
    fun `shows nothing until an account is signed in`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        assertEquals(null, f.plan.isPro.value)
    }

    @Test
    fun `an account that owns Pro, bought on another platform, shows as Pro on sign-in`() =
        runTest(UnconfinedTestDispatcher()) {
            val f = Fixture(this)
            f.source.proAccounts += alice.id

            f.signIn(alice)

            assertEquals(true, f.plan.isPro.value)
        }

    @Test
    fun `an account without Pro shows as Free, not as nothing`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        f.signIn(alice)

        assertEquals(false, f.plan.isPro.value)
    }

    @Test
    fun `waits for RevenueCat to know the account before reading its plan`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.source.proAccounts += alice.id

        f.signIn(alice, billingLinked = false)

        assertEquals(0, f.source.reads)
        assertEquals(null, f.plan.isPro.value)
    }

    @Test
    fun `reads again once billing is linked`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.source.proAccounts += alice.id
        f.signIn(alice, billingLinked = false)

        f.accountState.value = AccountState.SignedIn(alice, billingLinked = true)

        assertEquals(true, f.plan.isPro.value)
    }

    @Test
    fun `signing out clears the plan`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.source.proAccounts += alice.id
        f.signIn(alice)

        f.signOut()

        assertEquals(null, f.plan.isPro.value)
    }

    @Test
    fun `the next account never sees the previous account's plan, even while its own is loading`() =
        runTest(UnconfinedTestDispatcher()) {
            val f = Fixture(this)
            f.source.proAccounts += alice.id
            f.signIn(alice)
            f.source.gate = CompletableDeferred()

            f.signIn(bob)
            assertEquals(null, f.plan.isPro.value)

            f.source.gate!!.complete(Unit)
            assertEquals(false, f.plan.isPro.value)
        }

    @Test
    fun `a refresh that answers after its account has left is dropped`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.source.proAccounts += alice.id
        f.signIn(alice)
        f.source.gate = CompletableDeferred()
        f.plan.refresh()

        f.signOut()
        f.source.gate!!.complete(Unit)

        assertEquals(null, f.plan.isPro.value)
    }

    @Test
    fun `refresh picks up a Pro bought elsewhere while the app was open`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.signIn(alice)
        assertEquals(false, f.plan.isPro.value)

        f.source.proAccounts += alice.id
        f.plan.refresh()

        assertEquals(true, f.plan.isPro.value)
    }

    @Test
    fun `a failed read leaves the plan as it was`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.source.proAccounts += alice.id
        f.signIn(alice)

        f.source.failure = IllegalStateException("RevenueCat unreachable")
        f.plan.refresh()

        assertEquals(true, f.plan.isPro.value)
    }

    @Test
    fun `a failed first read leaves the plan unknown, never Free`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.source.failure = IllegalStateException("RevenueCat unreachable")

        f.signIn(alice)

        assertEquals(null, f.plan.isPro.value)
    }

    @Test
    fun `refresh does nothing while signed out`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        f.plan.refresh()

        assertEquals(0, f.source.reads)
    }
}
