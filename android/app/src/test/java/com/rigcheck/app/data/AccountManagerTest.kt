package com.rigcheck.app.data

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

// The account manager's one job: whichever Supabase account is signed in is
// the RevenueCat customer, so a purchase on any device lands on the shared
// account. Both outside services are faked at their narrow interfaces, and
// every assertion is on what a user (or RevenueCat) would observe.
@OptIn(ExperimentalCoroutinesApi::class)
class AccountManagerTest {

    private val alice = Account(id = "11111111-aaaa", email = "alice@example.com")
    private val bob = Account(id = "22222222-bbbb", email = "bob@example.com")

    private class FakeBackend : AccountBackend {
        val statusFlow = MutableStateFlow<BackendStatus>(BackendStatus.Initializing)
        override val status = statusFlow

        var token: String? = null
        var nextResult: AccountResult = AccountResult.Success
        val calls = mutableListOf<String>()

        override suspend fun signUp(email: String, password: String): AccountResult {
            calls += "signUp:$email"
            return nextResult
        }

        override suspend fun signIn(email: String, password: String): AccountResult {
            calls += "signIn:$email"
            return nextResult
        }

        override suspend fun signInWithGoogle(idToken: String, rawNonce: String): AccountResult {
            calls += "google:$idToken:$rawNonce"
            return nextResult
        }

        override suspend fun signInWithApple(): AccountResult {
            calls += "apple"
            return nextResult
        }

        override suspend fun requestPasswordReset(email: String): AccountResult {
            calls += "reset:$email"
            return nextResult
        }

        override suspend fun signOut(): AccountResult {
            calls += "signOut"
            statusFlow.value = BackendStatus.NotAuthenticated
            return nextResult
        }

        override suspend fun accessToken(): String? = token
    }

    private class FakeBilling : BillingIdentity {
        val calls = mutableListOf<String>()
        var failLogIn: Boolean = false

        override suspend fun logIn(accountId: String) {
            calls += "logIn:$accountId"
            if (failLogIn) throw IllegalStateException("RevenueCat unreachable")
        }

        override suspend fun logOut() {
            calls += "logOut"
        }
    }

    private class Fixture(scope: TestScope) {
        val backend = FakeBackend()
        val billing = FakeBilling()
        val manager = AccountManager(backend, billing, scope.backgroundScope)
    }

    @Test
    fun `is loading until the backend has finished restoring its session`() = runTest {
        val f = Fixture(this)

        assertEquals(AccountState.Loading, f.manager.state.value)
    }

    @Test
    fun `a restored session identifies the account to RevenueCat and signs in`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        f.backend.statusFlow.value = BackendStatus.Authenticated(alice)

