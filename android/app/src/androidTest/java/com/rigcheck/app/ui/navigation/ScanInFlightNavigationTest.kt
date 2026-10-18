package com.rigcheck.app.ui.navigation

import android.net.Uri
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
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
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.ScanMessages
import kotlinx.coroutines.CompletableDeferred
import kotlinx.serialization.json.JsonObject
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
// entry screen, or crash; what it must do: tell the user and leave the app usable.
@RunWith(AndroidJUnit4::class)
class ScanInFlightNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    private fun viewModel() = ViewModelProvider(composeRule.activity)[RigCheckViewModel::class.java]

    // The Scan the sender was asked to make, and what it is waiting on.
    private val answer = CompletableDeferred<ScanResult>()
    private var sent = 0

    private val gvwrScan = ScanResult.Success(buildJsonObject { put("gvwr_lb", 11111) })

    // Same recipe as RigCheckNavHostTest (#125): leave the soft keyboard really
    // closed so a later Back is a Back.
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

    // A new rig, on the Truck Tag Chooser, with the view model's Scan held on `answer`.
    private fun startRigOnTheChooser(nickname: String) {
        composeRule.runOnUiThread {
            viewModel().scanSender = { _, _ ->
                sent++
                answer.await()
            }
        }
        enterNickname(nickname)
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
    }

    private fun scanTruckTag() {
        composeRule.runOnUiThread {
            viewModel().performScan(EntryModule.TRUCK, composeRule.activity.contentResolver, Uri.parse("content://scan/photo"))
        }
    }

    private fun waitForText(text: String) {
        composeRule.waitUntil(timeoutMillis = 10_000) {
            composeRule.onAllNodesWithText(text).fetchSemanticsNodes().isNotEmpty()
        }
    }

    private fun truckGvwr(): Double? {
        var gvwr: Double? = null
        composeRule.runOnUiThread { gvwr = viewModel().truck.gvwrLb }
        return gvwr
    }

    @Test
    fun aSecondScanWhileOneIsOutSendsNothing() {
        startRigOnTheChooser("One At A Time")

        scanTruckTag()
        scanTruckTag()
        composeRule.waitForIdle()

        assertEquals(1, sent)
        answer.complete(gvwrScan)
        waitForText("Next: Trailer Tag")
    }

    @Test
    fun aScanAnsweredOnTheCheckItStartedInFillsItAndOpensTheEntryScreen() {
        startRigOnTheChooser("Stays Put")

        scanTruckTag()
        answer.complete(gvwrScan)

        waitForText("Next: Trailer Tag")
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
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
        answer.complete(gvwrScan)

        waitForText("Next: Trailer Tag")
    }

    @Test
    fun aScanAnsweredAfterBackingOutToTheRigPickerIsNotUsedAndTheUserIsTold() {
        startRigOnTheChooser("Backed Out")
        scanTruckTag()
        pressBack()
        composeRule.onNodeWithText("Which rig?").assertIsDisplayed()

        answer.complete(gvwrScan)

        waitForText(ScanMessages.RESULT_NOT_USED)
        assertNull(truckGvwr())
        composeRule.onNodeWithText("Which rig?").assertIsDisplayed()
        composeRule.onAllNodesWithText("Next: Trailer Tag").assertCountEquals(0)
    }

    @Test
    fun aScanAnsweredAfterAnotherRigWasStartedDoesNotTouchThatRig() {
        startRigOnTheChooser("First Rig")
        scanTruckTag()
        composeRule.runOnUiThread { viewModel().startNewRig("Second Rig") }

        answer.complete(gvwrScan)

        waitForText(ScanMessages.RESULT_NOT_USED)
        assertNull(truckGvwr())
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
        composeRule.onAllNodesWithText("Next: Trailer Tag").assertCountEquals(0)
    }

    @Test
    fun theNextCheckCanScanWhileTheOldScanIsStillOut() {
        startRigOnTheChooser("Old Check")
        scanTruckTag()
        composeRule.runOnUiThread { viewModel().startNewRig("New Check") }

        scanTruckTag()
        composeRule.waitForIdle()

        assertEquals(2, sent)
        answer.complete(gvwrScan)
        waitForText(ScanMessages.RESULT_NOT_USED)
    }

    @Test
    fun aFailureAnsweredAfterTheCheckWasLeftShowsItsOwnMessageWithOnlyOk() {
        startRigOnTheChooser("Failed Late")
        scanTruckTag()
        composeRule.runOnUiThread { viewModel().startNewRig("Other Rig") }

        answer.complete(ScanResult.Failure("extraction_failed", "worker text"))

        waitForText(ScanMessages.EXTRACTION_FAILED)
        composeRule.onNodeWithText("OK").assertIsDisplayed()
        composeRule.onAllNodesWithText("Try again").assertCountEquals(0)
        composeRule.onAllNodesWithText("Scan failed").assertCountEquals(0)
    }
}
