package com.rigcheck.app.ui.navigation

import android.net.Uri
import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.core.app.ApplicationProvider
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.espresso.Espresso.pressBack
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
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.UiTags
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// A signed-in account that can sign out, and counts the sign-outs that reached it.
private class SignOutAccount : AccountBackend {
    private val account = Account("account-1", "rig@example.com")
    private val state = MutableStateFlow<BackendStatus>(BackendStatus.Authenticated(account))
    var signOuts = 0
        private set

    override val status: Flow<BackendStatus> = state
    override suspend fun accessToken(): String? = "token"
    private val notExercised = AccountResult.Failure("not used by these tests")
    override suspend fun signUp(email: String, password: String) = notExercised
    override suspend fun signIn(email: String, password: String) = notExercised
    override suspend fun signInWithGoogle(idToken: String, rawNonce: String) = notExercised
    override suspend fun signInWithApple() = notExercised
    override suspend fun requestPasswordReset(email: String) = notExercised
    override suspend fun signOut(): AccountResult {
        signOuts++
        state.value = BackendStatus.NotAuthenticated
        return AccountResult.Success
    }
}

private object EmptyGarage : GarageBackend {
    override suspend fun list(): List<RecentRig> = emptyList()
    override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) = Unit
    override suspend fun updateRig(rig: RecentRig) = Unit
    override suspend fun deleteRig(id: String) = Unit
}

private object EmptyHistory : HistoryBackend {
    override suspend fun list(): List<HistoryEntry> = emptyList()
    override suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?) = Unit
    override suspend fun caps() = HistoryCaps(free = 10, pro = 50)
}

// #197 (owner decision 2026-10-28, from the #192 merge): Sign out is not possible while a paid Scan is out. A Scan
// started on the Chooser stays out when the user backs out of the check (the Worker has taken a Scan Credit for it),
// so the picker's account sheet, which a user gets back to by system Back, and the Paywall's Sign out both say it is
// unavailable, in words, until the Scan has answered. Through the real nav host and view model, with the Scan held
// open by the test (RigCheckViewModel.scanSender).
@RunWith(AndroidJUnit4::class)
class SignOutDuringScanNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    private lateinit var viewModel: RigCheckViewModel
    private val account = SignOutAccount()
    private val answer = CompletableDeferred<ScanResult>()

    private fun showAppSignedIn() {
        composeRule.runOnUiThread {
            viewModel = RigCheckViewModel(ApplicationProvider.getApplicationContext(), account, EmptyGarage, EmptyHistory)
            viewModel.scanSender = { _, _ -> answer.await() }
        }
        composeRule.setContent { RigCheckNavHost(viewModel = viewModel) }
        composeRule.waitUntil(timeoutMillis = 10_000) { accountState() is AccountState.SignedIn }
    }

    private fun accountState(): AccountState {
        var state: AccountState? = null
        composeRule.runOnUiThread { state = viewModel.accountState.value }
        return state!!
    }

    // Same recipe as RigCheckNavHostTest (#125): leave the soft keyboard really closed, so a later Back is a Back.
    private fun enterNickname(nickname: String) {
        composeRule.onNodeWithTag(UiTags.PICKER_NEW_RIG_INPUT).performTextInput(nickname)
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

    // Starts a Scan on the Truck Tag Chooser and backs out to the Rig picker with it still out.
    private fun startAScanAndBackOutToThePicker() {
        enterNickname("Big Blue")
        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).assertIsDisplayed()
        composeRule.runOnUiThread {
            viewModel.performScan(EntryModule.TRUCK, composeRule.activity.contentResolver, Uri.parse("content://scan/photo"))
        }
        composeRule.waitUntil(timeoutMillis = 10_000) { viewModel.scanIsOut }
        pressBack()
        composeRule.onNodeWithTag(UiTags.PICKER_HEADING).assertIsDisplayed()
    }

    private fun openTheAccountSheet() {
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).performClick()
        composeRule.onNodeWithTag(UiTags.PICKER_SIGN_OUT_BUTTON).assertIsDisplayed()
    }

    private fun answerTheScan() {
        answer.complete(ScanResult.Success(buildJsonObject { put("gvwr_lb", 11111) }))
        // The Scan answered after its check ended: the user is told, and OK is the way on.
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(UiTags.LATE_SCAN_OK_BUTTON) > 0 }
        composeRule.onNodeWithTag(UiTags.LATE_SCAN_OK_BUTTON).performClick()
    }

    @Test
    fun theAccountSheetOfARigPickerBackedOutToWhileAScanIsOutOffersNoSignOut() {
        showAppSignedIn()
        startAScanAndBackOutToThePicker()

        openTheAccountSheet()

        composeRule.onNodeWithTag(UiTags.PICKER_SIGN_OUT_BUTTON).assertIsNotEnabled()
        composeRule.onNodeWithText(ScanMessages.SIGN_OUT_UNAVAILABLE).assertIsDisplayed()
        // A tap does nothing, and neither does the view model if it is asked: the account is still signed in.
        composeRule.onNodeWithTag(UiTags.PICKER_SIGN_OUT_BUTTON).performClick()
        composeRule.runOnUiThread { viewModel.signOut() }
        composeRule.waitForIdle()
        assertEquals(0, account.signOuts)
        assertTrue(accountState() is AccountState.SignedIn)
    }

    @Test
    fun signOutWorksAgainOnceTheScanHasAnswered() {
        showAppSignedIn()
        startAScanAndBackOutToThePicker()
        answerTheScan()

        openTheAccountSheet()

        composeRule.onNodeWithTag(UiTags.PICKER_SIGN_OUT_BUTTON).assertIsEnabled()
        composeRule.onAllNodesWithText(ScanMessages.SIGN_OUT_UNAVAILABLE).assertCountEquals(0)
        composeRule.onNodeWithTag(UiTags.PICKER_SIGN_OUT_BUTTON).performClick()
        composeRule.waitUntil(timeoutMillis = 10_000) { accountState() is AccountState.SignedOut }
        assertEquals(1, account.signOuts)
    }

    @Test
    fun thePaywallsSignOutIsAlsoUnavailableWhileAScanIsOut() {
        showAppSignedIn()
        startAScanAndBackOutToThePicker()

        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).performClick()

        composeRule.onNodeWithTag(UiTags.PAYWALL_SIGN_OUT_BUTTON).assertIsNotEnabled()
        composeRule.onNodeWithText(ScanMessages.SIGN_OUT_UNAVAILABLE).assertIsDisplayed()
    }
}
