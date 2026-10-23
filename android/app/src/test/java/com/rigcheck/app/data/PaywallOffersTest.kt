package com.rigcheck.app.data

import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.revenuecat.purchases.PresentedOfferingContext
import com.revenuecat.purchases.ProductType
import com.revenuecat.purchases.models.StoreProduct
import io.mockk.every
import io.mockk.mockk
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

// Which packages in the Offering are Pro and which are scan packs (#101). The
// split must come from what RevenueCat reports about each package, never from
// product ids or prices, so each package here has an arbitrary id and the tests
// vary only the reported package and product types.
class PaywallOffersTest {

    private fun pkg(id: String, packageType: PackageType, productType: ProductType = ProductType.INAPP): Package {
        val product = mockk<StoreProduct>()
        every { product.type } returns productType
        return Package(id, packageType, product, PresentedOfferingContext("default"))
    }

    @Test
    fun `the lifetime package is Pro and the other one-time packages are scan packs`() {
        val pro = pkg("anything-1", PackageType.LIFETIME)
        val small = pkg("anything-2", PackageType.CUSTOM)
        val large = pkg("anything-3", PackageType.CUSTOM)

        val offers = paywallOffers(listOf(small, pro, large))

        assertEquals(pro, offers.proUnlock)
        assertEquals(listOf(small, large), offers.scanPacks)
    }

    @Test
    fun `Pro is never also a scan pack`() {
        val pro = pkg("anything-1", PackageType.LIFETIME)

        assertEquals(emptyList<Package>(), paywallOffers(listOf(pro)).scanPacks)
    }

    @Test
    fun `an offering with no lifetime package has nothing to unlock Pro with`() {
        val offers = paywallOffers(listOf(pkg("anything-1", PackageType.CUSTOM)))

        assertNull(offers.proUnlock)
    }

    @Test
    fun `a subscription is neither Pro nor a scan pack`() {
        val monthly = pkg("anything-1", PackageType.MONTHLY, ProductType.SUBS)

        val offers = paywallOffers(listOf(monthly))

        assertNull(offers.proUnlock)
        assertEquals(0, offers.scanPacks.size)
    }

    @Test
    fun `an empty offering offers nothing`() {
        val offers = paywallOffers(emptyList())

        assertNull(offers.proUnlock)
        assertEquals(0, offers.scanPacks.size)
    }
}
