package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.compose.ui.test.assertIsDisplayed
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
        onChooseManual: () -> Unit = {},
        onPhotoScanned: (Uri) -> Unit = {},
        onNeedCredits: () -> Unit = {},
        onOpenPaywall: () -> Unit = {},
        onDismissScanError: () -> Unit = {},
        onScanErrorNextStep: (ScanNextStep) -> Unit = {},
    ) {
        composeRule.setContent {
            ChooserScreen(
                module = EntryModule.SCALE,
                creditBalance = creditBalance,
                scanState = scanState,
                onChooseManual = onChooseManual,
                onPhotoScanned = onPhotoScanned,
                onNeedCredits = onNeedCredits,
                onOpenPaywall = onOpenPaywall,
                onDismissScanError = onDismissScanError,
                onScanErrorNextStep = onScanErrorNextStep,
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
