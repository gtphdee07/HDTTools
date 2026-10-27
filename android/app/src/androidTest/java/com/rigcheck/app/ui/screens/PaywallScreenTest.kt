package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.rigcheck.app.testsupport.fakePackage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// The daily-tier custom test Application (CustomTestRunner) never calls
// Purchases.configure(), so RevenueCatManager.getOfferings() always throws
// here - unless a test passes its own `loadPackages`, as the #101 cases at the
// end of this file do. The rest cover the resulting error-state rendering,
// which is genuinely what an unconfigured/offline device would see. Real Test Store
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
        composeRule.onNodeWithText("You have 7 scans left.", substring = true).assertIsDisplayed()
        // The glossary's words are "Scan" and "Scan Credit"; the lower-case "scan credits" is not used.
        composeRule.onNodeWithText("scan credit", substring = true, ignoreCase = true).assertDoesNotExist()
        composeRule.onNodeWithText("Couldn't load offers", substring = true).assertIsDisplayed()
    }

    @Test
    fun singularCreditWordingForOneCredit() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 1, onPurchase = { _, _ -> }, onRestore = { }, onDone = { })
        }

        composeRule.onNodeWithText("You have 1 scan left.", substring = true).assertIsDisplayed()
    }

    @Test
    fun restorePurchaseLinkIsPresent() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 0, onPurchase = { _, _ -> }, onRestore = { }, onDone = { })
        }

        composeRule.onNodeWithText("Restore purchase").assertIsDisplayed()
    }

    // Purchases land on the signed-in account (#22), so the paywall names
    // it - and signing out from here is how a different household member
    // switches accounts on a shared phone.
    @Test
    fun namesTheAccountThePurchaseIsFor() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 2,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                accountLabel = "alice@example.com",
            )
        }

        composeRule.onNodeWithText("Buying for alice@example.com").assertIsDisplayed()
    }

    // The plan is the account's, however Pro was bought (#27): a Pro bought on Web
    // reads as "Pro plan" here. Not known yet shows nothing, never "Free plan".
    @Test
    fun showsTheProPlanForAProAccount() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 2, onPurchase = { _, _ -> }, onRestore = { }, onDone = { }, isPro = true)
        }

        composeRule.onNodeWithText("Pro plan").assertIsDisplayed()
        composeRule.onNodeWithText("Free plan").assertDoesNotExist()
    }

    @Test
    fun showsTheFreePlanForAFreeAccount() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 0, onPurchase = { _, _ -> }, onRestore = { }, onDone = { }, isPro = false)
        }

        composeRule.onNodeWithText("Free plan").assertIsDisplayed()
        composeRule.onNodeWithText("Pro plan").assertDoesNotExist()
    }

    @Test
    fun showsNoPlanWhileItIsNotKnown() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 0, onPurchase = { _, _ -> }, onRestore = { }, onDone = { }, isPro = null)
        }

        composeRule.onNodeWithText("Pro plan").assertDoesNotExist()
        composeRule.onNodeWithText("Free plan").assertDoesNotExist()
    }

    @Test
    fun signOutButtonInvokesOnSignOut() {
        var signedOut = false
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 2,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                accountLabel = "alice@example.com",
                onSignOut = { signedOut = true },
            )
        }

        composeRule.onNodeWithText("Sign out").performClick()

        assert(signedOut) { "onSignOut should have fired" }
    }

    @Test
    fun showsNoAccountRowWhenNoAccountIsGiven() {
        composeRule.setContent {
            PaywallScreen(creditBalance = 2, onPurchase = { _, _ -> }, onRestore = { }, onDone = { })
        }

        composeRule.onNodeWithText("Sign out").assertDoesNotExist()
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

        composeRule.onNodeWithText("You have 0 scans left.", substring = true).assertIsDisplayed()
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

    // Scan packs are for Pro accounts only (#101, ADR-0006's 2026-10-12 amendment).
    // RevenueCat is faked as the Offering's packages: the ids are arbitrary and the
    // prices are the fakes' own, so what tells Pro from a pack is the reported
    // package type alone, and what is shown is the store's own price text.
    private val proPackage = fakePackage("pkg-a", PackageType.LIFETIME, "Pro (lifetime)", "\$14.99")
    private val smallPack = fakePackage("pkg-b", PackageType.CUSTOM, "10 scans", "\$2.99")
    private val largePack = fakePackage("pkg-c", PackageType.CUSTOM, "50 scans", "\$9.99")

    private fun waitForText(text: String) {
        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithText(text, substring = true).fetchSemanticsNodes().isNotEmpty()
        }
    }

    @Test
    fun aFreeAccountIsOfferedProAndNoScanPacks() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                isPro = false,
                loadPackages = { listOf(smallPack, proPackage, largePack) },
            )
        }

        waitForText("Pro (lifetime)")
        composeRule.onNodeWithText("Unlock Pro").assertIsDisplayed()
        composeRule.onNodeWithText("\$14.99").assertIsDisplayed()
        composeRule.onNodeWithText("10 scans").assertDoesNotExist()
        composeRule.onNodeWithText("50 scans").assertDoesNotExist()
        composeRule.onNodeWithText("\$2.99").assertDoesNotExist()
    }

    @Test
    fun aProAccountIsOfferedScanPacksAndNotPro() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                isPro = true,
                loadPackages = { listOf(smallPack, proPackage, largePack) },
            )
        }

        waitForText("10 scans")
        composeRule.onNodeWithText("50 scans").assertIsDisplayed()
        composeRule.onNodeWithText("\$2.99").assertIsDisplayed()
        composeRule.onNodeWithText("\$9.99").assertIsDisplayed()
        composeRule.onNodeWithText("Pro (lifetime)").assertDoesNotExist()
        composeRule.onNodeWithText("\$14.99").assertDoesNotExist()
    }

    // Nothing is offered while the plan is not known: showing packs to an account
    // that turns out to be Free would let it buy scans without Pro.
    @Test
    fun nothingIsOfferedWhileThePlanIsNotKnownAndTryAgainReadsItAgain() {
        var planReads = 0
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                isPro = null,
                onRetryPlan = { planReads++ },
                loadPackages = { listOf(smallPack, proPackage) },
            )
        }

        waitForText("Checking your plan")
        composeRule.onNodeWithText("Pro (lifetime)").assertDoesNotExist()
        composeRule.onNodeWithText("10 scans").assertDoesNotExist()

        composeRule.onNodeWithText("Try again").performClick()

        assertEquals(1, planReads)
    }

    // Buying Pro does not close the screen: once the account is Pro (and the starter
    // scans are in its balance) the packs replace the Pro offer where it stands.
    @Test
    fun buyingProOnThePaywallSwapsInTheScanPacksWithoutLeavingIt() {
        val isPro = mutableStateOf<Boolean?>(false)
        val balance = mutableStateOf<Int?>(0)
        var bought: Package? = null
        var done = false
        composeRule.setContent {
            PaywallScreen(
                creditBalance = balance.value,
                onPurchase = { pkg, report ->
                    bought = pkg
                    isPro.value = true
                    balance.value = 25
                    report(true, null)
                },
                onRestore = { },
                onDone = { done = true },
                isPro = isPro.value,
                loadPackages = { listOf(proPackage, smallPack, largePack) },
            )
        }
        waitForText("Pro (lifetime)")

        composeRule.onNodeWithText("\$14.99").performClick()

        waitForText("10 scans")
        assertEquals(proPackage, bought)
        assertFalse("buying Pro must not leave the Paywall", done)
        composeRule.onNodeWithText("Pro (lifetime)").assertDoesNotExist()
        composeRule.onNodeWithText("You have 25 scans left.", substring = true).assertIsDisplayed()
    }

    // The plan is read again after the purchase, so for a moment the account has Pro but
    // still reads as Free. Pro must not be buyable a second time in that gap.
    @Test
    fun proCannotBeBoughtAgainWhileThePlanCatchesUp() {
        val isPro = mutableStateOf<Boolean?>(false)
        var purchases = 0
        var planReads = 0
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, report ->
                    purchases++
                    report(true, null)
                },
                onRestore = { },
                onDone = { },
                isPro = isPro.value,
                onRetryPlan = { planReads++ },
                loadPackages = { listOf(proPackage, smallPack) },
            )
        }
        waitForText("Pro (lifetime)")

        composeRule.onNodeWithText("\$14.99").performClick()

        composeRule.onNodeWithText("\$14.99").assertIsNotEnabled()
        composeRule.onNodeWithText("Pro is yours.", substring = true).assertIsDisplayed()
        composeRule.onNodeWithText("Try again").performClick()
        assertEquals(1, planReads)
        assertEquals(1, purchases)

        composeRule.runOnUiThread { isPro.value = true }
        waitForText("10 scans")
        composeRule.onNodeWithText("Pro is yours.", substring = true).assertDoesNotExist()
    }

    @Test
    fun buyingAScanPackLeavesThePaywall() {
        var bought: Package? = null
        var done = false
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { pkg, report ->
                    bought = pkg
                    report(true, null)
                },
                onRestore = { },
                onDone = { done = true },
                isPro = true,
                loadPackages = { listOf(proPackage, smallPack, largePack) },
            )
        }
        waitForText("10 scans")

        composeRule.onNodeWithText("\$2.99").performClick()

        assertEquals(smallPack, bought)
        assertTrue("buying a pack ends the visit", done)
    }

    @Test
    fun aFreeAccountWithNoProPackageInTheOfferingIsToldProIsUnavailable() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                isPro = false,
                loadPackages = { listOf(smallPack, largePack) },
            )
        }

        waitForText("Pro isn't available to buy right now.")
        composeRule.onNodeWithText("10 scans").assertDoesNotExist()
    }

    @Test
    fun aProAccountWithNoScanPacksInTheOfferingIsToldSo() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                isPro = true,
                loadPackages = { listOf(proPackage) },
            )
        }

        waitForText("No scan packs are available right now.")
        composeRule.onNodeWithText("Pro (lifetime)").assertDoesNotExist()
    }

    // --- Scrolling and Back (#186) ---

    // A large font in a window too short for the content, as on a small phone or in split
    // screen: "Restore purchase" starts out of view and has to be reachable by scrolling,
    // while Back stays where it is.
    @Test
    fun aPaywallTallerThanTheWindowScrollsToRestorePurchaseAndKeepsBackInView() {
        composeRule.setContent {
            CompositionLocalProvider(LocalDensity provides Density(LocalDensity.current.density, fontScale = 2f)) {
                Box(modifier = Modifier.height(360.dp)) {
                    PaywallScreen(
                        creditBalance = 3,
                        onPurchase = { _, _ -> },
                        onRestore = { },
                        onDone = { },
                        accountLabel = "alice@example.com",
                        isPro = true,
                        loadPackages = { listOf(smallPack, largePack) },
                    )
                }
            }
        }
        waitForText("10 scans")
        composeRule.onNodeWithText("Restore purchase").assertIsNotDisplayed()

        composeRule.onNodeWithText("Restore purchase").performScrollTo().assertIsDisplayed()

        composeRule.onNodeWithTag("paywall_back").assertIsDisplayed()
    }

    // Restore purchase follows the offers instead of waiting at the bottom of the screen.
    @Test
    fun restorePurchaseComesRightAfterTheOffersNotAtTheBottomOfTheScreen() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 3,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                isPro = true,
                loadPackages = { listOf(smallPack) },
            )
        }
        waitForText("10 scans")

        val offerBottom = composeRule.onNodeWithText("\$2.99").fetchSemanticsNode().boundsInRoot.bottom
        val restoreTop = composeRule.onNodeWithText("Restore purchase").fetchSemanticsNode().boundsInRoot.top
        val windowHeight = composeRule.onRoot().fetchSemanticsNode().boundsInRoot.height
        assertTrue(
            "Restore purchase should sit near the offers, not at the bottom: " +
                "offer ends at $offerBottom, Restore starts at $restoreTop of $windowHeight",
            restoreTop - offerBottom < windowHeight / 4,
        )
    }

    // Back leaves the Paywall for every account state the screen can be in.
    private fun backLeaves(isPro: Boolean?, accountLabel: String?) {
        var left = 0
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { left++ },
                accountLabel = accountLabel,
                isPro = isPro,
            )
        }

        composeRule.onNodeWithText("Back").assertIsDisplayed().performClick()

        assertEquals(1, left)
    }

    @Test
    fun backLeavesThePaywallForAFreeAccount() = backLeaves(isPro = false, accountLabel = "alice@example.com")

    @Test
    fun backLeavesThePaywallForAProAccount() = backLeaves(isPro = true, accountLabel = "alice@example.com")

    @Test
    fun backLeavesThePaywallWhileThePlanIsNotKnown() = backLeaves(isPro = null, accountLabel = "alice@example.com")

    // Back, Sign out and Restore purchase all stay: adding Back took none of them away.
    @Test
    fun backSitsBesideSignOutAndRestorePurchase() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
                accountLabel = "alice@example.com",
                isPro = false,
            )
        }

        composeRule.onNodeWithText("Back").assertIsDisplayed()
        composeRule.onNodeWithText("Sign out").assertIsDisplayed()
        composeRule.onNodeWithText("Restore purchase").assertIsDisplayed()
    }

    // Leaving while a restore is out would let its result act on another screen.
    @Test
    fun backIsDisabledWhileARestoreIsOut() {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 0,
                onPurchase = { _, _ -> },
                onRestore = { },
                onDone = { },
            )
        }

        composeRule.onNodeWithText("Restore purchase").performClick()

        composeRule.onNodeWithText("Back").assertIsNotEnabled()
    }

    // The beta build buys with test cards (#182): the label shows with the flag set and is gone without it.
    @Test
    fun betaLabelShowsOnlyWhenTheBetaFlagIsSet() {
        val isBeta = mutableStateOf(true)
        composeRule.setContent {
            PaywallScreen(creditBalance = 0, onPurchase = { _, _ -> }, onRestore = { }, onDone = { }, isBeta = isBeta.value)
        }

        composeRule.onNodeWithText("Beta: test payments", substring = true).assertIsDisplayed()

        isBeta.value = false
        composeRule.onNodeWithText("Beta: test payments", substring = true).assertDoesNotExist()
    }
}
