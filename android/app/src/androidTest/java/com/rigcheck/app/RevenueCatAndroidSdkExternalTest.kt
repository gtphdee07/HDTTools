package com.rigcheck.app

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.revenuecat.purchases.CacheFetchPolicy
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.awaitCustomerInfo
import com.revenuecat.purchases.awaitGetVirtualCurrencies
import com.revenuecat.purchases.awaitLogIn
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.paywallOffers
import com.rigcheck.app.testsupport.ExternalSurface
import com.rigcheck.app.testsupport.weeklyAccountIdFromMarker
import com.rigcheck.app.testsupport.whileOffline
import com.rigcheck.app.ui.screens.PaywallScreen
import java.io.File
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import com.rigcheck.app.ui.UiTags
import androidx.compose.ui.test.onNodeWithTag

// External suite, surface `revenuecat-android-sdk` (ADR-0008, #39): what the
// RevenueCat Android SDK really returns to RevenueCatManager.kt, against the
// funded Supabase test account's RevenueCat customer (#75). Started only by
// android/test-external.ps1 - it writes the weekly marker file that makes
// CustomTestRunner configure the real SDK, and refuses to start without a
// device that has Google Play Services. Excluded from connectedDebugAndroidTest
// by build.gradle.kts (notAnnotation ExternalSurface).
//
// Never makes a purchase and never spends a scan, so it costs nothing (the
// manifest's max_paid_calls is 0). PaywallScreenWeeklyTest keeps the Test Store
// purchase and the Worker scans; it is the old weekly suite and is untouched.
//
// Depth, per the ticket:
//  - reachable and authenticated: configuredSdkAuthenticatesAsTheFundedAccount
//  - response shape: offeringsCarryTheFieldsThePaywallReads,
//    scanBalanceIsReadFromTheScanCurrency
//  - error contracts: unknownUserHasAnEmptyScanBalance,
//    offlineReadsComeFromTheCacheAndNetworkCallsFailWithAMessage
//  - journey (load paywall, fetch offerings, restore): paywallLoadsOfferingsThenRestores
@ExternalSurface("revenuecat-android-sdk")
@RunWith(AndroidJUnit4::class)
class RevenueCatAndroidSdkExternalTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    private val fundedAccountId: String
        get() = weeklyAccountIdFromMarker(File(WEEKLY_MARKER_PATH).readText())

    @Test
    fun configuredSdkAuthenticatesAsTheFundedAccount() = runBlocking {
        // A fresh fetch (not the cache) proves the configured key is accepted by
        // RevenueCat for this customer, not just that the SDK started.
        val info = Purchases.sharedInstance.awaitCustomerInfo(CacheFetchPolicy.FETCH_CURRENT)
        assertEquals(fundedAccountId, info.originalAppUserId)
        assertFalse("The funded account must not be an anonymous customer", Purchases.sharedInstance.isAnonymous)
    }

    @Test
    fun offeringsCarryTheFieldsThePaywallReads() = runBlocking {
        val offerings = RevenueCatManager.getOfferings()
        val current = offerings.current
        assertNotNull("RevenueCat returned no current offering for the project", current)
        assertTrue("The current offering has no packages", current!!.availablePackages.isNotEmpty())
        // PaywallScreen renders the title and the formatted price of every package (the
        // description is optional there: it is shown only when not blank).
        for (pkg in current.availablePackages) {
            assertTrue("package ${pkg.identifier} has no product title", pkg.product.title.isNotBlank())
            assertTrue("package ${pkg.identifier} has no formatted price", pkg.product.price.formatted.isNotBlank())
        }
    }

    @Test
    fun scanBalanceIsReadFromTheScanCurrency() = runBlocking {
        // getScanCreditBalance reads currency code "SCAN" and treats a missing one
        // as zero, so a renamed or removed currency would silently show 0 scans.
        val currencies = Purchases.sharedInstance.awaitGetVirtualCurrencies()
        val scan = currencies.get("SCAN")
        assertNotNull("RevenueCat's virtual currencies for the funded account have no SCAN entry", scan)
        assertTrue("SCAN balance must not be negative", scan!!.balance >= 0)
        assertEquals(scan.balance, RevenueCatManager.getScanCreditBalance())
    }

    @Test
    fun unknownUserHasAnEmptyScanBalance() = runBlocking {
        // RevenueCat creates a customer the first time it sees an id; the app
        // relies on that new customer reading as zero scans and no purchases,
        // not as an error. The id is fixed so reruns reuse one customer.
        try {
            Purchases.sharedInstance.awaitLogIn(UNKNOWN_USER_ID)
            assertEquals(0, RevenueCatManager.getScanCreditBalance())
            val info = Purchases.sharedInstance.awaitCustomerInfo(CacheFetchPolicy.FETCH_CURRENT)
            assertEquals(UNKNOWN_USER_ID, info.originalAppUserId)
            assertTrue("A new customer must have no entitlements", info.entitlements.active.isEmpty())
        } finally {
            Purchases.sharedInstance.awaitLogIn(fundedAccountId)
        }
    }

    @Test
    fun offlineReadsComeFromTheCacheAndNetworkCallsFailWithAMessage() = runBlocking {
        // Measured on the emulator with the Test Store key (2026-10-20): offline, the
        // SDK answers offerings and restore from its cache, while a fresh customer
        // fetch and a login for an id it has not seen fail with a PurchasesException
        // ("Error performing request."). RigCheckViewModel and AccountManager show
        // that message as is, so it must exist and the call must not hang. (The scan
        // balance is left out on purpose: whether it errors or serves the disk
        // cache offline varied between two otherwise identical runs.)
        val onlineTitles = RevenueCatManager.getOfferings().current!!.availablePackages.map { it.product.title }
        whileOffline {
            val offlineTitles = RevenueCatManager.getOfferings().current?.availablePackages?.map { it.product.title }
            assertEquals("Offline offerings should come from the SDK's cache", onlineTitles, offlineTitles)
            // The Test Store has no store-side restore, so this returns the cached customer.
            assertEquals(fundedAccountId, RevenueCatManager.restorePurchases().originalAppUserId)

            val fetchError = failureOf { Purchases.sharedInstance.awaitCustomerInfo(CacheFetchPolicy.FETCH_CURRENT) }
            assertFalse("offline customer fetch failed without a message", fetchError.message.isNullOrBlank())
            val loginError = failureOf { RevenueCatManager.logIn(OFFLINE_USER_ID) }
            assertFalse("offline login failed without a message", loginError.message.isNullOrBlank())
            assertEquals("A failed login must leave the funded account in place", fundedAccountId, Purchases.sharedInstance.appUserID)
        }
    }

    @Test
    fun paywallLoadsOfferingsThenRestores() {
        runBlocking {
            // The paywall offers scan packs to a Pro account only (#101), so it renders as one.
            val expectedTitle = paywallOffers(RevenueCatManager.getOfferings().current!!.availablePackages)
                .scanPacks.first().product.title
            val restore = AtomicReference<Pair<Boolean, String?>>()

            composeRule.setContent {
                PaywallScreen(
                    creditBalance = null,
                    isPro = true,
                    onPurchase = { _, _ -> },
                    // The same call RigCheckViewModel.restorePurchases makes.
                    onRestore = { report ->
                        CoroutineScope(Dispatchers.Main).launch {
                            val result = runCatching { RevenueCatManager.restorePurchases() }
                            val error = result.exceptionOrNull()?.message
                            restore.set(result.isSuccess to error)
                            report(result.isSuccess, error)
                        }
                    },
                    onDone = { },
                )
            }

            composeRule.waitUntil(timeoutMillis = 15_000) {
                composeRule.onAllNodesWithText(expectedTitle, substring = true).fetchSemanticsNodes().isNotEmpty() ||
                    composeRule.onAllNodesWithTag(UiTags.PAYWALL_LOAD_ERROR).fetchSemanticsNodes().isNotEmpty()
            }
            assertTrue(
                "The paywall showed its load error instead of the offerings",
                composeRule.onAllNodesWithTag(UiTags.PAYWALL_LOAD_ERROR).fetchSemanticsNodes().isEmpty(),
            )
            composeRule.onNodeWithText(expectedTitle, substring = true).assertIsDisplayed()

            composeRule.onNodeWithTag(UiTags.PAYWALL_RESTORE_BUTTON).performClick()
            composeRule.waitUntil(timeoutMillis = 30_000) { restore.get() != null }
            val (success, error) = restore.get()
            assertTrue("Restore failed: $error", success)
            // RigCheckViewModel discards the CustomerInfo, so all the app can depend on is
            // which customer it describes.
            assertEquals(fundedAccountId, RevenueCatManager.restorePurchases().originalAppUserId)
        }
    }

    // The exception `block` fails with, or a test failure if it succeeds.
    private suspend fun failureOf(block: suspend () -> Any?): Throwable {
        try {
            withTimeout(OFFLINE_CALL_TIMEOUT_MS) { block() }
        } catch (e: TimeoutCancellationException) {
            fail("The call hung for ${OFFLINE_CALL_TIMEOUT_MS}ms while offline instead of failing")
        } catch (e: Exception) {
            return e
        }
        fail("Expected the call to fail while offline, but it succeeded")
        throw AssertionError("unreachable")
    }

    private companion object {
        const val UNKNOWN_USER_ID = "external-test-unknown-user"
        const val OFFLINE_USER_ID = "external-test-offline-user"
        const val OFFLINE_CALL_TIMEOUT_MS = 30_000L
    }
}
