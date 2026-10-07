package com.rigcheck.app.data

import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

// The shared RigCheck account (Supabase Auth, ADR-0004). `id` is the
// Supabase user id - also the RevenueCat app user id, so a purchase on any
// device or platform lands on the same customer (ADR-0003).
data class Account(val id: String, val email: String?)

sealed interface AccountState {
    // The backend hasn't finished restoring a stored session yet.
    data object Loading : AccountState
    data object SignedOut : AccountState

    // billingLinked is false when the account is signed in but RevenueCat
    // couldn't be told about it (e.g. offline) - purchases must not proceed
    // until ensureBillingLinked() succeeds, or they'd land on the wrong
    // RevenueCat customer.
    data class SignedIn(val account: Account, val billingLinked: Boolean) : AccountState
}

sealed interface AccountResult {
    data object Success : AccountResult

    // Sign-up worked but the account must be confirmed by email before it
    // can sign in.
    data object NeedsConfirmation : AccountResult

    // The user backed out of a provider's chooser; nothing to report.
    data object Cancelled : AccountResult
    data class Failure(val message: String) : AccountResult
}

sealed interface BackendStatus {
    data object Initializing : BackendStatus
    data object NotAuthenticated : BackendStatus
    data class Authenticated(val account: Account) : BackendStatus
}

// The slice of Supabase Auth this app uses - narrow so tests can fake it.
interface AccountBackend {
    val status: Flow<BackendStatus>
    suspend fun signUp(email: String, password: String): AccountResult
    suspend fun signIn(email: String, password: String): AccountResult

    // idToken from Google's Credential Manager; rawNonce is the un-hashed
    // nonce whose SHA-256 was put in the Google request.
    suspend fun signInWithGoogle(idToken: String, rawNonce: String): AccountResult

    // Opens Apple's OAuth page in a browser tab; the session arrives later
    // through `status` once the deep link returns.
    suspend fun signInWithApple(): AccountResult
    suspend fun requestPasswordReset(email: String): AccountResult

    // Signs out this device only - other devices on the account stay signed in.
    suspend fun signOut(): AccountResult
    suspend fun accessToken(): String?
}

// The slice of RevenueCat that identifies the customer.
interface BillingIdentity {
    suspend fun logIn(accountId: String)
    suspend fun logOut()
}

// Keeps RevenueCat's customer in step with the signed-in account.
class AccountManager(
    private val backend: AccountBackend,
    private val billing: BillingIdentity,
    scope: CoroutineScope,
) {
    private val _state = MutableStateFlow<AccountState>(AccountState.Loading)
    val state: StateFlow<AccountState> = _state

    // The account id RevenueCat currently knows; null = still anonymous.
    private var billingAccountId: String? = null
    private val lock = Mutex()

    init {
        scope.launch {
            backend.status.collect { status ->
                lock.withLock { apply(status) }
            }
        }
    }

    private suspend fun apply(status: BackendStatus) {
        when (status) {
            BackendStatus.Initializing -> Unit
            BackendStatus.NotAuthenticated -> {
                // logOut on an anonymous RevenueCat user is an SDK error, so
                // only call it when we actually logged an account in.
                if (billingAccountId != null) {
                    runCatching { billing.logOut() }
                    billingAccountId = null
                }
                _state.value = AccountState.SignedOut
            }
            is BackendStatus.Authenticated -> {
                val account = status.account
                if (billingAccountId != account.id) linkBilling(account.id)
                _state.value = AccountState.SignedIn(account, billingLinked = billingAccountId == account.id)
            }
        }
    }

    private suspend fun linkBilling(accountId: String) {
        try {
            billing.logIn(accountId)
            billingAccountId = accountId
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            billingAccountId = null
        }
    }

    // True once purchases are safe to make for the signed-in account;
    // retries the RevenueCat login if an earlier attempt failed.
    suspend fun ensureBillingLinked(): Boolean = lock.withLock {
        val current = _state.value as? AccountState.SignedIn ?: return@withLock false
        if (billingAccountId != current.account.id) linkBilling(current.account.id)
        val linked = billingAccountId == current.account.id
        _state.value = current.copy(billingLinked = linked)
        linked
    }

    suspend fun accessToken(): String? = backend.accessToken()

    suspend fun signUp(email: String, password: String) = guarded { backend.signUp(email, password) }
    suspend fun signIn(email: String, password: String) = guarded { backend.signIn(email, password) }
    suspend fun signInWithGoogle(idToken: String, rawNonce: String) =
        guarded { backend.signInWithGoogle(idToken, rawNonce) }

    suspend fun signInWithApple() = guarded { backend.signInWithApple() }
    suspend fun requestPasswordReset(email: String) = guarded { backend.requestPasswordReset(email) }
    suspend fun signOut() = guarded { backend.signOut() }

    private suspend fun guarded(block: suspend () -> AccountResult): AccountResult = try {
        block()
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        AccountResult.Failure(e.message ?: "Something went wrong.")
    }
}
