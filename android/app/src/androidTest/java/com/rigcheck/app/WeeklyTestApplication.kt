package com.rigcheck.app

import android.app.Application
import com.revenuecat.purchases.LogLevel
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesConfiguration

// Mirrors RigCheckApplication.kt's real onCreate() exactly, except the
// app user id - weekly-test-user instead of smoke-test-user. Lives in
// androidTest only, never shipped. The public key is duplicated here
// (not hoisted out of RigCheckApplication.kt) so the two onCreate()
// bodies diff cleanly against each other; it's a RevenueCat *public* SDK
// key, already exempt from any secrecy rule.
private const val REVENUECAT_PUBLIC_API_KEY = "test_LFhGCYRgSfTFUpYRaWkEakLWOdS"

// Dedicated Weekly-tier RevenueCat test customer (real SCAN balance +
// RigCheck Pro entitlement, created 2026-08-21 - see
// workers/scan-proxy/TESTING.md for how it was created). Never
// smoke-test-user - reserved for manual field testing, its balance gets
// hand-edited too often to be a reliable automated fixture.
private const val WEEKLY_TEST_APP_USER_ID = "weekly-test-user"

class WeeklyTestApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Purchases.logLevel = LogLevel.DEBUG
        Purchases.configure(
            PurchasesConfiguration.Builder(this, REVENUECAT_PUBLIC_API_KEY)
                .appUserID(WEEKLY_TEST_APP_USER_ID)
                .build(),
        )
    }
}
