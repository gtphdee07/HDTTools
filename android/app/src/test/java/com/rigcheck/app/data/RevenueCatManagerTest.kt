@file:OptIn(InternalRevenueCatAPI::class)

package com.rigcheck.app.data

import com.revenuecat.purchases.InternalRevenueCatAPI
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.interfaces.GetVirtualCurrenciesCallback
import com.revenuecat.purchases.virtualcurrencies.VirtualCurrencies
import com.revenuecat.purchases.virtualcurrencies.VirtualCurrency
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkObject
import io.mockk.unmockkAll
import io.mockk.verifyOrder
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
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

    @Test
    fun `appUserId reads straight through to Purchases sharedInstance`() {
        every { purchases.appUserID } returns "smoke-test-user"

        assertEquals("smoke-test-user", RevenueCatManager.appUserId)
    }
}
