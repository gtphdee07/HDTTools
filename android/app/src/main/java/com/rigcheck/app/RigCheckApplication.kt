package com.rigcheck.app

import android.app.Application
import com.revenuecat.purchases.LogLevel
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesConfiguration

// RevenueCat's PUBLIC SDK key - safe to embed in app code (this is what
// "public key" means for RevenueCat: extractable from the APK trivially,
// unlike the Worker's secret key which must never appear here). This is
// specifically the Test Store key from the RevenueCat dashboard's
// "Install the SDK" screen, not a production key.
private const val REVENUECAT_PUBLIC_API_KEY = "test_LFhGCYRgSfTFUpYRaWkEakLWOdS"

class RigCheckApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Purchases.logLevel = LogLevel.DEBUG
        // No app user id here: RevenueCat starts anonymous, and AccountManager
        // logs the signed-in account's id in (and back out) so purchases land
        // on the shared account (#22). The old shared "smoke-test-user" id
        // is gone - a signed-in account now owns its own SCAN balance.
        Purchases.configure(PurchasesConfiguration.Builder(this, REVENUECAT_PUBLIC_API_KEY).build())
    }
}
