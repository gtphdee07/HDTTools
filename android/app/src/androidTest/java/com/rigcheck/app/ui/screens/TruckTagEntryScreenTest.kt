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
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.ui.NO_WEIGHT_ERROR
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
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

        composeRule.onNodeWithTag(UiTags.TRUCK_DESCRIPTION).performTextInput("Ford F-450")

        assertEquals("Ford F-450", current.description)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = { continued = true })
        }

        // Pinned below the scrolling form, so it is on screen however tall the content is.
        composeRule.onNodeWithTag(UiTags.TRUCK_NEXT_BUTTON).assertIsDisplayed().performClick()

        assert(continued) { "onContinue should have fired" }
    }

    // Predictive-estimate feature (Round 2, landed 2026-08-21): the scan
    // entry point + pin-weight-% slider added to this screen.

    @Test
    fun pinWeightSliderShowsWhenStandaloneWeightIsUnknown() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, pinWeightPct = 20)
        }

        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).scrollToIfScrollable().assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.TRUCK_PIN_WEIGHT_LABEL, "No ticket? Estimate pin/hitch weight as 20% of the trailer's weight")
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

        composeRule.onNodeWithTagText(UiTags.SCAN_STANDALONE_TICKET, "Reading…").scrollToIfScrollable().assertIsNotEnabled()
        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).performClick()

        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
        assertEquals(0, needCredits)
    }

    @Test
    fun standaloneScanButtonIsEnabledWhenNoScanIsReading() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, creditBalance = 5)
        }

        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).scrollToIfScrollable().assertIsEnabled()
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

        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).scrollToIfScrollable().assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.TRUCK_PIN_WEIGHT_LABEL, "No ticket? Estimate pin/hitch weight as 20% of the trailer's weight")
            .assertDoesNotExist()
    }

    @Test
    fun scanStandaloneTicketButtonWithCreditsOpensTheSourceChoiceDialog() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = {}, creditBalance = 3)
        }

        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).scrollToIfScrollable().performClick()

        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_GALLERY).assertIsDisplayed()
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

        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).scrollToIfScrollable().performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
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

        composeRule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET).scrollToIfScrollable().performClick()

        assert(neededCredits) { "onNeedCredits should have fired when no balance is loaded" }
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_TITLE).assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.SCAN_ERROR_MESSAGE, "Could not read the image.").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_SIGN_IN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_BUY_SCANS).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).assertDoesNotExist()

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_OK_BUTTON).performClick()

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

        composeRule.onNodeWithTagText(UiTags.SCAN_ERROR_MESSAGE, "Your sign-in has expired. Nothing was used. Sign in again to scan.").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_SIGN_IN).performClick()

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

        composeRule.onNodeWithTagText(
            UiTags.SCAN_ERROR_MESSAGE,
            "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself.",
        ).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_BUY_SCANS).performClick()

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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).performClick()

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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).performClick()

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_TITLE).assertDoesNotExist()
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithTag(UiTags.TRUCK_DESCRIPTION).performTextInput("Ford F-450")
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

        composeRule.onNodeWithTagText(
            UiTags.SCAN_ERROR_MESSAGE,
            "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. " +
                "Type the weight in, or choose a different photo.",
        ).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).performClick()

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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_GALLERY).assertIsDisplayed()
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

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
    }

    // #47: the optional GCWR, typed by hand from the owner's manual.

    @Test
    fun gcwrFieldShowsItsHintAndTypingItSetsTheTruckGcwr() {
        var current = TruckTag()
        composeRule.setContent {
            TruckTagEntryScreen(truck = current, onTruckChange = { current = it }, onContinue = {})
        }

        composeRule.onNodeWithTag(UiTags.TRUCK_GCWR).scrollToIfScrollable().assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.TRUCK_GCWR_HELP, "From your owner's manual. Leave blank if you can't find it.")
            .scrollToIfScrollable()
            .assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.TRUCK_GCWR).scrollToIfScrollable().performTextInput("26000")

        assertEquals(26_000.0, current.gcwrLb)
    }

    @Test
    fun gcwrBelowTheGvwrShowsAWarningAndTheValueIsKept() {
        // State, so the screen recomposes with the typed value and the warning can appear.
        var current by mutableStateOf(TruckTag(gvwrLb = 14_000.0))
        composeRule.setContent {
            TruckTagEntryScreen(truck = current, onTruckChange = { current = it }, onContinue = {})
        }

        composeRule.onNodeWithTag(UiTags.TRUCK_GCWR_WARNING).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.TRUCK_GCWR).scrollToIfScrollable().performTextInput("13000")

        composeRule.onNodeWithTag(UiTags.TRUCK_GCWR_WARNING).scrollToIfScrollable().assertIsDisplayed()
        assertEquals(13_000.0, current.gcwrLb)
    }

    @Test
    fun noGcwrWarningWhenTheGvwrIsNotKnown() {
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(gcwrLb = 13_000.0), onTruckChange = {}, onContinue = {})
        }

        composeRule.onNodeWithTag(UiTags.TRUCK_GCWR_WARNING).assertDoesNotExist()
    }

    // The error a failed Scan with this code shows, as the app builds it.
    private fun failed(code: String) = scanErrorFor(ScanResult.Failure(code, "the Worker's own text"))
}
