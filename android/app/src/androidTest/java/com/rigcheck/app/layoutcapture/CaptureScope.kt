package com.rigcheck.app.layoutcapture

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.junit4.ComposeTestRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.testsupport.scrollToIfScrollable

// What a CaptureCase's setUp can do to put its screen into the state: the Compose test rule (taps and typing, found by
// UiTags tag) and the soft keyboard.
class CaptureScope(val rule: ComposeTestRule, private val activity: ComponentActivity) {

    private val decorView get() = activity.window.decorView

    // The first element with the tag (a repeated item has several), scrolled into view.
    fun node(tag: String): SemanticsNodeInteraction =
        rule.onAllNodesWithTag(tag, useUnmergedTree = true).onFirst().scrollToIfScrollable()

    fun tap(tag: String) {
        node(tag).performClick()
    }

    fun type(tag: String, text: String) {
        node(tag).performTextInput(text)
    }

    // Views are touched on the main thread only.
    private fun <T> onMain(block: () -> T): T {
        var result: Result<T>? = null
        InstrumentationRegistry.getInstrumentation().runOnMainSync { result = runCatching(block) }
        return result!!.getOrThrow()
    }

    private fun imeBottomPx(): Int =
        onMain { ViewCompat.getRootWindowInsets(decorView)?.getInsets(WindowInsetsCompat.Type.ime())?.bottom ?: 0 }

    // Waits until the soft keyboard is up and has stopped moving. Fails if it never comes up. In a long suite on a cold
    // software-GPU emulator the first test to ask for the keyboard after a stretch without one (the input method is
    // idle, or is started again) now and then gets no keyboard for 20 s (#202: it failed so in full suites, in two
    // different classes, and never in 10 runs of the class alone, headless or windowed). So the wait is 30 s, the
    // request is made once more if nothing has come up after ASK_AGAIN_MS, and the failure says what the window was
    // doing when it gave up; the keyboard must still appear and settle.
    fun awaitKeyboardShown() {
        awaitImeStill(askAgainAfterMs = ASK_AGAIN_MS) { imeBottomPx() > 0 }
    }

    // Closes the soft keyboard that typing opened, so a state with typed text is not also a keyboard-open state.
    fun hideKeyboard() {
        onMain { WindowCompat.getInsetsController(activity.window, decorView).hide(WindowInsetsCompat.Type.ime()) }
        awaitImeStill { imeBottomPx() == 0 }
    }

    private fun awaitImeStill(askAgainAfterMs: Long? = null, wanted: () -> Boolean) {
        val started = System.currentTimeMillis()
        val deadline = started + KEYBOARD_MS
        var askedAgain = false
        var last = -1
        var steady = 0
        while (steady < STEADY_POLLS) {
            val now = System.currentTimeMillis()
            check(now < deadline) {
                "the soft keyboard did not settle (ime inset ${imeBottomPx()} px, asked again: $askedAgain, " +
                    "window focused: ${onMain { decorView.hasWindowFocus() }}, focus: ${onMain { activity.currentFocus?.javaClass?.simpleName }})"
            }
            if (askAgainAfterMs != null && !askedAgain && imeBottomPx() == 0 && now - started > askAgainAfterMs) {
                askedAgain = true
                onMain { WindowCompat.getInsetsController(activity.window, decorView).show(WindowInsetsCompat.Type.ime()) }
            }
            Thread.sleep(POLL_MS)
            val inset = imeBottomPx()
            steady = if (wanted() && inset == last) steady + 1 else 0
            last = inset
        }
        rule.waitForIdle()
    }

    private companion object {
        const val KEYBOARD_MS = 30_000L
        const val ASK_AGAIN_MS = 10_000L
        const val POLL_MS = 150L
        const val STEADY_POLLS = 4
    }
}
