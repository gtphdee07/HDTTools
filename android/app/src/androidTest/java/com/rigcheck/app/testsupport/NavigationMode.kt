package com.rigcheck.app.testsupport

import android.app.Instrumentation
import android.os.Build
import androidx.test.uiautomator.UiDevice

// Puts the device on 3-button navigation for a test and back where it was (#197): the system-bar rule is only proven on
// the bar that takes room (SystemBarsTest, TESTING.md "System bar tests"). Like DisplayFrame, a test calls use3Buttons()
// before it launches an activity and restore() in an @After; restore() is safe when nothing was changed.
class NavigationMode(instrumentation: Instrumentation) {
    private val device = UiDevice.getInstance(instrumentation)
    private var changedFrom: String? = null

    fun use3Buttons() {
        val current = mode()
        if (current == THREE_BUTTON) return
        // Android 8.0 to 9 (API 26 to 28) has no navigation_mode setting and no navigation overlay: the phone always shows
        // the on-screen bar, so it is already on 3-button navigation and there is nothing to change or restore (#225).
        // From API 29 a missing reading is not trusted: it falls through to the overlay path and fails loudly there.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q && current.isNavigationModeMissing()) return
        changedFrom = overlayOf(current)
        device.executeShellCommand("cmd overlay enable $THREE_BUTTON_OVERLAY")
        awaitMode(THREE_BUTTON)
    }

    fun restore() {
        val overlay = changedFrom ?: return
        changedFrom = null
        device.executeShellCommand("cmd overlay enable $overlay")
    }

    // 0 = 3-button, 1 = 2-button, 2 = gestures (Settings.Secure navigation_mode).
    private fun mode(): String = device.executeShellCommand("settings get secure navigation_mode").trim()

    // `settings get` prints the word "null" for a setting that does not exist.
    private fun String.isNavigationModeMissing(): Boolean = isEmpty() || this == "null"

    private fun overlayOf(mode: String): String = when (mode) {
        "0" -> THREE_BUTTON_OVERLAY
        "1" -> "com.android.internal.systemui.navbar.twobutton"
        else -> "com.android.internal.systemui.navbar.gestural"
    }

    private fun awaitMode(wanted: String) {
        val deadline = System.currentTimeMillis() + SETTLE_MS
        while (mode() != wanted) {
            check(System.currentTimeMillis() < deadline) { "the navigation mode did not become $wanted (it is ${mode()})" }
            Thread.sleep(POLL_MS)
        }
        // The bar is drawn a moment after the setting changes.
        Thread.sleep(BAR_MS)
        device.waitForIdle()
    }

    private companion object {
        const val THREE_BUTTON = "0"
        const val THREE_BUTTON_OVERLAY = "com.android.internal.systemui.navbar.threebutton"
        const val SETTLE_MS = 15_000L
        const val POLL_MS = 200L
        const val BAR_MS = 1_500L
    }
}
