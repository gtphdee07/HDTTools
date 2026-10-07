package com.rigcheck.app.data

import android.content.Intent
import io.github.jan.supabase.SupabaseClient
import io.github.jan.supabase.auth.Auth
import io.github.jan.supabase.auth.FlowType
import io.github.jan.supabase.auth.SignOutScope
import io.github.jan.supabase.auth.auth
import io.github.jan.supabase.auth.handleDeeplinks
import io.github.jan.supabase.auth.providers.Apple
import io.github.jan.supabase.auth.providers.Google
import io.github.jan.supabase.auth.providers.builtin.Email
import io.github.jan.supabase.auth.providers.builtin.IDToken
import io.github.jan.supabase.auth.status.SessionStatus
import io.github.jan.supabase.auth.user.UserInfo
import io.github.jan.supabase.createSupabaseClient
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map

// Both values ship in the app by design, like the Web build's
// web/.env.production: the publishable key only identifies the project, and
// row-level rules plus the signed-in session are what protect data. Never
// put the service-role key or any test credentials here.
internal const val SUPABASE_URL = "https://lifginpapkevreyrzzex.supabase.co"
internal const val SUPABASE_PUBLISHABLE_KEY = "sb_publishable_Aph46sKPDsU90ZLFqo2Q5Q_m46x4R-Z"

// The custom-URL-scheme the Apple (browser) sign-in returns to. Must match
// the intent-filter on MainActivity in AndroidManifest.xml and be on
// Supabase's redirect-URL allow list (see scripts/wizard_android_sign_in.sh).
const val AUTH_REDIRECT_SCHEME = "rigcheck"
internal const val AUTH_REDIRECT_HOST = "login"

// Where the password-reset email link lands: the Web app, which already
// handles the recovery step (web/src/auth.tsx), so the phone needs no
// deep-link handler for it.
private const val PASSWORD_RESET_REDIRECT = "https://rigcheck-web.pages.dev"

class SupabaseAccountBackend private constructor(private val client: SupabaseClient) : AccountBackend {

    override val status: Flow<BackendStatus> = client.auth.sessionStatus.map { status ->
        when (status) {
            is SessionStatus.Initializing -> BackendStatus.Initializing
            is SessionStatus.Authenticated -> authenticatedOrNot(status.session.user)
            is SessionStatus.NotAuthenticated -> BackendStatus.NotAuthenticated
            // A failed token refresh (offline at launch) keeps the stored
            // session; stay signed in rather than looking signed out.
            is SessionStatus.RefreshFailure -> authenticatedOrNot(client.auth.currentUserOrNull())
        }
    }

    private fun authenticatedOrNot(user: UserInfo?): BackendStatus =
        user?.let { BackendStatus.Authenticated(Account(it.id, it.email)) } ?: BackendStatus.NotAuthenticated

    override suspend fun signUp(email: String, password: String): AccountResult {
        client.auth.signUpWith(Email) {
            this.email = email
            this.password = password
        }
        // With email confirmation on, sign-up creates the user but no session.
        return if (client.auth.currentSessionOrNull() != null) AccountResult.Success else AccountResult.NeedsConfirmation
    }

    override suspend fun signIn(email: String, password: String): AccountResult {
        client.auth.signInWith(Email) {
            this.email = email
            this.password = password
        }
        return AccountResult.Success
    }

    override suspend fun signInWithGoogle(idToken: String, rawNonce: String): AccountResult {
        client.auth.signInWith(IDToken) {
            this.idToken = idToken
            provider = Google
            nonce = rawNonce
        }
        return AccountResult.Success
    }

    // Returns once the browser tab is launched; the session itself arrives
    // through `status` after MainActivity hands the redirect to handleDeepLink.
    override suspend fun signInWithApple(): AccountResult {
        client.auth.signInWith(Apple)
        return AccountResult.Success
    }

    override suspend fun requestPasswordReset(email: String): AccountResult {
        client.auth.resetPasswordForEmail(email, redirectUrl = PASSWORD_RESET_REDIRECT)
        return AccountResult.Success
    }

    override suspend fun signOut(): AccountResult {
        client.auth.signOut(SignOutScope.LOCAL)
        return AccountResult.Success
    }

    override suspend fun accessToken(): String? = client.auth.currentAccessTokenOrNull()

    fun handleDeepLink(intent: Intent) {
        client.handleDeeplinks(intent)
    }

    companion object {
        @Volatile
        private var shared: SupabaseAccountBackend? = null

        // One client for the whole process: the Activity hands deep links to
        // it and the ViewModel observes it. Null if the client can't be
        // built (callers fall back to UnavailableAccountBackend).
        fun get(): SupabaseAccountBackend? = shared ?: synchronized(this) {
            shared ?: runCatching {
                SupabaseAccountBackend(
                    createSupabaseClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY) {
                        install(Auth) {
                            // Explicit: the rigcheck:// redirect is claimable by any
                            // app, so the code exchange must be PKCE-bound.
                            flowType = FlowType.PKCE
                            scheme = AUTH_REDIRECT_SCHEME
                            host = AUTH_REDIRECT_HOST
                        }
                    },
                )
            }.getOrNull().also { shared = it }
        }
    }
}

// Used when the Supabase client can't be built, so the rest of the app
// (the free flow) keeps working and sign-in explains itself.
object UnavailableAccountBackend : AccountBackend {
    private val unavailable = AccountResult.Failure("Accounts are not available right now.")
    override val status: Flow<BackendStatus> = flowOf(BackendStatus.NotAuthenticated)
    override suspend fun signUp(email: String, password: String) = unavailable
    override suspend fun signIn(email: String, password: String) = unavailable
    override suspend fun signInWithGoogle(idToken: String, rawNonce: String) = unavailable
    override suspend fun signInWithApple() = unavailable
    override suspend fun requestPasswordReset(email: String) = unavailable
    override suspend fun signOut() = unavailable
    override suspend fun accessToken(): String? = null
}
