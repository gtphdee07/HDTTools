package com.rigcheck.app.ui.screens

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.ui.NO_WEIGHT_ERROR
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.scanErrorFor
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

        composeRule.onNodeWithTag("scan_standalone_ticket").scrollToIfScrollable().assertIsDisplayed()
        composeRule.onNodeWithText("No ticket? Estimate pin/hitch weight as 20% of the trailer's weight")
            .scrollToIfScrollable()
            .assertIsDisplayed()
    }

    // #118: the button used to stay tappable while it read "Reading…", so a
    // second tap sent a second Scan.
    @Test
    fun standaloneScanButtonCannotBeTappedWhileAScanIsReading() {
        var needCredits = 0
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = ScanUiState.Loading,
                creditBalance = 5,
                onNeedCredits = { needCredits++ },
            )
        }

        composeRule.onNodeWithText("Reading…").scrollToIfScrollable().assertIsNotEnabled()
        composeRule.onNodeWithTag("scan_standalone_ticket").performClick()

        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
        assertEquals(0, needCredits)
    }

    @Test
    fun standaloneScanButtonIsEnabledWhenNoScanIsReading() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, creditBalance = 5)
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").scrollToIfScrollable().assertIsEnabled()
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

        composeRule.onNodeWithTag("scan_standalone_ticket").scrollToIfScrollable().assertIsDisplayed()
        composeRule.onNodeWithText("No ticket? Estimate pin/hitch weight as 20% of the trailer's weight")
            .assertDoesNotExist()
    }

    @Test
    fun scanStandaloneTicketButtonWithCreditsOpensTheSourceChoiceDialog() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, creditBalance = 3)
        }

        composeRule.onNodeWithTag("scan_standalone_ticket").scrollToIfScrollable().performClick()

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

        composeRule.onNodeWithTag("scan_standalone_ticket").scrollToIfScrollable().performClick()

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

        composeRule.onNodeWithTag("scan_standalone_ticket").scrollToIfScrollable().performClick()

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
        composeRule.onNodeWithText("Buy more Scans").assertDoesNotExist()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
        composeRule.onNodeWithText("Choose a different photo").assertDoesNotExist()
        composeRule.onNodeWithText("Type it in").assertDoesNotExist()

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
                scanState = failed("unauthorized"),
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("Your sign-in has expired. Nothing was used. Sign in again to scan.").assertIsDisplayed()
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
                scanState = failed("insufficient_credits"),
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText(
            "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself.",
        ).assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
        composeRule.onNodeWithText("Buy more Scans").performClick()

        assertEquals(listOf(ScanNextStep.BUY_SCANS), steps)
    }

    @Test
    fun standaloneScanErrorAfterALostAnswerOffersTryAgainAndPassesTheStepOn() {
        val steps = mutableListOf<ScanNextStep>()
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = failed("timeout"),
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("Choose a different photo").assertDoesNotExist()
        composeRule.onNodeWithText("Try again").performClick()

        assertEquals(listOf(ScanNextStep.TRY_AGAIN), steps)
    }

    @Test
    fun standaloneScanErrorAfterARejectedRequestOffersTypingOrADifferentPhotoAndNotTryAgain() {
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = failed("bad_request"),
            )
        }

        composeRule.onNodeWithText("Type it in").assertIsDisplayed()
        composeRule.onNodeWithText("Choose a different photo").assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    @Test
    fun standaloneScanErrorAfterAPhotoThatCannotBeSentOffersTypingOrADifferentPhotoAndNotTryAgain() {
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = failed("photo_unsendable"),
            )
        }

        composeRule.onNodeWithText("Type it in").assertIsDisplayed()
        composeRule.onNodeWithText("Choose a different photo").assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    // The weight fields are already on this screen, so typing it in only closes
    // the error and leaves them usable.
    @Test
    fun typingItInAfterARejectedRequestClosesTheErrorAndLeavesTheFieldsUsable() {
        val steps = mutableListOf<ScanNextStep>()
        var current = TruckTag()
        composeRule.setContent {
            var scanState by remember { mutableStateOf<ScanUiState>(failed("bad_request")) }
            TruckTagEntryScreen(
                truck = current,
                onTruckChange = { current = it },
                onContinue = {},
                scanState = scanState,
                onDismissStandaloneScanError = { scanState = ScanUiState.Idle },
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("Type it in").performClick()

        composeRule.onNodeWithText("Scan failed").assertDoesNotExist()
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithTag("truck_description").performTextInput("Ford F-450")
        assertEquals("Ford F-450", current.description)
    }

    // The ticket was read and the Scan used, but it held no weight: no Try again,
    // which would be another paid Scan of the same photo.
    @Test
    fun standaloneTicketWithNoWeightSaysTheScanWasUsedAndOffersTypingOrADifferentPhoto() {
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = NO_WEIGHT_ERROR,
            )
        }

        composeRule.onNodeWithText(
            "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. " +
                "Type the weight in, or choose a different photo.",
        ).assertIsDisplayed()
        composeRule.onNodeWithText("Type it in").assertIsDisplayed()
        composeRule.onNodeWithText("Choose a different photo").assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    @Test
    fun typingItInClosesTheErrorAndPassesNothingOn() {
        var dismissed = false
        val steps = mutableListOf<ScanNextStep>()
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = NO_WEIGHT_ERROR,
                onDismissStandaloneScanError = { dismissed = true },
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("Type it in").performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(emptyList<ScanNextStep>(), steps)
    }

    @Test
    fun choosingADifferentPhotoClosesTheErrorAndOffersTheSourceChoice() {
        var dismissed = false
        val steps = mutableListOf<ScanNextStep>()
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = NO_WEIGHT_ERROR,
                onDismissStandaloneScanError = { dismissed = true },
                creditBalance = 3,
                onScanErrorNextStep = { steps += it },
            )
        }

        composeRule.onNodeWithText("Choose a different photo").performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithText("Take Photo").assertIsDisplayed()
        composeRule.onNodeWithText("Choose from Gallery").assertIsDisplayed()
    }

    // The no-weight answer charged a Scan, so the balance may now be 0: a different
    // photo goes through the same gate as the Scan button, to the paywall.
    @Test
    fun choosingADifferentPhotoWithNoScansLeftGoesToThePaywallInsteadOfTheSourceChoice() {
        var neededCredits = false
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(),
                onTruckChange = {},
                onContinue = {},
                scanState = NO_WEIGHT_ERROR,
                creditBalance = 0,
                onNeedCredits = { neededCredits = true },
            )
        }

        composeRule.onNodeWithText("Choose a different photo").performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
    }

    // The error a failed Scan with this code shows, as the app builds it.
    private fun failed(code: String) = scanErrorFor(ScanResult.Failure(code, "the Worker's own text"))
}
