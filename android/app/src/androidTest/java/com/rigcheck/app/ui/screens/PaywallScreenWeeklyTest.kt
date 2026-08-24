package com.rigcheck.app.ui.screens

import android.util.Base64
import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.ScanApiClient
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// Weekly-equivalent tier - runs against real RevenueCat Test Store
// offerings and a real deployed Worker call. test-weekly.ps1 touches a
// device-side marker file before invoking `am instrument`, which
// CustomTestRunner checks to substitute WeeklyTestApplication
// (weekly-test-user) for the Daily tier's plain offline Application.
// Explicitly excluded from ./gradlew connectedDebugAndroidTest via
// build.gradle.kts's testInstrumentationRunnerArguments["notClass"] -
// see android/TESTING.md, CustomTestRunner.kt, and android/test-weekly.ps1
// for how this tier is invoked and why (two earlier mechanisms tried and
// rejected, confirmed hands-on: a second named instrumentation runner
// doesn't survive AGP's manifest merge; instrumentation args aren't
// readable yet when newApplication() fires in this environment).
//
// Real cost per full run: one real ~$0.01 Claude call (the scan case).
// The purchase case's cost is zero - RevenueCat's Test Store never
// charges a real payment method, confirmed hands-on (2026-08-23) by
// triggering a real Test Store purchase and reading its own dialog text:
// "This is a test purchase and should only be used during development."
@RunWith(AndroidJUnit4::class)
class PaywallScreenWeeklyTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun rendersRealOfferingsFromTestStore() {
        runBlocking {
            // Fetch the real package directly first, so the assertion below
            // checks for a concrete known value (not a guess about internal
            // UI structure) - the same pkg.product.title/price.formatted
            // fields PaywallScreen itself renders.
            val offerings = RevenueCatManager.getOfferings()
            val pkg = offerings.current?.availablePackages?.firstOrNull()
            assertNotNull("Test Store offering must have at least one package", pkg)
            val expectedTitle = pkg!!.product.title
            val expectedPrice = pkg.product.price.formatted

            composeRule.setContent {
                PaywallScreen(
                    creditBalance = null,
                    onPurchase = { _, _ -> },
                    onRestore = { },
                    onDone = { },
                )
            }

            // Real offerings take a real network round trip to load - unlike
            // the daily tier's PaywallScreenTest, which sees the "Couldn't
            // load offers" error state immediately (no Purchases.configure()
            // call at all there).
            composeRule.waitUntil(timeoutMillis = 15_000) {
                composeRule.onAllNodesWithText(expectedTitle, substring = true).fetchSemanticsNodes().isNotEmpty() ||
                    composeRule.onAllNodesWithText("Couldn't load offers", substring = true).fetchSemanticsNodes().isNotEmpty()
            }

            assertTrue(
                "Should not show the offline error state when real offerings are configured",
                composeRule.onAllNodesWithText("Couldn't load offers", substring = true).fetchSemanticsNodes().isEmpty(),
            )
            composeRule.onNodeWithText(expectedTitle, substring = true).assertIsDisplayed()
            composeRule.onNodeWithText(expectedPrice, substring = true).assertIsDisplayed()
        }
    }

    // RevenueCat's Test Store purchase flow pops a native (non-Compose)
    // "Test Store Purchase" AlertDialog beyond the app's own Buy button -
    // confirmed hands-on before writing this test (screenshotted the real
    // dialog via the already-installed app, same SDK dialog regardless of
    // app-user-id). Standard android:id/button1/2/3 resource-ids, so
    // UiDevice/UiAutomator (not composeRule, which can't see outside the
    // Compose hierarchy) drives it. The dialog's own text confirms this is
    // a dev-only purchase with no real charge ("This is a test purchase
    // and should only be used during development").
    @Test
    fun realPurchaseIncrementsBalance() = runBlocking {
        val balanceBefore = RevenueCatManager.getScanCreditBalance()
        val offerings = RevenueCatManager.getOfferings()
        val pkg = offerings.current?.availablePackages?.firstOrNull()
        assertNotNull("Test Store offering must have at least one package", pkg)

        val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())

        coroutineScope {
            // Must launch on the main thread - confirmed hands-on
            // 2026-08-23: calling purchasePackage from the instrumentation
            // thread (runBlocking/async's default dispatcher here) never
            // shows the Test Store dialog at all, even with a generous
            // wait; a real button tap (which always runs on main) shows it
            // instantly. RevenueCat's purchase flow apparently requires
            // main-thread invocation to launch its confirmation UI.
            val purchase = async(Dispatchers.Main) { RevenueCatManager.purchasePackage(composeRule.activity, pkg!!) }
            val validPurchaseButton = device.wait(Until.findObject(By.res("android:id/button1")), 10_000)
            assertNotNull("Expected the Test Store's confirmation dialog to appear", validPurchaseButton)
            validPurchaseButton.click()
            purchase.await()
        }

        val balanceAfter = RevenueCatManager.getScanCreditBalance()
        println("[WeeklyTest] purchase balance: $balanceBefore -> $balanceAfter")
        assertTrue(
            "Balance should increase after a real purchase (was $balanceBefore, now $balanceAfter)",
            balanceAfter > balanceBefore,
        )
    }

    @Test
    fun realScanDecrementsBalance() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().context
        val imageBytes = context.assets.open("AddieTag.jpg").use { it.readBytes() }
        val imageBase64 = Base64.encodeToString(imageBytes, Base64.NO_WRAP)

        val balanceBefore = RevenueCatManager.getScanCreditBalance()
        val result = ScanApiClient.scan(RevenueCatManager.appUserId, EntryModule.TRUCK, imageBase64)

        val success = result as? ScanResult.Success
        assertNotNull("Expected a successful scan, got: $result", success)
        assertTrue("Scan should return non-empty fields", success!!.fields.isNotEmpty())

        val balanceAfter = RevenueCatManager.getScanCreditBalance()
        println("[WeeklyTest] scan balance: $balanceBefore -> $balanceAfter")
        assertEquals(balanceBefore - 1, balanceAfter)
    }

    // Hands-on verification for roadmap item #5, Gap B: proves the
    // client_request_id -> RevenueCat Idempotency-Key wiring actually
    // dedupes against the real RevenueCat API, not just against fake deps
    // in scan.test.ts. Two full round trips to the real deployed Worker
    // (two real ~$0.01 Claude calls - the accepted residual-cost tradeoff
    // documented in NEXT_STEPS.md item #5, since the Worker stays
    // stateless and can't cache the extraction result) with the SAME
    // client-generated id must still only move the RevenueCat balance by 1.
    @Test
    fun realDuplicateScanWithSameClientRequestIdSpendsOnce() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().context
        val imageBytes = context.assets.open("AddieTag.jpg").use { it.readBytes() }
        val imageBase64 = Base64.encodeToString(imageBytes, Base64.NO_WRAP)
        val sharedClientRequestId = "weekly-idempotency-check-${System.currentTimeMillis()}"

        val balanceBefore = RevenueCatManager.getScanCreditBalance()

        val first = ScanApiClient.scan(
            RevenueCatManager.appUserId,
            EntryModule.TRUCK,
            imageBase64,
            clientRequestId = sharedClientRequestId,
        )
        assertNotNull("Expected the first scan to succeed, got: $first", first as? ScanResult.Success)

        val second = ScanApiClient.scan(
            RevenueCatManager.appUserId,
            EntryModule.TRUCK,
            imageBase64,
            clientRequestId = sharedClientRequestId,
        )
        assertNotNull("Expected the retried scan to succeed too, got: $second", second as? ScanResult.Success)

        val balanceAfter = RevenueCatManager.getScanCreditBalance()
        println("[WeeklyTest] duplicate-idempotency-key balance: $balanceBefore -> $balanceAfter")
        assertEquals(
            "Two scans sharing one client_request_id must spend exactly once against real RevenueCat",
            balanceBefore - 1,
            balanceAfter,
        )
    }
}
