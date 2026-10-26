package com.rigcheck.app.ui.navigation

import android.net.Uri
import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.core.app.ApplicationProvider
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.Account
import com.rigcheck.app.data.AccountBackend
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.data.AccountState
import com.rigcheck.app.data.BackendStatus
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.ScanUiState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// An account backend the test controls: signed in or out from the start, and it
// counts the sessions it was asked to end (ending one signs it out, as Supabase does).
private class FakeAccountBackend(signedIn: Boolean) : AccountBackend {
    private val account = Account("account-1", "rig@example.com")
    private val statuses = MutableStateFlow<BackendStatus>(
        if (signedIn) BackendStatus.Authenticated(account) else BackendStatus.NotAuthenticated,
    )
    var signOutCalls = 0
        private set

    override val status: Flow<BackendStatus> = statuses
    override suspend fun signOut(): AccountResult {
        signOutCalls++
        statuses.value = BackendStatus.NotAuthenticated
        return AccountResult.Success
    }

    // Null when signed out: the real Scan path then fails with not_signed_in
    // before anything is sent.
    override suspend fun accessToken(): String? = if (statuses.value is BackendStatus.Authenticated) "token" else null

    private val notExercised = AccountResult.Failure("not used by these tests")
    override suspend fun signUp(email: String, password: String) = notExercised
    override suspend fun signIn(email: String, password: String) = notExercised
    override suspend fun signInWithGoogle(idToken: String, rawNonce: String) = notExercised
    override suspend fun signInWithApple() = notExercised
    override suspend fun requestPasswordReset(email: String) = notExercised
}

