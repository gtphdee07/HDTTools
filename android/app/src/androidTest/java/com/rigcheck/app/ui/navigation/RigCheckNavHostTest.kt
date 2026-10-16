package com.rigcheck.app.ui.navigation

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.espresso.Espresso.pressBack
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// Real RigCheckNavHost + a real RigCheckViewModel - CustomTestRunner keeps
// this offline (no Purchases.configure()), so the credit chip just shows
// its "not yet loaded" placeholder and Scan Photo always routes to
// onNeedCredits/Paywall rather than actually scanning; every path exercised
// here is manual entry, matching the daily tier's offline scope.
@RunWith(AndroidJUnit4::class)
class RigCheckNavHostTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    // Types into the "Rig nickname" field and leaves the soft keyboard fully
    // closed. Typing focuses the field, which asks the IME to show; on a
    // freshly booted emulator Gboard takes seconds to bring its window up. If
    // the test moves on meanwhile, the hide it sends is lost, the keyboard
    // appears over a later screen and takes the first Back for itself (it
    // closes, nothing navigates). closeSoftKeyboard alone cannot help: it only
    // checks the app's own view of the keyboard, which still says hidden while
    // the show is in flight (#125). So wait until the keyboard is really up,
    // close it, and wait until it is really gone. Any test that types and later
    // presses Back must enter text through this.
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

    // The system Back button. With enterNickname() the keyboard is already
    // closed, so this closeSoftKeyboard is only a safety net for a test that
    // opens the keyboard some other way.
    private fun goBack() {
        closeSoftKeyboard()
        pressBack()
    }

    // The Next / Check Weights buttons are pinned below each entry form's
    // scrolling area, so they are always on screen and need no scrolling.
    private fun goThroughManualEntryFlow(nickname: String) {
        enterNickname(nickname)
        composeRule.onNodeWithText("Create").performClick()

        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Trailer Tag").assertIsDisplayed().performClick()

        composeRule.onNodeWithText("Trailer Tag").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Scale Ticket").assertIsDisplayed().performClick()

        composeRule.onNodeWithText("Scale Ticket").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Check Weights").assertIsDisplayed().performClick()
    }

    // The re-skinned Results screen has no "Results" title; its pinned
    // "Start another check" button is the one thing only it shows.
    private fun assertOnResults() {
        composeRule.onNodeWithText("Start another check").assertIsDisplayed()
    }

    @Test
    fun newRigHappyPathShowsDisclaimerThenResults() {
        composeRule.setContent { RigCheckNavHost() }

        goThroughManualEntryFlow("Big Blue")

        // First checkout in this session - disclaimer must appear.
        composeRule.onNodeWithText("Experimental Tool —\nNot for Safety Decisions").assertIsDisplayed()
        composeRule.onNodeWithText("I Understand, Continue").performClick()

        assertOnResults()
    }

    // Regression test for a real bug found during 2026-08-18 manual
    // testing: selecting an existing rig from RigPickerScreen used to
    // navigate straight to ScaleTicketEntryScreen, skipping the
    // Scan/Manual chooser entirely - so returning users had no way to
    // scan their scale ticket. Fixed in RigCheckNavHost.kt's
    // onSelectRecentRig to route through Chooser(EntryModule.SCALE)
    // first, same as every other module.
    @Test
    fun recentRigSelectionRoutesThroughTheChooserAndSkipsTheDisclaimerSecondTime() {
        composeRule.setContent { RigCheckNavHost() }

        goThroughManualEntryFlow("Goose and Addie")
        composeRule.onNodeWithText("I Understand, Continue").performClick()
        assertOnResults()

        // Results -> RigPicker is a single pop (popUpTo RigPicker, inclusive = false).
        goBack()

        // saveCurrentRig() writes to DataStore asynchronously (Results
        // screen's LaunchedEffect), and RigPickerScreen's recentRigs list
        // is sourced from that same Flow - poll instead of asserting
        // immediately, since Compose's own idle-sync doesn't wait on
        // arbitrary coroutine/IO completion, only on recomposition.
        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithText("Goose and Addie").fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithText("Goose and Addie").performClick()

        // Must land on the Chooser for the scale ticket, not straight on
        // the entry form - this is the regression check.
        composeRule.onNodeWithText("Scale Ticket").assertIsDisplayed()
        composeRule.onNodeWithText("Scan Photo").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()

        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Check Weights").assertIsDisplayed().performClick()

        // Disclaimer already acknowledged this session - straight to Results.
        assertOnResults()
    }

    // Offline (CustomTestRunner), so creditBalance is always the "not yet
    // loaded" null placeholder - ChooserScreen's (creditBalance ?: 0) > 0
    // check is therefore always false, so tapping "Scan Photo" always fires
    // onNeedCredits() rather than opening the take-photo/gallery dialog.
    // This is a real, previously-untested route into RigCheckRoute.Paywall
    // (the single composable<RigCheckRoute.Paywall> block was never reached
    // by either existing test) - and confirms the system back button pops
    // back to the Chooser it came from rather than crashing/getting stuck.
    @Test
    fun scanPhotoWithoutCreditsRoutesToPaywallAndBackReturnsToChooser() {
        composeRule.setContent { RigCheckNavHost() }

        enterNickname("Zoomer")
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()

        composeRule.onNodeWithText("Scan Photo").performClick()

        // Signed out, buying asks for an account first (#22).
        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()

        goBack()

        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
    }

    // Second, separate entry point into the same Paywall route:
    // CreditBalanceChip's onClick wires to onOpenPaywall directly (tapping
    // the chip itself, not the 0-credit Scan Photo gate above) - a distinct
    // call site/lambda in RigCheckNavHost.kt from onNeedCredits above, so
    // exercising only one of the two doesn't cover the other.
    @Test
    fun creditChipTapOpensPaywallDirectlyAndBackReturnsToChooser() {
        composeRule.setContent { RigCheckNavHost() }

        enterNickname("Chip Test")
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()

        // "…" is CreditBalanceChip's not-yet-loaded placeholder text.
        composeRule.onNodeWithText("…").performClick()

        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()

        goBack()

        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()
    }

    // The "Scan tow-vehicle-only ticket" button had no gate: a signed-out tap
    // opened the camera and only failed afterwards with a dead-end "Sign in to
    // scan." dialog. Offline (CustomTestRunner) there is no balance and no
    // account, so the tap must land on the sign-in screen with no photo
    // source offered, and "Not now" must return to the Truck Tag form.
    @Test
    fun standaloneTicketScanWhileSignedOutGoesToSignInBeforeAnyPhotoSource() {
        composeRule.setContent { RigCheckNavHost() }

        enterNickname("Tow Only")
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Trailer Tag").assertIsDisplayed()

        composeRule.onNodeWithTag("scan_standalone_ticket").performScrollTo().performClick()

        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()

        composeRule.onNodeWithText("Not now").performClick()

        composeRule.onNodeWithText("Next: Trailer Tag").assertIsDisplayed()
    }

    // The free flow must never be gated: a full manual check reaches
    // Results with no account and no sign-in screen along the way (the
    // happy-path test above already does exactly that) - and the only
    // thing that asks for an account is buying, so "Not now" on that
    // screen returns to where the user was with nothing lost.
    @Test
    fun notNowOnTheSignInScreenReturnsToTheChooser() {
        composeRule.setContent { RigCheckNavHost() }

        enterNickname("Maybe Later")
        composeRule.onNodeWithText("Create").performClick()
        composeRule.onNodeWithText("Scan Photo").performClick()
        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()

        composeRule.onNodeWithText("Not now").performClick()

        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
    }
}
