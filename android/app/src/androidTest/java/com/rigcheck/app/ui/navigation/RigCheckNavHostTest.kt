package com.rigcheck.app.ui.navigation

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
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

    private fun goThroughManualEntryFlow(nickname: String) {
        composeRule.onNodeWithText("Rig nickname (e.g. Big Blue)").performTextInput(nickname)
        composeRule.onNodeWithText("Create").performClick()

        composeRule.onNodeWithText("Truck Tag").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Trailer Tag").performScrollTo().performClick()

        composeRule.onNodeWithText("Trailer Tag").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Next: Scale Ticket").performScrollTo().performClick()

        composeRule.onNodeWithText("Scale Ticket").assertIsDisplayed()
        composeRule.onNodeWithText("Enter Manually").performClick()
        composeRule.onNodeWithText("Check Weights").performScrollTo().performClick()
    }

    @Test
    fun newRigHappyPathShowsDisclaimerThenResults() {
        composeRule.setContent { RigCheckNavHost() }

        goThroughManualEntryFlow("Big Blue")

        // First checkout in this session - disclaimer must appear.
        composeRule.onNodeWithText("Experimental Tool —\nNot for Safety Decisions").assertIsDisplayed()
        composeRule.onNodeWithText("I Understand, Continue").performClick()

        composeRule.onNodeWithText("Results").assertIsDisplayed()
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
        composeRule.onNodeWithText("Results").assertIsDisplayed()

        // Results -> RigPicker is a single pop (popUpTo RigPicker, inclusive = false).
        pressBack()

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
        composeRule.onNodeWithText("Check Weights").performScrollTo().performClick()

        // Disclaimer already acknowledged this session - straight to Results.
        composeRule.onNodeWithText("Results").assertIsDisplayed()
    }
}
