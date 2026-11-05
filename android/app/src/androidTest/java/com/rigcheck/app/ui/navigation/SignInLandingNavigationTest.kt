package com.rigcheck.app.ui.navigation

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.Account
import com.rigcheck.app.data.AccountBackend
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.data.AccountState
import com.rigcheck.app.data.BackendStatus
import com.rigcheck.app.data.GarageBackend
import com.rigcheck.app.data.HistoryBackend
import com.rigcheck.app.data.HistoryCaps
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.UiTags
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// An account the test controls. A password sign-in succeeds at once; `becomeSignedIn` is what the account
// backend does after Google's own screen hands back a credential and it has been exchanged: the status becomes
// signed in. A device test cannot drive Google's screen, so the Google criterion is tested at this status change,
// which is the one place Google, Apple and password sign-in all come back through.
private class SignInAccount(initial: BackendStatus) : AccountBackend {
    private val account = Account("account-1", "rig@example.com")
    private val state = MutableStateFlow(initial)

    override val status: Flow<BackendStatus> = state
    override suspend fun accessToken(): String? = if (state.value is BackendStatus.Authenticated) "token" else null

    override suspend fun signIn(email: String, password: String): AccountResult {
        state.value = BackendStatus.Authenticated(account)
        return AccountResult.Success
    }

    // Google's credential exchanged, or a saved session found: the account is signed in.
    fun becomeSignedIn() {
        state.value = BackendStatus.Authenticated(account)
    }

    private val notExercised = AccountResult.Failure("not used by these tests")
    override suspend fun signUp(email: String, password: String) = notExercised
    override suspend fun signInWithGoogle(idToken: String, rawNonce: String) = notExercised
    override suspend fun signInWithApple() = notExercised
    override suspend fun requestPasswordReset(email: String) = notExercised
    override suspend fun signOut(): AccountResult {
        state.value = BackendStatus.NotAuthenticated
        return AccountResult.Success
    }
}

private object NoRigs : GarageBackend {
    override suspend fun list(): List<RecentRig> = emptyList()
    override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) = Unit
    override suspend fun updateRig(rig: RecentRig) = Unit
    override suspend fun deleteRig(id: String) = Unit
}

private object NoChecks : HistoryBackend {
    override suspend fun list(): List<HistoryEntry> = emptyList()
    override suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?) = Unit
    override suspend fun caps() = HistoryCaps(free = 10, pro = 50)
}

