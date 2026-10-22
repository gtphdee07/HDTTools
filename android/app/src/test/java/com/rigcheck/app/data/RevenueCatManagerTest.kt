@file:OptIn(InternalRevenueCatAPI::class)

package com.rigcheck.app.data

import com.revenuecat.purchases.CacheFetchPolicy
import com.revenuecat.purchases.CustomerInfo
import com.revenuecat.purchases.EntitlementInfo
import com.revenuecat.purchases.EntitlementInfos
import com.revenuecat.purchases.InternalRevenueCatAPI
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesError
import com.revenuecat.purchases.PurchasesErrorCode
import com.revenuecat.purchases.interfaces.GetVirtualCurrenciesCallback
import com.revenuecat.purchases.interfaces.ReceiveCustomerInfoCallback
import com.revenuecat.purchases.virtualcurrencies.VirtualCurrencies
import com.revenuecat.purchases.virtualcurrencies.VirtualCurrency
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkObject
import io.mockk.unmockkAll
import io.mockk.verify
import io.mockk.verifyOrder
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test

// The bug this file exists to catch is exactly the one that made it to
// on-device testing on 2026-08-18: the RevenueCat SDK caches virtual-
// currency balance client-side, but scan-proxy's Worker deducts/refunds
// credits via a direct server-side REST call, never through this SDK's own
// purchase flow - so the cache has no way to know a balance changed unless
// invalidateVirtualCurrenciesCache() is called first. That bug shipped once
// and was only caught by a real on-device scan; these tests would have
// caught it without a device.
class RevenueCatManagerTest {

    private val purchases = mockk<Purchases>(relaxed = true)

    @Before
    fun setUp() {
        // Purchases.sharedInstance is Purchases.Companion.getSharedInstance()
        // under the hood - mockkObject on the companion is what actually
        // intercepts it; mockkStatic(Purchases::class) does not, and silently
        // lets the real getter run (which throws unless Purchases.configure()
        // has been called - never true in a plain JVM unit test).
        mockkObject(Purchases.Companion)
        every { Purchases.sharedInstance } returns purchases
    }

    @After
    fun tearDown() {
        unmockkAll()
    }

    // VirtualCurrency/VirtualCurrencies are plain constructible value types
    // (no interesting behavior of their own) - real instances are simpler
    // and more robust here than mocking them.
    private fun virtualCurrenciesWithBalance(code: String, balance: Int): VirtualCurrencies =
        VirtualCurrencies(mapOf(code to VirtualCurrency(balance, "Scan Credits", code, "Test currency")))

    // Stubs the real callback-based getVirtualCurrencies(...), not the
    // awaitGetVirtualCurrencies() suspend extension function
    // RevenueCatManager actually calls. Mocking that suspend extension
    // directly via MockK's coEvery/mockkStatic deadlocked twice while
    // developing this file (confirmed via thread dumps both times - MockK's
    // suspend-call recording internally uses its own runBlocking, which
    // parks the test thread waiting on itself). Mocking the plain callback
    // method the extension is built on sidesteps that machinery entirely:
    // RevenueCatManager's real (unmocked) awaitGetVirtualCurrencies() still
    // runs and bridges this callback into a suspend result exactly as it
    // does in production.
    private fun stubVirtualCurrencies(result: VirtualCurrencies) {
        every { purchases.getVirtualCurrencies(any()) } answers {
            firstArg<GetVirtualCurrenciesCallback>().onReceived(result)
        }
    }

    @Test
    fun `invalidates the virtual-currencies cache before reading the balance, not after`() {
        stubVirtualCurrencies(virtualCurrenciesWithBalance("SCAN", 5))

        runBlocking { RevenueCatManager.getScanCreditBalance() }

        verifyOrder {
            purchases.invalidateVirtualCurrenciesCache()
            purchases.getVirtualCurrencies(any())
        }
    }

    @Test
    fun `returns the SCAN currency's balance`() {
        stubVirtualCurrencies(virtualCurrenciesWithBalance("SCAN", 42))

        val balance = runBlocking { RevenueCatManager.getScanCreditBalance() }

        assertEquals(42, balance)
    }

    @Test
    fun `returns 0 when the SCAN currency isn't present at all`() {
        stubVirtualCurrencies(VirtualCurrencies(emptyMap()))

        val balance = runBlocking { RevenueCatManager.getScanCreditBalance() }

        assertEquals(0, balance)
    }

    // CustomerInfo and its entitlements are large SDK types built from a server
    // reply, so the test states only what isPro reads: which entitlements are active.
    private fun customerWithActiveEntitlements(vararg ids: String): CustomerInfo {
        val active = ids.associateWith { mockk<EntitlementInfo>() }
        val entitlements = mockk<EntitlementInfos> { every { this@mockk.active } returns active }
        return mockk { every { this@mockk.entitlements } returns entitlements }
    }

    private fun stubCustomerInfo(info: CustomerInfo) {
        every { purchases.getCustomerInfo(any<CacheFetchPolicy>(), any()) } answers {
            secondArg<ReceiveCustomerInfoCallback>().onReceived(info)
        }
    }

    @Test
    fun `isPro is true when the pro entitlement is active, however it was bought`() {
        stubCustomerInfo(customerWithActiveEntitlements("pro"))

        assertEquals(true, runBlocking { RevenueCatManager.isPro() })
    }

    @Test
    fun `isPro is false when only some other entitlement is active`() {
        stubCustomerInfo(customerWithActiveEntitlements("something_else"))

        assertEquals(false, runBlocking { RevenueCatManager.isPro() })
    }

    @Test
    fun `isPro is false for a customer with no active entitlement`() {
        stubCustomerInfo(customerWithActiveEntitlements())

        assertEquals(false, runBlocking { RevenueCatManager.isPro() })
    }

    // A Pro bought on Web reaches RevenueCat's server, not this device's cache,
    // so the cached customer would keep showing Free until it expired.
    @Test
    fun `isPro asks for the current customer, not the cached one`() {
        stubCustomerInfo(customerWithActiveEntitlements("pro"))

        runBlocking { RevenueCatManager.isPro() }

        verify { purchases.getCustomerInfo(CacheFetchPolicy.FETCH_CURRENT, any()) }
    }

    @Test
    fun `isPro fails rather than guess Free when the customer cannot be fetched`() {
        every { purchases.getCustomerInfo(any<CacheFetchPolicy>(), any()) } answers {
            secondArg<ReceiveCustomerInfoCallback>().onError(PurchasesError(PurchasesErrorCode.NetworkError))
        }

        val failure = runCatching { runBlocking { RevenueCatManager.isPro() } }.exceptionOrNull()

        assertNotNull(failure)
    }

    @Test
    fun `isAnonymous reads straight through to Purchases sharedInstance`() {
        every { purchases.isAnonymous } returns false

        assertEquals(false, RevenueCatManager.isAnonymous)
    }
}