// #124: what the Scan error dialog's "Sign in" and "Buy more Scans" buttons do once
// tapped (followScanNextStep in RigCheckNavHost), through the real nav host and
// view model. A Scan is made to fail the way the Worker's answer would
// (RigCheckViewModel.scanSender), or fails by itself for not_signed_in, so no
// Worker or Scan Credit is involved. The account is a fake backend, signed in or out.
@RunWith(AndroidJUnit4::class)
class ScanErrorNextStepNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    private lateinit var backend: FakeAccountBackend
    private lateinit var viewModel: RigCheckViewModel

    // Where the Scan is started: the Scan Photo button of the Chooser, or the
    // stand-alone "Scan tow-vehicle-only ticket" button of the Truck Tag screen.
    private enum class ScanButton { CHOOSER, TRUCK_TAG_TICKET }

    // Same recipe as RigCheckNavHostTest (#125): leave the soft keyboard really closed.
    private fun enterNickname(nickname: String) {
        composeRule.onNodeWithText("Rig nickname").performTextInput(nickname)
        composeRule.waitUntil(timeoutMillis = 30_000) { isKeyboardVisible() }
        closeSoftKeyboard()
        composeRule.waitUntil(timeoutMillis = 30_000) { !isKeyboardVisible() }
    }

    private fun isKeyboardVisible(): Boolean {
        var visible = false
        composeRule.runOnUiThread {
            visible = ViewCompat.getRootWindowInsets(composeRule.activity.window.decorView)
                ?.isVisible(WindowInsetsCompat.Type.ime()) == true
        }
        return visible
    }

    private fun accountState(): AccountState {
        var state: AccountState? = null
        composeRule.runOnUiThread { state = viewModel.accountState.value }
        return state!!
    }

    // A new rig on the Truck Tag Chooser, with the account signed in or out and
    // every Scan answered with `failure` (null = the real send, which needs a token).
    private fun startRig(signedIn: Boolean, failure: ScanResult.Failure?, button: ScanButton) {
        backend = FakeAccountBackend(signedIn)
        composeRule.runOnUiThread {
            viewModel = RigCheckViewModel(ApplicationProvider.getApplicationContext(), backend)
            failure?.let { viewModel.scanSender = { _, _ -> it } }
        }
        composeRule.setContent { RigCheckNavHost(viewModel = viewModel) }
        // The account settles once the backend's first status is read.
        composeRule.waitUntil(timeoutMillis = 10_000) {
            val settled = if (signedIn) AccountState.SignedIn::class else AccountState.SignedOut::class
            settled.isInstance(accountState())
        }

        enterNickname("Scan Error Rig")
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
        if (button == ScanButton.TRUCK_TAG_TICKET) {
            composeRule.onNodeWithText("Enter Manually").performClick()
            composeRule.onNodeWithText("Next: Trailer Tag").assertIsDisplayed()
        }
    }

    private fun failScan(button: ScanButton, message: String) {
        composeRule.runOnUiThread {
            val resolver = composeRule.activity.contentResolver
            when (button) {
                ScanButton.CHOOSER -> viewModel.performScan(EntryModule.TRUCK, resolver, Uri.parse("content://scan/photo"))
                ScanButton.TRUCK_TAG_TICKET -> viewModel.performStandaloneScan(resolver, Uri.parse("content://scan/ticket"))
            }
        }
        composeRule.waitUntil(timeoutMillis = 10_000) {
            nodesWithText("Scan failed") == 1
        }
        composeRule.onNodeWithText(message).assertIsDisplayed()
    }

    private fun nodesWithText(text: String): Int = composeRule.onAllNodesWithText(text).fetchSemanticsNodes().size

    // Closed means the error is cleared, not just off screen: tapping a button that
    // opens another screen takes the dialog's screen out of the composition, but an
    // error left in the view model would be shown again when the user came back.
    private fun assertDialogClosed() {
        composeRule.onNodeWithText("Scan failed").assertDoesNotExist()
        var state: ScanUiState? = null
        composeRule.runOnUiThread { state = viewModel.scanState }
        assertEquals(ScanUiState.Idle, state)
    }

    // The sign-in screen the Paywall route shows a signed-out user.
    private fun assertOnSignInScreen() {
        composeRule.waitUntil(timeoutMillis = 10_000) { nodesWithText("Continue with Google") == 1 }
        composeRule.onNodeWithText("Get More Scans").assertDoesNotExist()
    }

    private fun assertOnPaywallSignedIn() {
        composeRule.waitUntil(timeoutMillis = 10_000) { nodesWithText("Get More Scans") == 1 }
        composeRule.onNodeWithText("Buying for rig@example.com").assertIsDisplayed()
        composeRule.onNodeWithText("Continue with Google").assertDoesNotExist()
    }

    // Still where the Scan was started, signed in, with nothing opened.
    private fun assertStayedPut(button: ScanButton) {
        assertDialogClosed()
        when (button) {
            ScanButton.CHOOSER -> composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
            ScanButton.TRUCK_TAG_TICKET -> composeRule.onNodeWithText("Next: Trailer Tag").assertIsDisplayed()
        }
        composeRule.onNodeWithText("Continue with Google").assertDoesNotExist()
        composeRule.onNodeWithText("Get More Scans").assertDoesNotExist()
    }

    private fun signInAfterRejectedToken(button: ScanButton) {
        startRig(signedIn = true, failure = ScanResult.Failure("unauthorized", "worker text"), button = button)
        failScan(button, ScanMessages.EXPIRED_SIGN_IN)

        composeRule.onNodeWithText("Sign in").performClick()

        assertDialogClosed()
        assertOnSignInScreen()
        assertEquals(1, backend.signOutCalls)
        assertEquals(AccountState.SignedOut, accountState())
    }

    private fun signInWithNoToken(button: ScanButton) {
        startRig(signedIn = false, failure = null, button = button)
        failScan(button, ScanMessages.NOT_SIGNED_IN)

        composeRule.onNodeWithText("Sign in").performClick()

        assertDialogClosed()
        assertOnSignInScreen()
        assertEquals(0, backend.signOutCalls)
    }

    private fun buyScansWhenOutOfScans(button: ScanButton) {
        startRig(signedIn = true, failure = ScanResult.Failure("insufficient_credits", "worker text"), button = button)
        failScan(button, ScanMessages.OUT_OF_SCANS)

        composeRule.onNodeWithText("Buy more Scans").performClick()

        assertDialogClosed()
        assertOnPaywallSignedIn()
        assertEquals(0, backend.signOutCalls)
    }

    // OK on the sign-in dialog of a rejected token (the one that could end the
    // session) and on the buy dialog: both only close, and the user stays signed in.
    private fun okOnlyCloses(button: ScanButton) {
        startRig(signedIn = true, failure = ScanResult.Failure("unauthorized", "worker text"), button = button)
        failScan(button, ScanMessages.EXPIRED_SIGN_IN)
        composeRule.onNodeWithText("OK").performClick()
        assertStayedPut(button)

        composeRule.runOnUiThread { viewModel.scanSender = { _, _ -> ScanResult.Failure("insufficient_credits", "worker text") } }
        failScan(button, ScanMessages.OUT_OF_SCANS)
        composeRule.onNodeWithText("OK").performClick()
        assertStayedPut(button)

        assertEquals(0, backend.signOutCalls)
        assert(accountState() is AccountState.SignedIn) { "OK must not end the session" }
    }

    // #186: the signed-in Paywall's Back control returns to the screen the user came from,
    // with the account still signed in.
    private fun backFromThePaywall(button: ScanButton) {
        startRig(signedIn = true, failure = ScanResult.Failure("insufficient_credits", "worker text"), button = button)
        failScan(button, ScanMessages.OUT_OF_SCANS)
        composeRule.onNodeWithText("Buy more Scans").performClick()
        assertOnPaywallSignedIn()

        composeRule.onNodeWithText("Back").performClick()

        assertStayedPut(button)
        assert(accountState() is AccountState.SignedIn) { "Back must not end the session" }
    }

    @Test
    fun chooserPaywallBackReturnsToTheChooser() = backFromThePaywall(ScanButton.CHOOSER)

    @Test
    fun truckTagTicketPaywallBackReturnsToTheTruckTag() = backFromThePaywall(ScanButton.TRUCK_TAG_TICKET)

    @Test
    fun chooserSignInAfterARejectedTokenEndsTheSessionAndShowsTheSignInScreen() = signInAfterRejectedToken(ScanButton.CHOOSER)

    @Test
    fun chooserSignInWithNoTokenShowsTheSignInScreenWithoutEndingASession() = signInWithNoToken(ScanButton.CHOOSER)

    @Test
    fun chooserBuyScansShowsThePaywallForASignedInUser() = buyScansWhenOutOfScans(ScanButton.CHOOSER)

    @Test
    fun chooserOkOnTheSignInAndBuyDialogsOnlyClosesThem() = okOnlyCloses(ScanButton.CHOOSER)

    @Test
    fun truckTagTicketSignInAfterARejectedTokenEndsTheSessionAndShowsTheSignInScreen() =
        signInAfterRejectedToken(ScanButton.TRUCK_TAG_TICKET)

    @Test
    fun truckTagTicketSignInWithNoTokenShowsTheSignInScreenWithoutEndingASession() = signInWithNoToken(ScanButton.TRUCK_TAG_TICKET)

    @Test
    fun truckTagTicketBuyScansShowsThePaywallForASignedInUser() = buyScansWhenOutOfScans(ScanButton.TRUCK_TAG_TICKET)

    @Test
    fun truckTagTicketOkOnTheSignInAndBuyDialogsOnlyClosesThem() = okOnlyCloses(ScanButton.TRUCK_TAG_TICKET)
}
