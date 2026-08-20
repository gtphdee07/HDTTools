package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
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
}