// #206: signing in returns to the screen the sign-in was started from, not to the account standing the sign-in screen
// turns into: the front page (the Rig picker) when it was started there, the check's own screen when it was started
// inside a check. Only the change from signed out to signed in does it. Through the real nav host and view model with
// a fake account.
@RunWith(AndroidJUnit4::class)
class SignInLandingNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    private lateinit var viewModel: RigCheckViewModel
    private lateinit var navController: NavHostController

    private fun showApp(account: SignInAccount) {
        composeRule.runOnUiThread {
            viewModel = RigCheckViewModel(ApplicationProvider.getApplicationContext(), account, NoRigs, NoChecks)
        }
        composeRule.setContent {
            val controller = rememberNavController()
            navController = controller
            RigCheckNavHost(navController = controller, viewModel = viewModel)
        }
    }

    private fun accountState(): AccountState {
        var state: AccountState? = null
        composeRule.runOnUiThread { state = viewModel.accountState.value }
        return state!!
    }

    private fun waitForAccount(signedIn: Boolean) {
        composeRule.waitUntil(timeoutMillis = 10_000) {
            val settled = if (signedIn) AccountState.SignedIn::class else AccountState.SignedOut::class
            settled.isInstance(accountState())
        }
    }

    // The signed-out picker's account row opens the sign-in screen.
    private fun openTheSignInScreen() {
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).performClick()
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.ACCOUNT_GOOGLE_BUTTON) == 1 }
    }

    private fun assertOnTheFrontPageSignedIn() {
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.PICKER_HEADING) == 1 }
        composeRule.onNodeWithTag(UiTags.PICKER_HEADING).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.ACCOUNT_GOOGLE_BUTTON).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.PAYWALL_TITLE).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).assertIsDisplayed()
    }

    // Back from the front page has nowhere to go: the sign-in screen is gone from the back stack, not just hidden.
    private fun assertFrontPageIsAloneInTheBackStack() {
        var routes = emptyList<Boolean>()
        var previousIsNull = false
        composeRule.runOnUiThread {
            routes = navController.currentBackStack.value.filter { it.destination.route != null }
                .map { it.destination.hasRoute<RigCheckRoute.Paywall>() }
            previousIsNull = navController.previousBackStackEntry == null
        }
        assertTrue("the sign-in screen must not be in the back stack: $routes", routes.none { it })
        assertTrue("Back from the front page must have nowhere to go", previousIsNull)
    }

    @Test
    fun aPasswordSignInFromTheSignInScreenLandsOnTheFrontPage() {
        showApp(SignInAccount(BackendStatus.NotAuthenticated))
        waitForAccount(signedIn = false)
        openTheSignInScreen()

        composeRule.onNodeWithTag(UiTags.ACCOUNT_EMAIL_FIELD).performTextInput("rig@example.com")
        composeRule.onNodeWithTag(UiTags.ACCOUNT_PASSWORD_FIELD).performTextInput("hunter22")
        composeRule.onNodeWithTag(UiTags.ACCOUNT_SUBMIT).performClick()

        waitForAccount(signedIn = true)
        assertOnTheFrontPageSignedIn()
        assertFrontPageIsAloneInTheBackStack()
    }

    @Test
    fun aGoogleSignInComingBackOnTheSignInScreenLandsOnTheFrontPage() {
        val account = SignInAccount(BackendStatus.NotAuthenticated)
        showApp(account)
        waitForAccount(signedIn = false)
        openTheSignInScreen()

        account.becomeSignedIn()

        waitForAccount(signedIn = true)
        assertOnTheFrontPageSignedIn()
        assertFrontPageIsAloneInTheBackStack()
    }

    // A sign-in started inside a check (a Scan error's "Sign in", buying Scans while signed out) opens the same
    // sign-in screen over the check's own screen; the user goes back to that screen, not to the front page. The
    // Chooser is put in place by navigating, which avoids typing a nickname (and so the keyboard waits of #125).
    @Test
    fun aSignInStartedInsideACheckReturnsToTheCheck() {
        showApp(SignInAccount(BackendStatus.NotAuthenticated))
        waitForAccount(signedIn = false)
        composeRule.runOnUiThread {
            navController.navigate(RigCheckRoute.Chooser(EntryModule.TRUCK))
            navController.navigate(RigCheckRoute.Paywall)
        }
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.ACCOUNT_GOOGLE_BUTTON) == 1 }

        composeRule.onNodeWithTag(UiTags.ACCOUNT_EMAIL_FIELD).performTextInput("rig@example.com")
        composeRule.onNodeWithTag(UiTags.ACCOUNT_PASSWORD_FIELD).performTextInput("hunter22")
        composeRule.onNodeWithTag(UiTags.ACCOUNT_SUBMIT).performClick()

        waitForAccount(signedIn = true)
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.CHOOSER_MANUAL_CARD) == 1 }
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PAYWALL_TITLE).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.ACCOUNT_GOOGLE_BUTTON).assertDoesNotExist()
    }

    @Test
    fun theAccountStandingOpenedWhileSignedInStaysOpen() {
        showApp(SignInAccount(BackendStatus.Authenticated(Account("account-1", "rig@example.com"))))
        waitForAccount(signedIn = true)

        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).performClick()

        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.PAYWALL_TITLE) == 1 }
        composeRule.waitForIdle()
        composeRule.onNodeWithTagText(UiTags.PAYWALL_ACCOUNT_LABEL, "Buying for rig@example.com").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PICKER_HEADING).assertDoesNotExist()
    }

    // The app opened already signed in: the account is "Loading" while the saved session is read, and the user may
    // already have opened the account standing. Loading to signed in is not a sign-in.
    @Test
    fun aSavedSessionFoundWhileTheAccountStandingIsOpenDoesNotMoveTheUser() {
        val account = SignInAccount(BackendStatus.Initializing)
        showApp(account)
        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).performClick()
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.PICKER_HEADING) == 0 }

        account.becomeSignedIn()

        waitForAccount(signedIn = true)
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.PAYWALL_TITLE) == 1 }
        composeRule.waitForIdle()
        composeRule.onNodeWithTag(UiTags.PAYWALL_TITLE).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PICKER_HEADING).assertDoesNotExist()
    }
}
