package com.rigcheck.app.ui.navigation

import android.net.Uri
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.ViewModelProvider
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.espresso.Espresso.pressBack
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.MainActivity
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.testsupport.nodesWithTagShowing
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import kotlinx.coroutines.CompletableDeferred
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #118: a Scan in flight, through the real MainActivity, nav host and view model.
// The view model's Scan is answered by the test (RigCheckViewModel.scanSender), so
// a Scan can be held open and answered when the test chooses, with no Worker and
// no Scan Credit. What a late answer must not do: change the current rig, open an
// entry screen, touch the loading or error state of the check the user is in now,
// or crash; what it must do: tell the user and leave the app usable.
@RunWith(AndroidJUnit4::class)
class ScanInFlightNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    private fun viewModel() = ViewModelProvider(composeRule.activity)[RigCheckViewModel::class.java]

    // One answer per Scan, in the order the Scans are sent; the test completes each
    // when it likes. `sent` counts the Scans that reached the sender.
    private val answers = List(2) { CompletableDeferred<ScanResult>() }
    private val answer = answers[0]
    private var sent = 0

    private val gvwrScan = ScanResult.Success(buildJsonObject { put("gvwr_lb", 11111) })
    private val ticketScan = ScanResult.Success(buildJsonObject { put("gross_weight_lb", 7000) })

    // Same recipe as RigCheckNavHostTest (#125): leave the soft keyboard really
    // closed so a later Back is a Back.
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

    // A new rig, on the Truck Tag Chooser, with the view model's Scans held on `answers`.
    private fun startRigOnTheChooser(nickname: String) {
        composeRule.runOnUiThread {
            viewModel().scanSender = { _, _ -> answers[sent++].await() }
        }
        enterNickname(nickname)
        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).assertIsDisplayed()
    }

    private fun scanTruckTag() {
        composeRule.runOnUiThread {
            viewModel().performScan(EntryModule.TRUCK, composeRule.activity.contentResolver, Uri.parse("content://scan/photo"))
        }
    }

    private fun scanStandaloneTicket() {
        composeRule.runOnUiThread {
            viewModel().performStandaloneScan(composeRule.activity.contentResolver, Uri.parse("content://scan/ticket"))
        }
    }

    private fun waitForTag(tag: String) {
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTag(tag) > 0 }
    }

    private fun waitForTagText(tag: String, text: String) {
        composeRule.waitUntil(timeoutMillis = 10_000) { composeRule.nodesWithTagShowing(tag, text) > 0 }
    }

    private fun <T> onUiThread(read: RigCheckViewModel.() -> T): T {
        var value: T? = null
        composeRule.runOnUiThread { value = viewModel().read() }
        @Suppress("UNCHECKED_CAST")
        return value as T
    }

    private fun truckGvwr(): Double? = onUiThread { truck.gvwrLb }

    private fun standaloneWeight(): Double? = onUiThread { truck.standaloneWeightLb }

    private fun scanState(): ScanUiState = onUiThread { scanState }

    @Test
    fun aSecondScanWhileOneIsOutSendsNothing() {
        startRigOnTheChooser("One At A Time")

        scanTruckTag()
        scanTruckTag()
        composeRule.waitForIdle()

        assertEquals(1, sent)
        answer.complete(gvwrScan)
        waitForTag(UiTags.TRUCK_NEXT_BUTTON)
    }

    @Test
    fun aScanAnsweredOnTheCheckItStartedInFillsItAndOpensTheEntryScreen() {
        startRigOnTheChooser("Stays Put")

        scanTruckTag()
        answer.complete(gvwrScan)

        waitForTag(UiTags.TRUCK_NEXT_BUTTON)
        assertEquals(11111.0, truckGvwr()!!, 0.0)
    }

    @Test
    fun aScanAnsweredAfterTheDeviceWasTurnedOpensTheEntryScreenAndKeepsTheApp() {
        // The callback that opened the entry screen used to hold the NavController
        // of the screen that started the Scan; turning the device builds a new one,
        // and the old one was told to navigate after it was gone (a crash).
        startRigOnTheChooser("Turned")
        scanTruckTag()

        composeRule.activityRule.scenario.recreate()
        composeRule.waitForIdle()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).assertIsDisplayed()
        answer.complete(gvwrScan)

        waitForTag(UiTags.TRUCK_NEXT_BUTTON)
    }

    @Test
    fun aScanAnsweredAfterBackingOutToTheRigPickerIsNotUsedAndTheUserIsTold() {
        startRigOnTheChooser("Backed Out")
        scanTruckTag()
        pressBack()
        composeRule.onNodeWithTag(UiTags.PICKER_HEADING).assertIsDisplayed()
        // Leaving the check cleared its loading state at once.
        assertEquals(ScanUiState.Idle, scanState())

        answer.complete(gvwrScan)

        waitForTagText(UiTags.LATE_SCAN_MESSAGE, ScanMessages.RESULT_NOT_USED)
        assertNull(truckGvwr())
        composeRule.onNodeWithTag(UiTags.PICKER_HEADING).assertIsDisplayed()
        composeRule.onAllNodesWithTag(UiTags.TRUCK_NEXT_BUTTON).assertCountEquals(0)
    }

    @Test
    fun aScanAnsweredAfterAnotherRigWasStartedDoesNotTouchThatRig() {
        startRigOnTheChooser("First Rig")
        scanTruckTag()
        assertEquals(ScanUiState.Loading, scanState())
        composeRule.runOnUiThread { viewModel().startNewRig("Second Rig") }
        assertEquals(ScanUiState.Idle, scanState())

        answer.complete(gvwrScan)

        waitForTagText(UiTags.LATE_SCAN_MESSAGE, ScanMessages.RESULT_NOT_USED)
        assertNull(truckGvwr())
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).assertIsDisplayed()
        composeRule.onAllNodesWithTag(UiTags.TRUCK_NEXT_BUTTON).assertCountEquals(0)
    }

    @Test
    fun theNextCheckCanScanWhileTheOldScanIsOutAndTheOldAnswerLeavesItsLoadingStateAlone() {
        startRigOnTheChooser("Old Check")
        scanTruckTag()
        composeRule.runOnUiThread { viewModel().startNewRig("New Check") }

        scanTruckTag()
        composeRule.waitForIdle()
        assertEquals(2, sent)
        assertEquals(ScanUiState.Loading, scanState())

        // The old Scan answers while the new check's Scan is still out: it is
        // reported, and the new check is still loading, with no error shown.
        answers[0].complete(gvwrScan)
        waitForTagText(UiTags.LATE_SCAN_MESSAGE, ScanMessages.RESULT_NOT_USED)
        assertEquals(ScanUiState.Loading, scanState())
        composeRule.onAllNodesWithTag(UiTags.SCAN_ERROR_TITLE).assertCountEquals(0)
        assertNull(truckGvwr())

        // The new check's own Scan then fills it and opens its entry screen.
        answers[1].complete(gvwrScan)
        waitForTag(UiTags.TRUCK_NEXT_BUTTON)
        assertEquals(11111.0, truckGvwr()!!, 0.0)
    }

    @Test
    fun aFailureAnsweredAfterTheCheckWasLeftShowsItsOwnMessageWithOnlyOk() {
        startRigOnTheChooser("Failed Late")
        scanTruckTag()
        composeRule.runOnUiThread { viewModel().startNewRig("Other Rig") }

        answer.complete(ScanResult.Failure("extraction_failed", "worker text"))

        waitForTagText(UiTags.LATE_SCAN_MESSAGE, ScanMessages.EXTRACTION_FAILED)
        composeRule.onNodeWithTag(UiTags.LATE_SCAN_OK_BUTTON).assertIsDisplayed()
        composeRule.onAllNodesWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertCountEquals(0)
        composeRule.onAllNodesWithTag(UiTags.SCAN_ERROR_TITLE).assertCountEquals(0)
        assertEquals(ScanUiState.Idle, scanState())
    }

    // --- The stand-alone ticket Scan, on the Truck Tag screen ---

    private fun openTheTruckTagByHand() {
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).performClick()
        composeRule.onNodeWithTag(UiTags.TRUCK_NEXT_BUTTON).assertIsDisplayed()
    }

    @Test
    fun aSecondStandaloneScanWhileOneIsOutSendsNothing() {
        startRigOnTheChooser("Ticket Once")
        openTheTruckTagByHand()

        scanStandaloneTicket()
        scanStandaloneTicket()
        composeRule.waitForIdle()

        assertEquals(1, sent)
        answer.complete(ticketScan)
        composeRule.waitUntil(timeoutMillis = 10_000) { standaloneWeight() == 7000.0 }
    }

    @Test
    fun aStandaloneScanAnsweredOnTheTruckTagScreenFillsTheWeight() {
        startRigOnTheChooser("Ticket Here")
        openTheTruckTagByHand()

        scanStandaloneTicket()
        answer.complete(ticketScan)

        composeRule.waitUntil(timeoutMillis = 10_000) { standaloneWeight() == 7000.0 }
        composeRule.onAllNodesWithTag(UiTags.LATE_SCAN_MESSAGE).assertCountEquals(0)
    }

    @Test
    fun aStandaloneScanAnsweredAfterLeavingTheTruckTagScreenIsNotUsedAndTheUserIsTold() {
        startRigOnTheChooser("Ticket Gone")
        openTheTruckTagByHand()
        scanStandaloneTicket()
        composeRule.onNodeWithTag(UiTags.TRUCK_NEXT_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).assertIsDisplayed()
        assertEquals(ScanUiState.Idle, scanState())

        answer.complete(ticketScan)

        waitForTagText(UiTags.LATE_SCAN_MESSAGE, ScanMessages.RESULT_NOT_USED)
        assertNull(standaloneWeight())
    }

    @Test
    fun aStandaloneScanAnsweredAfterAnotherRigWasStartedDoesNotTouchThatRig() {
        startRigOnTheChooser("Ticket First")
        openTheTruckTagByHand()
        scanStandaloneTicket()
        composeRule.runOnUiThread { viewModel().startNewRig("Ticket Second") }

        answer.complete(ticketScan)

        waitForTagText(UiTags.LATE_SCAN_MESSAGE, ScanMessages.RESULT_NOT_USED)
        assertNull(standaloneWeight())
    }
}
