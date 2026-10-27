package com.rigcheck.app.ui.navigation

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
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
import com.rigcheck.app.ui.RigCheckViewModel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// A signed-in account, with nothing to sign in or out of.
private class HistoryTestAccount : AccountBackend {
    override val status: Flow<BackendStatus> =
        MutableStateFlow(BackendStatus.Authenticated(Account("account-1", "rig@example.com")))
    override suspend fun accessToken(): String? = "token"
    private val notExercised = AccountResult.Failure("not used by these tests")
    override suspend fun signUp(email: String, password: String) = notExercised
    override suspend fun signIn(email: String, password: String) = notExercised
    override suspend fun signInWithGoogle(idToken: String, rawNonce: String) = notExercised
    override suspend fun signInWithApple() = notExercised
    override suspend fun requestPasswordReset(email: String) = notExercised
    override suspend fun signOut() = notExercised
}

// These tests are about the History, so the Garage accepts every Rig and holds none.
private object AcceptingGarage : GarageBackend {
    override suspend fun list(): List<RecentRig> = emptyList()
    override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) = Unit
    override suspend fun updateRig(rig: RecentRig) = Unit
    override suspend fun deleteRig(id: String) = Unit
}

// The account's History on a pretend server: checks that "another device" can add behind the app's back, and a
// switch that makes the next saves fail.
private class PretendHistory : HistoryBackend {
    private val lock = Any()
    private val entries = mutableListOf<HistoryEntry>()
    private var nextId = 1
    var failAdds = false
    var addCalls = 0
        private set

    fun madeElsewhere(nickname: String, verdict: VerdictStatus) = synchronized(lock) {
        entries.add(0, HistoryEntry("elsewhere-${nextId++}", "2026-10-20T12:00:00Z", nickname, verdict))
    }

    fun saved(): List<Pair<String, VerdictStatus>> = synchronized(lock) { entries.map { it.rigNickname to it.verdict } }

    override suspend fun list(): List<HistoryEntry> = synchronized(lock) { entries.toList() }

    override suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?) =
        synchronized(lock) {
            addCalls++
            if (failAdds) throw java.io.IOException("offline")
            entries.add(0, HistoryEntry("entry-${nextId++}", "2026-10-22T12:00:00Z", rigNickname, verdict))
            Unit
        }

    override suspend fun caps() = HistoryCaps(free = 10, pro = 50)
}

// #32: the History screen over the account's History, through the real nav host and view model. The account is a
// fake signed in, and the History a pretend server, so what is checked is what the user sees: checks made on
// another device are listed, a finished check is saved once and listed, and a check that could not be saved still
// shows its result.
@RunWith(AndroidJUnit4::class)
class HistoryNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    private lateinit var viewModel: RigCheckViewModel

    private fun showApp(history: PretendHistory) {
        composeRule.runOnUiThread {
            viewModel = RigCheckViewModel(ApplicationProvider.getApplicationContext(), HistoryTestAccount(), AcceptingGarage, history)
        }
        composeRule.setContent { RigCheckNavHost(viewModel = viewModel) }
        composeRule.waitUntil(timeoutMillis = 10_000) {
            var state: AccountState? = null
            composeRule.runOnUiThread { state = viewModel.accountState.value }
            state is AccountState.SignedIn
        }
    }

    private fun waitForText(text: String) = composeRule.waitUntil(timeoutMillis = 10_000) {
        composeRule.onAllNodesWithText(text, substring = true).fetchSemanticsNodes().isNotEmpty()
    }

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

    // The disclaimer is shown once per app session, so a second check in the same session goes straight to Results.
    private fun checkNewRigThroughToResults(nickname: String, disclaimerShown: Boolean = true) {
        enterNickname(nickname)
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Trailer Tag").performClick()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Scale Ticket").performClick()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Check Weights").performClick()
        if (disclaimerShown) composeRule.onNodeWithText("I Understand, Continue").performClick()
        composeRule.onNodeWithText("Start another check").assertIsDisplayed()
    }

    private fun openHistory() {
        composeRule.onNodeWithTag("open_history").performClick()
        composeRule.onNodeWithText("Check History").assertIsDisplayed()
    }

    @Test
    fun aCheckMadeOnAnotherDeviceIsListed() {
        val history = PretendHistory().apply { madeElsewhere("Made on Web", VerdictStatus.FAIL) }
        showApp(history)

        openHistory()

        waitForText("Made on Web")
        composeRule.onNodeWithText("Over Limit").assertIsDisplayed()
    }

    // The app has been open a while: the check from the other device was made after sign-in read the History.
    @Test
    fun aCheckMadeOnAnotherDeviceWhileTheAppIsOpenIsListedWhenHistoryIsOpened() {
        val history = PretendHistory()
        showApp(history)
        history.madeElsewhere("Made on Web", VerdictStatus.PASS)

        openHistory()

        waitForText("Made on Web")
        composeRule.onNodeWithText("Safe to Tow").assertIsDisplayed()
    }

    @Test
    fun aFinishedCheckIsSavedToTheAccountAndListedInHistory() {
        val history = PretendHistory()
        showApp(history)

        checkNewRigThroughToResults("Big Blue")
        composeRule.waitUntil(timeoutMillis = 10_000) { history.saved().isNotEmpty() }
        composeRule.onNodeWithText("Start another check").performClick()
        openHistory()

        waitForText("Big Blue")
        // A check with nothing entered has nothing to check, which is not an over-limit one.
        composeRule.onNodeWithText("Not Enough Info").assertIsDisplayed()
        assertEquals(listOf("Big Blue" to VerdictStatus.INSUFFICIENT), history.saved())
    }

    @Test
    fun theResultsScreenShownAgainDoesNotRecordTheCheckTwice() {
        val history = PretendHistory()
        showApp(history)
        checkNewRigThroughToResults("Big Blue")
        composeRule.waitUntil(timeoutMillis = 10_000) { history.saved().isNotEmpty() }

        // Turning the device composes the Results screen again, which saves the check's Rig again.
        composeRule.runOnUiThread { viewModel.saveCurrentRig() }
        composeRule.waitForIdle()

        assertEquals(1, history.addCalls)
        assertEquals(1, history.saved().size)
    }

    @Test
    fun aSecondCheckWithAnotherNewRigIsSavedToo() {
        val history = PretendHistory()
        showApp(history)
        checkNewRigThroughToResults("Big Blue")
        composeRule.waitUntil(timeoutMillis = 10_000) { history.saved().size == 1 }
        composeRule.onNodeWithText("Start another check").performClick()

        checkNewRigThroughToResults("Red Rig", disclaimerShown = false)

        composeRule.waitUntil(timeoutMillis = 10_000) { history.saved().size == 2 }
        assertEquals(setOf("Big Blue", "Red Rig"), history.saved().map { it.first }.toSet())
    }

    @Test
    fun aCheckThatCouldNotBeSavedStillShowsItsResultAndSaysItWasNotSaved() {
        val history = PretendHistory().apply { failAdds = true }
        showApp(history)

        checkNewRigThroughToResults("Big Blue")

        composeRule.waitUntil(timeoutMillis = 10_000) {
            composeRule.onAllNodesWithText("couldn't save this check to your History", substring = true)
                .fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithTag("history_notice").assertIsDisplayed()
        composeRule.onNodeWithText("Start another check").assertIsDisplayed()
        assertEquals(emptyList<Pair<String, VerdictStatus>>(), history.saved())
    }
}
