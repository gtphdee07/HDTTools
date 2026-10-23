package com.rigcheck.app.testsupport

import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.revenuecat.purchases.PresentedOfferingContext
import com.revenuecat.purchases.ProductType
import com.revenuecat.purchases.models.Period
import com.revenuecat.purchases.models.Price
import com.revenuecat.purchases.models.PurchasingData
import com.revenuecat.purchases.models.StoreProduct
import com.revenuecat.purchases.models.SubscriptionOption
import com.revenuecat.purchases.models.SubscriptionOptions

// A RevenueCat product with nothing behind it, so a screen test can hand the
// Paywall an Offering without Purchases.configure() or a network. Only what the
// Paywall reads (title, description, price, type) is meaningful.
private class FakeStoreProduct(
    override val id: String,
    override val type: ProductType,
    override val title: String,
    override val description: String,
    priceText: String,
) : StoreProduct {
    override val price = Price(priceText, 1_000_000L, "USD")
    override val name = title
    override val period: Period? = null
    override val subscriptionOptions: SubscriptionOptions? = null
    override val defaultOption: SubscriptionOption? = null
    override val purchasingData = object : PurchasingData {
        override val productId = id
        override val productType = type
    }

    @Deprecated("Replaced with presentedOfferingContext")
    override val presentedOfferingIdentifier: String? = null
    override val presentedOfferingContext: PresentedOfferingContext? = null

    @Deprecated("Replaced with id")
    override val sku = id

    @Deprecated("Replaced with copyWithPresentedOfferingContext")
    override fun copyWithOfferingId(offeringId: String): StoreProduct = this

    override fun copyWithPresentedOfferingContext(presentedOfferingContext: PresentedOfferingContext?): StoreProduct = this
}

fun fakePackage(
    id: String,
    packageType: PackageType,
    title: String,
    price: String,
    description: String = "",
    productType: ProductType = ProductType.INAPP,
): Package = Package(
    id,
    packageType,
    FakeStoreProduct(id, productType, title, description, price),
    PresentedOfferingContext("default"),
)
