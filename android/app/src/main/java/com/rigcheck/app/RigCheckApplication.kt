package com.rigcheck.app

import android.app.Application
import com.revenuecat.purchases.LogLevel
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesConfiguration

class RigCheckApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Purchases.logLevel = LogLevel.DEBUG
        // No app user id here: RevenueCat starts anonymous, and AccountManager
        // logs the signed-in account's id in (and back out) so purchases land
        // on the shared account (#22). The old shared "smoke-test-user" id
        // is gone - a signed-in account now owns its own SCAN balance.
        //
        // The key is RevenueCat's PUBLIC SDK key (safe to embed: extractable from
        // the APK, unlike the Worker's secret key). Debug builds get the Test
        // Store key; a release build takes the production key and fails to build
        // without one (verifyRevenueCatReleaseKey in app/build.gradle.kts, #166).
        Purchases.configure(PurchasesConfiguration.Builder(this, BuildConfig.REVENUECAT_PUBLIC_API_KEY).build())
    }
}
