package com.rigcheck.app.layoutcapture

import android.app.Instrumentation
import androidx.test.uiautomator.UiDevice
import kotlin.math.roundToInt

// A phone frame for the layout capture (#189): the size of the screen in dp, and the system font scale.
// 400 dpi is 2.5 px per dp, so both reference frames are a whole number of pixels (412 x 892 dp is
// 1030 x 2230 px, 360 x 640 dp is 900 x 1600 px) and every bound in the capture is a multiple of 0.4 dp.
data class Frame(val widthDp: Int, val heightDp: Int, val fontScale: Float = 1f) {
    val name: String get() = "${widthDp}x$heightDp" + if (fontScale == 1f) "" else "-font$fontScale"
    val widthPx: Int get() = (widthDp * PX_PER_DP).roundToInt()
    val heightPx: Int get() = (heightDp * PX_PER_DP).roundToInt()

    companion object {
        const val DPI = 400
        const val PX_PER_DP = DPI / 160.0
    }
}

// Puts the device's display into a Frame and puts it back. The window of the app is then exactly the frame, with the
// real status bar and navigation bar and the insets the app itself handles, so a dialog is centred in the frame and
// a screenshot of the display is the frame. Apply before an activity is launched: a launched activity is recreated
// by the change. reset() is safe to call when nothing was applied.
class DisplayFrame(instrumentation: Instrumentation) {
    private val device = UiDevice.getInstance(instrumentation)
    private var originalFontScale: String? = null
    private var applied = false

    fun apply(frame: Frame) {
        if (!applied) originalFontScale = device.executeShellCommand("settings get system font_scale").trim()
        applied = true
        device.executeShellCommand("wm size ${frame.widthPx}x${frame.heightPx}")
        device.executeShellCommand("wm density ${Frame.DPI}")
        device.executeShellCommand("settings put system font_scale ${frame.fontScale}")
        val deadline = System.currentTimeMillis() + SETTLE_MS
        while (device.displayWidth != frame.widthPx || device.displayHeight != frame.heightPx) {
            check(System.currentTimeMillis() < deadline) {
                "the display did not become ${frame.widthPx}x${frame.heightPx} px (it is " +
                    "${device.displayWidth}x${device.displayHeight})"
            }
            Thread.sleep(POLL_MS)
        }
        device.waitForIdle()
    }

    fun reset() {
        if (!applied) return
        device.executeShellCommand("wm size reset")
        device.executeShellCommand("wm density reset")
        val original = originalFontScale
        if (original.isNullOrEmpty() || original == "null") {
            device.executeShellCommand("settings delete system font_scale")
        } else {
            device.executeShellCommand("settings put system font_scale $original")
        }
        applied = false
    }

    private companion object {
        const val SETTLE_MS = 15_000L
        const val POLL_MS = 200L
    }
}
