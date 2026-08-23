package com.rigcheck.app

import android.app.Application
import android.content.Context
import androidx.test.runner.AndroidJUnitRunner
import java.io.File

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
//
// The weekly tier (real RevenueCat, PaywallScreenWeeklyTest.kt) reuses
// this same runner rather than a second one - AGP's manifest merger only
// allows one <instrumentation> element per test APK (confirmed hands-on
// 2026-08-23: a second manifest-declared <instrumentation> silently folds
// its attributes into this one instead of registering as an invocable
// component). An instrumentation-args-based branch (-e weekly true) was
// tried next and also doesn't work: newApplication() fires *before*
// AndroidJUnitRunner.onCreate(Bundle) in this environment (confirmed via
// timestamped logging - newApplication ran first, contradicting the
// documented order), so no instrumentation-args mechanism can be read in
// time. The reliable fix is a device-side marker file, checked with plain
// synchronous file I/O that has no lifecycle-ordering dependency at all:
// test-weekly.ps1 touches WEEKLY_MARKER_PATH via `adb shell` before
// invoking `am instrument`, and removes it afterward so a later
// ./gradlew connectedDebugAndroidTest run never sees it.
private const val WEEKLY_MARKER_PATH = "/data/local/tmp/rigcheck_weekly_mode"

class CustomTestRunner : AndroidJUnitRunner() {
    override fun newApplication(cl: ClassLoader?, className: String?, context: Context?): Application {
        val applicationClassName = if (File(WEEKLY_MARKER_PATH).exists()) {
            WeeklyTestApplication::class.java.name
        } else {
            Application::class.java.name
        }
        return super.newApplication(cl, applicationClassName, context)
    }
}
