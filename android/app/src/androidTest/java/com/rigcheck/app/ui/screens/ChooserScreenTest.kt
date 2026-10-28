package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.navigation.EntryModule
import com.rigcheck.app.ui.scanErrorFor
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ChooserScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun setChooser(
        creditBalance: Int?,
        scanState: ScanUiState = ScanUiState.Idle,
        module: EntryModule = EntryModule.SCALE,
        signedOut: Boolean = false,
        onChooseManual: () -> Unit = {},
        onPhotoScanned: (Uri) -> Unit = {},
        onNeedCredits: () -> Unit = {},
        onOpenPaywall: () -> Unit = {},
        onDismissScanError: () -> Unit = {},
        onScanErrorNextStep: (ScanNextStep) -> Unit = {},
        onBack: () -> Unit = {},
    ) {
        composeRule.setContent {
            ChooserScreen(
                module = module,
                creditBalance = creditBalance,
                signedOut = signedOut,
                scanState = scanState,
                onChooseManual = onChooseManual,
                onPhotoScanned = onPhotoScanned,
                onNeedCredits = onNeedCredits,
                onOpenPaywall = onOpenPaywall,
                onDismissScanError = onDismissScanError,
                onScanErrorNextStep = onScanErrorNextStep,
                onBack = onBack,
            )
        }
    }

    // The error a failed Scan with this code shows, as the app builds it.
    private fun failed(code: String) = scanErrorFor(ScanResult.Failure(code, "the Worker's own text"))

    @Test
    fun creditChipShowsTheGivenBalance() {
        setChooser(creditBalance = 7)
        composeRule.onNodeWithTagText(UiTags.CHOOSER_CREDIT_CHIP, "7 scans").assertIsDisplayed()
    }

    @Test
    fun scanPhotoWithCreditsOpensTheSourceChoiceDialog() {
        setChooser(creditBalance = 5)

        composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).performClick()

        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_GALLERY).assertIsDisplayed()
    }

    @Test
    fun scanPhotoWithZeroCreditsCallsOnNeedCreditsInsteadOfShowingTheDialog() {
        var neededCredits = false
        setChooser(creditBalance = 0, onNeedCredits = { neededCredits = true })

        composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
    }

    @Test
    fun enterManuallyInvokesTheCallback() {
        var chose = false
        setChooser(creditBalance = 5, onChooseManual = { chose = true })

        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).performClick()

        assert(chose) { "onChooseManual should have fired" }
    }

    // #118: the emulator showed taps reaching the buttons under the spinner, so a
    // second Scan, or manual entry with the first still out, could be started.
    @Test
    fun whileAScanIsInFlightTheLoadingOverlayAbsorbsTapsOnTheButtonsUnderIt() {
        var chose = 0
        var needCredits = 0
        setChooser(
            creditBalance = 5,
            scanState = ScanUiState.Loading,
            onChooseManual = { chose++ },
            onNeedCredits = { needCredits++ },
        )

        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).performClick()

        assertEquals("Enter Manually must not fire under the overlay", 0, chose)
        assertEquals(0, needCredits)
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
    }

    // The three documents share the screen; what differs is the title, the question and the step (the copy lock keeps
    // the words, this keeps each one on the right document).
    @Test
    fun eachDocumentShowsItsOwnTitleQuestionAndStep() {
        val expected = mapOf(
            EntryModule.TRUCK to Triple("Truck Tag", "How do you want to enter your truck's compliance-label values?", 1),
            EntryModule.TRAILER to Triple("Trailer Tag", "How do you want to enter your trailer's compliance-label values?", 2),
            EntryModule.SCALE to Triple("Scale Ticket", "How do you want to enter your CAT Scale ticket values?", 3),
        )
        var module by mutableStateOf(EntryModule.TRUCK)
        composeRule.setContent {
            ChooserScreen(
                module = module,
                creditBalance = 5,
                scanState = ScanUiState.Idle,
                onChooseManual = {},
                onPhotoScanned = {},
                onNeedCredits = {},
                onOpenPaywall = {},
                onDismissScanError = {},
                onScanErrorNextStep = {},
            )
        }

        for ((each, words) in expected) {
            composeRule.runOnIdle { module = each }
            composeRule.onNodeWithTagText(UiTags.CHOOSER_TITLE, words.first).assertIsDisplayed()
            composeRule.onNodeWithTagText(UiTags.CHOOSER_PROMPT, words.second).assertIsDisplayed()
            composeRule.onNodeWithTagText(UiTags.CHOOSER_STEP_BAR, "Step ${words.third} of 3").assertIsDisplayed()
        }
    }

    @Test
    fun theTwoWaysSayWhatTheyCostSoManualReadsAsAFirstClassPath() {
        setChooser(creditBalance = 5)

        composeRule.onNodeWithTagText(UiTags.CHOOSER_SCAN_BADGE, "1 credit").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.CHOOSER_MANUAL_BADGE, "Free").assertIsDisplayed()
        val scan = composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).fetchSemanticsNode().size
        val manual = composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).fetchSemanticsNode().size
        assertEquals("the two cards are the same size", scan, manual)
    }

    @Test
    fun theSignedOutChipSaysZeroScansAndStillOpensThePaywall() {
        var opened = false
        setChooser(creditBalance = null, signedOut = true, onOpenPaywall = { opened = true })

        composeRule.onNodeWithTagText(UiTags.CHOOSER_CREDIT_CHIP, "0 scans").assertIsDisplayed().performClick()

        assert(opened) { "the chip should open the Paywall" }
    }

    // --- Back (#192) ------------------------------------------------------------------------------------

    @Test
    fun backGoesBack() {
        var back = 0
        setChooser(creditBalance = 5, onBack = { back++ })

        composeRule.onNodeWithTag(UiTags.CHOOSER_BACK).assertIsEnabled().performClick()

        assertEquals(1, back)
    }

    // The brief: during a paid Scan the user cannot leave or restart the check. The overlay covers the top bar too,
    // so neither Back nor the balance chip works under it, and Back says it is off.
    @Test
    fun whileAScanIsInFlightBackAndTheChipDoNothing() {
        var back = 0
        var opened = 0
        setChooser(creditBalance = 5, scanState = ScanUiState.Loading, onBack = { back++ }, onOpenPaywall = { opened++ })

        composeRule.onNodeWithTagText(UiTags.CHOOSER_LOADING_TEXT, "Reading…").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.CHOOSER_BACK).assertIsNotEnabled().performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_CREDIT_CHIP).performClick()

        assertEquals("Back must not fire under the overlay", 0, back)
        assertEquals("the chip must not open the Paywall under the overlay", 0, opened)
    }

    @Test
    fun withNoScanInFlightThereIsNoOverlay() {
        setChooser(creditBalance = 5)

        composeRule.onNodeWithTag(UiTags.CHOOSER_LOADING_OVERLAY).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.CHOOSER_LOADING_TEXT).assertDoesNotExist()
    }

    // --- The photo-source dialog (#192) -------------------------------------------------------------------

    @Test
    fun thePhotoDialogAsksAndOffersTakePhotoAboveChooseFromGallery() {
        setChooser(creditBalance = 5)

        composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).performClick()

        composeRule.onNodeWithTagText(UiTags.PHOTO_DIALOG_TITLE, "Scan Photo").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.PHOTO_DIALOG_BODY, "Take a new photo, or choose one you already have?").assertIsDisplayed()
        val camera = composeRule.onNodeWithTagText(UiTags.PHOTO_DIALOG_CAMERA, "Take Photo").assertIsDisplayed()
        val gallery = composeRule.onNodeWithTagText(UiTags.PHOTO_DIALOG_GALLERY, "Choose from Gallery").assertIsDisplayed()
        assert(camera.fetchSemanticsNode().boundsInRoot.top < gallery.fetchSemanticsNode().boundsInRoot.top) {
            "the design puts Take Photo (the primary) above Choose from Gallery"
        }
    }

    @Test
    fun theDialogClosesOnTheChoiceItOffers() {
        setChooser(creditBalance = 5)
        composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).performClick()

        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_GALLERY).performClick()

        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_TITLE).assertDoesNotExist()
    }

    @Test
    fun scanErrorShowsDialogWithMessageAndDismissesOnOk() {
        var dismissed = false
        setChooser(
            creditBalance = 5,
            scanState = ScanUiState.Error("Could not read the image."),
            onDismissScanError = { dismissed = true },
        )

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_TITLE).assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.SCAN_ERROR_MESSAGE, "Could not read the image.").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_SIGN_IN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_BUY_SCANS).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertDoesNotExist()

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_OK_BUTTON).performClick()

        assert(dismissed) { "onDismissScanError should have fired" }
    }

    @Test
    fun scanErrorThatNeedsASignInOffersItAndPassesTheStepOn() {
        val steps = mutableListOf<ScanNextStep>()
        setChooser(
            creditBalance = 5,
            scanState = failed("unauthorized"),
            onScanErrorNextStep = { steps += it },
        )

        composeRule.onNodeWithTagText(UiTags.SCAN_ERROR_MESSAGE, "Your sign-in has expired. Nothing was used. Sign in again to scan.").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_SIGN_IN).performClick()

        assertEquals(listOf(ScanNextStep.SIGN_IN), steps)
    }

    @Test
    fun scanErrorWithNoScansLeftOffersBuyingScans() {
        val steps = mutableListOf<ScanNextStep>()
        setChooser(
            creditBalance = 0,
            scanState = failed("insufficient_credits"),
            onScanErrorNextStep = { steps += it },
        )

        composeRule.onNodeWithTagText(
            UiTags.SCAN_ERROR_MESSAGE,
            "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself.",
        ).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_BUY_SCANS).performClick()

        assertEquals(listOf(ScanNextStep.BUY_SCANS), steps)
    }

    // A lost answer, an unverifiable account, a failed read and a failed balance
    // check each offer Try again, which the screen passes on (it re-sends the photo).
    @Test
    fun scanErrorAfterALostAnswerOffersTryAgainAndPassesTheStepOn() {
        val steps = mutableListOf<ScanNextStep>()
        setChooser(creditBalance = 5, scanState = failed("network_error"), onScanErrorNextStep = { steps += it })

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).performClick()

        assertEquals(listOf(ScanNextStep.TRY_AGAIN), steps)
    }

    @Test
    fun scanErrorAfterARefundedReadOffersTryAgain() {
        setChooser(creditBalance = 5, scanState = failed("extraction_failed"))

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertIsDisplayed()
    }

    // After a request the service rejected, or a photo that cannot be sent, the
    // same photo would fail again: typing the numbers in or a different photo is
    // offered, Try again is not.
    @Test
    fun scanErrorAfterARejectedRequestOffersTypingOrADifferentPhotoAndNotTryAgain() {
        setChooser(creditBalance = 5, scanState = failed("bad_request"))

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
    }

    @Test
    fun scanErrorAfterAPhotoThatCannotBeSentOffersTypingOrADifferentPhotoAndNotTryAgain() {
        setChooser(creditBalance = 5, scanState = failed("photo_unsendable"))

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
    }

    // Typing it in is the Enter Manually card's destination, reached from the
    // dialog: the error closes, nothing is scanned and no step is passed on (so
    // nothing is spent or retried).
    @Test
    fun typingItInAfterARejectedRequestClosesTheErrorAndOpensManualEntryWithoutAScan() {
        var dismissed = false
        var manual = 0
        val scanned = mutableListOf<Uri>()
        val steps = mutableListOf<ScanNextStep>()
        setChooser(
            creditBalance = 5,
            scanState = failed("bad_request"),
            onChooseManual = { manual++ },
            onPhotoScanned = { scanned += it },
            onDismissScanError = { dismissed = true },
            onScanErrorNextStep = { steps += it },
        )

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(1, manual)
        assertEquals(emptyList<Uri>(), scanned)
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
    }

    @Test
    fun typingItInAfterAPhotoThatCannotBeSentOpensManualEntry() {
        var manual = 0
        setChooser(creditBalance = 5, scanState = failed("photo_unsendable"), onChooseManual = { manual++ })

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN).performClick()

        assertEquals(1, manual)
    }

    @Test
    fun choosingADifferentPhotoClosesTheErrorAndOffersTheSourceChoice() {
        var dismissed = false
        val steps = mutableListOf<ScanNextStep>()
        setChooser(
            creditBalance = 5,
            scanState = failed("bad_request"),
            onDismissScanError = { dismissed = true },
            onScanErrorNextStep = { steps += it },
        )

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_GALLERY).assertIsDisplayed()
    }

    @Test
    fun choosingADifferentPhotoWithNoScansLeftGoesToThePaywallInsteadOfTheSourceChoice() {
        var neededCredits = false
        setChooser(
            creditBalance = 0,
            scanState = failed("bad_request"),
            onNeedCredits = { neededCredits = true },
        )

        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithTag(UiTags.PHOTO_DIALOG_CAMERA).assertDoesNotExist()
    }
}
