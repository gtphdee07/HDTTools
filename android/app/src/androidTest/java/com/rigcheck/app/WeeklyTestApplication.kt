package com.rigcheck.app

import android.app.Application
import com.revenuecat.purchases.LogLevel
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesConfiguration
import com.rigcheck.app.testsupport.weeklyAccountIdFromMarker
import java.io.File

// Mirrors RigCheckApplication.kt's real onCreate(), except it pins the
// app user id to the funded Supabase test account (production starts
// anonymous and logs the signed-in account in). Lives in
// androidTest only, never shipped. The public key is duplicated here
// (not hoisted out of RigCheckApplication.kt) so the two onCreate()
// bodies diff cleanly against each other; it's a RevenueCat *public* SDK
// key, already exempt from any secrecy rule.
private const val REVENUECAT_PUBLIC_API_KEY = "test_LFhGCYRgSfTFUpYRaWkEakLWOdS"

// The funded test account's id (its Supabase UUID, which is also its
// RevenueCat customer - set up by scripts/wizard_scan_proxy_live_accounts.sh,
// holding a real SCAN balance). test-weekly.ps1 writes it into the marker
// file CustomTestRunner already checks, because this class runs before
// instrumentation arguments can be read. Never smoke-test-user - reserved
// for manual field testing, its balance gets hand-edited too often to be
// a reliable automated fixture.
class WeeklyTestApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Purchases.logLevel = LogLevel.DEBUG
        Purchases.configure(
            PurchasesConfiguration.Builder(this, REVENUECAT_PUBLIC_API_KEY)
                .appUserID(weeklyAccountIdFromMarker(File(WEEKLY_MARKER_PATH).readText()))
                .build(),
        )
    }
}
