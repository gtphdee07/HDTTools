package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.navigation.EntryModule
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
        composeRule.onNodeWithText("Buy scans").assertDoesNotExist()

        composeRule.onNodeWithText("OK").performClick()

        assert(dismissed) { "onDismissScanError should have fired" }
    }

    @Test
    fun scanErrorThatNeedsASignInOffersItAndPassesTheStepOn() {
        val steps = mutableListOf<ScanNextStep>()
        setChooser(
            creditBalance = 5,
            scanState = ScanUiState.Error("Your sign-in has expired. Sign in again to scan.", ScanNextStep.SIGN_IN),
            onScanErrorNextStep = { steps += it },
        )

        composeRule.onNodeWithText("Your sign-in has expired. Sign in again to scan.").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in").performClick()

        assertEquals(listOf(ScanNextStep.SIGN_IN), steps)
    }

    @Test
    fun scanErrorWithNoScansLeftOffersBuyingScans() {
        val steps = mutableListOf<ScanNextStep>()
        setChooser(
            creditBalance = 5,
            scanState = ScanUiState.Error("You're out of scans.", ScanNextStep.BUY_SCANS),
            onScanErrorNextStep = { steps += it },
        )

        composeRule.onNodeWithText("You're out of scans.").assertIsDisplayed()
        composeRule.onNodeWithText("Buy scans").performClick()

        assertEquals(listOf(ScanNextStep.BUY_SCANS), steps)
    }
}
