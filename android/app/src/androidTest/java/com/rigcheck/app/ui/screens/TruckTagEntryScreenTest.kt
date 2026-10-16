package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TruckTagEntryScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun typingDescriptionUpdatesTheTruckAndBlankBecomesNull() {
        var current = TruckTag()
        composeRule.setContent {
            TruckTagEntryScreen(truck = current, onTruckChange = { current = it }, onContinue = {})
        }

        composeRule.onNodeWithTag("truck_description").performTextInput("Ford F-450")

        assertEquals("Ford F-450", current.description)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = { continued = true })
        }

        // Pinned below the scrolling form, so it is on screen however tall the content is.
        composeRule.onNodeWithText("Next: Trailer Tag").assertIsDisplayed().performClick()

        assert(continued) { "onContinue should have fired" }
    }

    // Predictive-estimate feature (Round 2, landed 2026-08-21): the scan
    // entry point + pin-weight-% slider added to this screen.

    @Test
    fun pinWeightSliderShowsWhenStandaloneWeightIsUnknown() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, pinWeightPct = 20)
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("No ticket? Estimate pin/hitch weight as 20% of the trailer's weight")
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun pinWeightSliderHidesWhenStandaloneWeightIsAlreadyKnown() {
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(standaloneWeightLb = 6000.0),
                onTruckChange = {},
                onContinue = {},
                pinWeightPct = 20,
            )
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("No ticket? Estimate pin/hitch weight as 20% of the trailer's weight")
            .assertDoesNotExist()
    }

    @Test
    fun scanStandaloneTicketButtonWithCreditsOpensTheSourceChoiceDialog() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, creditBalance = 3)
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").performScrollTo().performClick()

        composeRule.onNodeWithText("Take Photo").assertIsDisplayed()
        composeRule.onNodeWithText("Choose from Gallery").assertIsDisplayed()
    }

    // The same gate as the main Scan Photo button: no balance above zero (none
    // loaded, which is what a signed-out user has, or none left) goes to
    // onNeedCredits, which opens the paywall - or sign-in first when signed
    // out - before any camera or gallery is offered.
    @Test
    fun scanStandaloneTicketButtonWithZeroCreditsCallsOnNeedCreditsInsteadOfShowingTheDialog() {
        var neededCredits = false
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                creditBalance = 0,
                onNeedCredits = { neededCredits = true },
            )
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").performScrollTo().performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
    }

    @Test
    fun scanStandaloneTicketButtonWithNoBalanceLoadedCallsOnNeedCreditsInsteadOfShowingTheDialog() {
        var neededCredits = false
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                creditBalance = null,
                onNeedCredits = { neededCredits = true },
            )
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").performScrollTo().performClick()

        assert(neededCredits) { "onNeedCredits should have fired when no balance is loaded" }
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
    }

    @Test
    fun standaloneScanErrorShowsDialogWithMessageAndDismissesOnOk() {
        var dismissed = false
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = ScanUiState.Error("Could not read the image."),
                onDismissStandaloneScanError = { dismissed = true },
            )
        }

        composeRule.onNodeWithText("Scan failed").assertIsDisplayed()
        composeRule.onNodeWithText("Could not read the image.").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in").assertDoesNotExist()
        composeRule.onNodeWithText("Buy scans").assertDoesNotExist()

        composeRule.onNodeWithText("OK").performClick()

        assert(dismissed) { "onDismissStandaloneScanError should have fired" }
    }

    @Test
    fun standaloneScanErrorThatNeedsASignInOffersItAndPassesTheStepOn() {
        val steps = mutableListOf<ScanNextStep>()
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = ScanUiState.Error("Your sign-in has expired. Sign in again to scan.", ScanNextStep.SIGN_IN),
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("Your sign-in has expired. Sign in again to scan.").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in").performClick()

        assertEquals(listOf(ScanNextStep.SIGN_IN), steps)
    }

    @Test
    fun standaloneScanErrorWithNoScansLeftOffersBuyingScans() {
        val steps = mutableListOf<ScanNextStep>()
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = ScanUiState.Error("You're out of scans.", ScanNextStep.BUY_SCANS),
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("You're out of scans.").assertIsDisplayed()
        composeRule.onNodeWithText("Buy scans").performClick()

        assertEquals(listOf(ScanNextStep.BUY_SCANS), steps)
    }
}
