package com.rigcheck.app

import android.app.Application
import android.content.Context
import androidx.test.runner.AndroidJUnitRunner

// Instrumented tests run inside the real app process, which would
// otherwise instantiate the real RigCheckApplication and call
// Purchases.configure() against RevenueCat's Test Store on every test run
// - hitting real network and sharing smoke-test-user's balance with
// manual field testing. Substituting a plain Application here keeps the
// daily-tier test suite offline and hermetic: RigCheckViewModel's
// refreshCreditBalance() and PaywallScreen's getOfferings() call are
// already wrapped in runCatching/onFailure, so an unconfigured
// Purchases.sharedInstance fails gracefully into an empty/error UI state
// instead of crashing. Wired via testInstrumentationRunner in
// app/build.gradle.kts.
class CustomTestRunner : AndroidJUnitRunner() {
    override fun newApplication(cl: ClassLoader?, className: String?, context: Context?): Application =
        super.newApplication(cl, Application::class.java.name, context)
}
