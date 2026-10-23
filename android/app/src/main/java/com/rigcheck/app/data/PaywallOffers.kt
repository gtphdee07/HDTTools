package com.rigcheck.app.data

import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.revenuecat.purchases.ProductType

// What the Paywall can sell from the current Offering: the Pro unlock, and the
// scan packs that only a Pro account may buy (ADR-0006's 2026-10-12 amendment).
class PaywallOffers(
    val proUnlock: Package?,
    val scanPacks: List<Package>,
)

// Tells the two kinds of package apart by what RevenueCat reports about each,
// never by product id or price (both are the dashboard's to change). Pro is the
// Offering's lifetime package, the same package Web sells as Pro. A scan pack is
// any other one-time (in-app) package: the Android SDK reports in-app versus
// subscription but not consumable versus non-consumable, so "not the lifetime
// package" is what separates a pack from Pro. A subscription is neither.
fun paywallOffers(packages: List<Package>): PaywallOffers = PaywallOffers(
    proUnlock = packages.firstOrNull { it.packageType == PackageType.LIFETIME },
    scanPacks = packages.filter { it.packageType != PackageType.LIFETIME && it.product.type == ProductType.INAPP },
)
