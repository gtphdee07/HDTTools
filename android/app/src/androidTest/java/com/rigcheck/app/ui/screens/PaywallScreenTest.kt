package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// The daily-tier custom test Application (CustomTestRunner) never calls
// Purchases.configure(), so RevenueCatManager.getOfferings() always throws
// here - these tests cover the resulting error-state rendering, which is
// genuinely what an unconfigured/offline device would see. Real Test Store
// offerings/pricing is the weekly-equivalent tier, deferred until the
// dedicated RevenueCat test customer exists (see NEXT_STEPS.md).
@RunWith(AndroidJUnit4::class)
class PaywallScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun rendersCreditBalanceHeaderAndOfferLoadError() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 7,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
            )
        }

        composeRule.onNodeWithText("Get More Scans").assertIsDisplayed()
        composeRule.onNodeWithText("You have 7 scan credits left.", substring = true).assertIsDisplayed()
        composeRule.onNodeWithText("Couldn't load offers", substring = true).assertIsDisplayed()
    }

    @Test
    fun singularCreditWordingForOneCredit() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 1, onPurchase = { _, _ -> }, onRestore = { }, onDone = { })
        }

        composeRule.onNodeWithText("You have 1 scan credit left.", substring = true).assertIsDisplayed()
    }

    @Test
    fun restorePurchaseLinkIsPresent() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 0, onPurchase = { _, _ -> }, onRestore = { }, onDone = { })
        }

        composeRule.onNodeWithText("Restore purchase").assertIsDisplayed()
    }

    // creditBalance = null is a real, previously-untested branch of
    // `creditBalance ?: 0` and its pluralization check - every existing
    // test above passes a non-null Int (7, 1, 0), so the elvis operator's
    // null side was never actually exercised.
    @Test
    fun nullCreditBalanceDefaultsToZeroPluralWording() {
        composeRule.setContent {
            PaywallScreen(creditBalance = null, onPurchase = { _, _ -> }, onRestore = { }, onDone = { })
        }

        composeRule.onNodeWithText("You have 0 scan credits left.", substring = true).assertIsDisplayed()
    }

    // "Restore purchase" is a real button with real onRestore plumbing
    // (isBusy disables it, then re-enables on completion) - the existing
    // test above only checks the link is present, never taps it. This
    // drives the interaction using a fake onRestore that reports success,
    // matching this file's own "no real RevenueCat" fake-based style.
    @Test
    fun tappingRestorePurchaseInvokesOnRestoreWithSuccess() {
        var restoreInvoked = false

        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { _, _ -> },
                onRestore = { onResult ->
                    restoreInvoked = true
                    onResult(true, null)
                },
                onDone = { },
            )
        }

        composeRule.onNodeWithText("Restore purchase").performClick()

        assert(restoreInvoked) { "onRestore should have fired" }
        composeRule.onNodeWithText("Restore purchase").assertIsDisplayed()
    }

    // Failure path: onRestore reports an error rather than success - the
    // button must not crash and must remain usable afterward.
    @Test
    fun tappingRestorePurchaseHandlesFailureWithoutCrashing() {
        var restoreInvoked = false

        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { _, _ -> },
                onRestore = { onResult ->
                    restoreInvoked = true
                    onResult(false, "Network error")
                },
                onDone = { },
            )
        }

        composeRule.onNodeWithText("Restore purchase").performClick()

        assert(restoreInvoked) { "onRestore should have fired" }
        composeRule.onNodeWithText("Restore purchase").assertIsEnabled()
    }

    // isBusy actually gates the button (disabled while a restore is in
    // flight, re-enabled once the callback resolves) - only observable by
    // holding the callback open rather than resolving it synchronously.
    @Test
    fun restoreButtonIsDisabledWhileBusyThenReenabledOnCompletion() {
        var savedCallback: ((Boolean, String?) -> Unit)? = null

        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { _, _ -> },
                onRestore = { onResult -> savedCallback = onResult },
                onDone = { },
            )
        }

        composeRule.onNodeWithText("Restore purchase").performClick()
        composeRule.onNodeWithText("Restore purchase").assertIsNotEnabled()

        // Must run on the UI thread - PaywallScreen's success branch calls
        // Toast.makeText, which requires a prepared Looper (confirmed by
        // actually running this: invoking the callback directly from the
        // test/instrumentation thread threw a real
        // "Can't toast on a thread that has not called Looper.prepare()"
        // NullPointerException, not anything wrong with PaywallScreen
        // itself).
        composeRule.runOnUiThread { savedCallback?.invoke(true, null) }
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Restore purchase").assertIsEnabled()
    }
}
