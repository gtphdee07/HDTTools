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

// TESTING-PHASE ONLY: identifies every install as the one known RevenueCat
// test customer (already has a real SCAN balance, verified server-side
// 2026-08-17) rather than letting the SDK generate a fresh per-install
// anonymous ID. Must change before any real release - swap back to the
// default anonymous-ID behavior (drop .appUserID(...) entirely) once
// Phase 4 moves past manual testing.
private const val TESTING_APP_USER_ID = "smoke-test-user"

class RigCheckApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Purchases.logLevel = LogLevel.DEBUG
        Purchases.configure(
            PurchasesConfiguration.Builder(this, REVENUECAT_PUBLIC_API_KEY)
                .appUserID(TESTING_APP_USER_ID)
                .build(),
        )
    }
}
