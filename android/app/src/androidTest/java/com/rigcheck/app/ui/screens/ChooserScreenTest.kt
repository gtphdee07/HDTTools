package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
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
        composeRule.onNodeWithText("7 scans").assertIsDisplayed()
    }

    @Test
    fun scanPhotoWithCreditsOpensTheSourceChoiceDialog() {
        setChooser(creditBalance = 5)

        composeRule.onNodeWithText("Scan Photo").performClick()

        composeRule.onNodeWithText("Take Photo").assertIsDisplayed()
        composeRule.onNodeWithText("Choose from Gallery").assertIsDisplayed()
    }

    @Test
    fun scanPhotoWithZeroCreditsCallsOnNeedCreditsInsteadOfShowingTheDialog() {
        var neededCredits = false
        setChooser(creditBalance = 0, onNeedCredits = { neededCredits = true })

        composeRule.onNodeWithText("Scan Photo").performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
    }

    @Test
    fun enterManuallyInvokesTheCallback() {
        var chose = false
        setChooser(creditBalance = 5, onChooseManual = { chose = true })

        composeRule.onNodeWithText("Enter Manually").performClick()

        assert(chose) { "onChooseManual should have fired" }
    }

    @Test
    fun scanErrorShowsDialogWithMessageAndDismissesOnOk() {
        var dismissed = false
        setChooser(
            creditBalance = 5,
            scanState = ScanUiState.Error("Could not read the image."),
            onDismissScanError = { dismissed = true },
        )

        composeRule.onNodeWithText("Scan failed").assertIsDisplayed()
        composeRule.onNodeWithText("Could not read the image.").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in").assertDoesNotExist()
        composeRule.onNodeWithText("Buy more Scans").assertDoesNotExist()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
        composeRule.onNodeWithText("Choose a different photo").assertDoesNotExist()

        composeRule.onNodeWithText("OK").performClick()

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

        composeRule.onNodeWithText("Your sign-in has expired. Nothing was used. Sign in again to scan.").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in").performClick()

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

        composeRule.onNodeWithText(
            "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself.",
        ).assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
        composeRule.onNodeWithText("Buy more Scans").performClick()

        assertEquals(listOf(ScanNextStep.BUY_SCANS), steps)
    }

    // A lost answer, an unverifiable account, a failed read and a failed balance
    // check each offer Try again, which the screen passes on (it re-sends the photo).
    @Test
    fun scanErrorAfterALostAnswerOffersTryAgainAndPassesTheStepOn() {
        val steps = mutableListOf<ScanNextStep>()
        setChooser(creditBalance = 5, scanState = failed("network_error"), onScanErrorNextStep = { steps += it })

        composeRule.onNodeWithText("Choose a different photo").assertDoesNotExist()
        composeRule.onNodeWithText("Try again").performClick()

        assertEquals(listOf(ScanNextStep.TRY_AGAIN), steps)
    }

    @Test
    fun scanErrorAfterARefundedReadOffersTryAgain() {
        setChooser(creditBalance = 5, scanState = failed("extraction_failed"))

        composeRule.onNodeWithText("Try again").assertIsDisplayed()
    }

    // After a request the service rejected, or a photo that cannot be sent, the
    // same photo would fail again: typing the numbers in or a different photo is
    // offered, Try again is not.
    @Test
    fun scanErrorAfterARejectedRequestOffersTypingOrADifferentPhotoAndNotTryAgain() {
        setChooser(creditBalance = 5, scanState = failed("bad_request"))

        composeRule.onNodeWithText("Type it in").assertIsDisplayed()
        composeRule.onNodeWithText("Choose a different photo").assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    @Test
    fun scanErrorAfterAPhotoThatCannotBeSentOffersTypingOrADifferentPhotoAndNotTryAgain() {
        setChooser(creditBalance = 5, scanState = failed("photo_unsendable"))

        composeRule.onNodeWithText("Type it in").assertIsDisplayed()
        composeRule.onNodeWithText("Choose a different photo").assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
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

        composeRule.onNodeWithText("Type it in").performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(1, manual)
        assertEquals(emptyList<Uri>(), scanned)
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
    }

    @Test
    fun typingItInAfterAPhotoThatCannotBeSentOpensManualEntry() {
        var manual = 0
        setChooser(creditBalance = 5, scanState = failed("photo_unsendable"), onChooseManual = { manual++ })

        composeRule.onNodeWithText("Type it in").performClick()

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

        composeRule.onNodeWithText("Choose a different photo").performClick()

        assert(dismissed) { "the error should be dismissed" }
        assertEquals(emptyList<ScanNextStep>(), steps)
        composeRule.onNodeWithText("Take Photo").assertIsDisplayed()
        composeRule.onNodeWithText("Choose from Gallery").assertIsDisplayed()
    }

    @Test
    fun choosingADifferentPhotoWithNoScansLeftGoesToThePaywallInsteadOfTheSourceChoice() {
        var neededCredits = false
        setChooser(
            creditBalance = 0,
            scanState = failed("bad_request"),
            onNeedCredits = { neededCredits = true },
        )

        composeRule.onNodeWithText("Choose a different photo").performClick()

        assert(neededCredits) { "onNeedCredits should have fired for a 0-credit user" }
        composeRule.onNodeWithText("Take Photo").assertDoesNotExist()
    }
}