        assertEquals(AccountState.SignedIn(alice, billingLinked = true), f.manager.state.value)
        assertEquals(listOf("logIn:${alice.id}"), f.billing.calls)
    }

    @Test
    fun `no session at launch is signed out and leaves RevenueCat anonymous`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)

        f.backend.statusFlow.value = BackendStatus.NotAuthenticated

        assertEquals(AccountState.SignedOut, f.manager.state.value)
        assertTrue("logOut on an already-anonymous RevenueCat user is an SDK error", f.billing.calls.isEmpty())
    }

    @Test
    fun `signing out returns RevenueCat to anonymous exactly once`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.Authenticated(alice)

        f.manager.signOut()

        assertEquals(AccountState.SignedOut, f.manager.state.value)
        assertEquals(listOf("logIn:${alice.id}", "logOut"), f.billing.calls)
    }

    @Test
    fun `a token refresh for the same account does not log in to RevenueCat again`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.Authenticated(alice)

        f.backend.statusFlow.value = BackendStatus.Authenticated(alice.copy())
        f.backend.statusFlow.value = BackendStatus.Authenticated(alice.copy(email = "alice@new.example"))

        assertEquals(listOf("logIn:${alice.id}"), f.billing.calls)
        assertEquals("alice@new.example", (f.manager.state.value as AccountState.SignedIn).account.email)
    }

    @Test
    fun `a different account replaces the previous one in RevenueCat`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.Authenticated(alice)

        f.backend.statusFlow.value = BackendStatus.Authenticated(bob)

        assertEquals(listOf("logIn:${alice.id}", "logIn:${bob.id}"), f.billing.calls)
        assertEquals(AccountState.SignedIn(bob, billingLinked = true), f.manager.state.value)
    }

    @Test
    fun `a failed RevenueCat login keeps the user signed in but not billing-linked, and retrying links it`() =
        runTest(UnconfinedTestDispatcher()) {
            val f = Fixture(this)
            f.billing.failLogIn = true

            f.backend.statusFlow.value = BackendStatus.Authenticated(alice)

            assertEquals(AccountState.SignedIn(alice, billingLinked = false), f.manager.state.value)

            f.billing.failLogIn = false
            val linked = f.manager.ensureBillingLinked()

            assertTrue(linked)
            assertEquals(AccountState.SignedIn(alice, billingLinked = true), f.manager.state.value)
        }

    @Test
    fun `ensureBillingLinked is false when signed out and does not touch RevenueCat`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.NotAuthenticated

        assertFalse(f.manager.ensureBillingLinked())
        assertTrue(f.billing.calls.isEmpty())
    }

    @Test
    fun `ensureBillingLinked stays false if RevenueCat is still unreachable`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.billing.failLogIn = true
        f.backend.statusFlow.value = BackendStatus.Authenticated(alice)

        assertFalse(f.manager.ensureBillingLinked())
        assertEquals(AccountState.SignedIn(alice, billingLinked = false), f.manager.state.value)
    }

    @Test
    fun `a failed sign-in surfaces the backend's message and leaves the user signed out`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.NotAuthenticated
        f.backend.nextResult = AccountResult.Failure("Invalid login credentials")

        val result = f.manager.signIn("alice@example.com", "wrong")

        assertEquals(AccountResult.Failure("Invalid login credentials"), result)
        assertEquals(AccountState.SignedOut, f.manager.state.value)
        assertTrue(f.billing.calls.isEmpty())
    }

    @Test
    fun `sign-up that needs email confirmation is reported as such and does not sign in`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.NotAuthenticated
        f.backend.nextResult = AccountResult.NeedsConfirmation

        val result = f.manager.signUp("new@example.com", "hunter22")

        assertEquals(AccountResult.NeedsConfirmation, result)
        assertEquals(AccountState.SignedOut, f.manager.state.value)
    }

    @Test
    fun `email, Google and Apple sign-in each reach the backend with their inputs`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.NotAuthenticated

        f.manager.signIn("a@example.com", "pw")
        f.manager.signUp("b@example.com", "pw")
        f.manager.signInWithGoogle(idToken = "google-id-token", rawNonce = "raw-nonce")
        f.manager.signInWithApple()

        assertEquals(
            listOf("signIn:a@example.com", "signUp:b@example.com", "google:google-id-token:raw-nonce", "apple"),
            f.backend.calls,
        )
    }

    @Test
    fun `an exception thrown by the backend becomes a failure, not a crash`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        val throwing = object : AccountBackend by f.backend {
            override suspend fun signIn(email: String, password: String): AccountResult =
                throw java.io.IOException("offline")
        }
        val manager = AccountManager(throwing, f.billing, backgroundScope)

        val result = manager.signIn("a@example.com", "pw")

        assertEquals(AccountResult.Failure("offline"), result)
    }

    @Test
    fun `password reset and the access token pass through to the backend`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.token = "jwt-abc"

        f.manager.requestPasswordReset("a@example.com")

        assertEquals(listOf("reset:a@example.com"), f.backend.calls)
        assertEquals("jwt-abc", f.manager.accessToken())
    }

    @Test
    fun `state reflects the sign-in order the user performs end to end`() = runTest(UnconfinedTestDispatcher()) {
        val f = Fixture(this)
        f.backend.statusFlow.value = BackendStatus.NotAuthenticated
        assertEquals(AccountState.SignedOut, f.manager.state.first())

        f.backend.statusFlow.value = BackendStatus.Authenticated(alice)
        assertEquals(AccountState.SignedIn(alice, billingLinked = true), f.manager.state.first())

        f.manager.signOut()
        assertEquals(AccountState.SignedOut, f.manager.state.first())
    }
}
