package com.rigcheck.app.layoutcapture

import android.app.Instrumentation
import android.content.Context
import android.graphics.Bitmap
import android.view.autofill.AutofillManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.ui.navigation.RigCheckApp
import java.io.File
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #189: opens every screen state of docs/android-redesign/ui-inventory.json that the app can reach with the existing
// fixtures (captureCases), once per phone frame, and writes for each state `<screen>__<state>.png` (a screenshot of
// the display) and `<screen>__<state>.json` (the position and size in dp of every UiTags element, and whether it is on
// show) under files/layout-capture/<frame> in the app's external files directory. scripts/android_layout_capture.py
// runs it and pulls the files; `uv run scripts/ui_inventory.py --merge-bounds` merges them into the inventory.
//
// Each state is measured twice, in two freshly launched activities, and the test fails if the two measurements
// differ: a layout that moves between runs has no position to record. A state that cannot be put on screen fails the
// test too, after the rest have been captured, naming it.
//
// It changes the display size, density and font scale of the device and puts them back, so it is skipped unless the
// runner is given `-e layoutCapture true` (the Gradle connectedDebugAndroidTest run does not pass it).
@RunWith(AndroidJUnit4::class)
class LayoutCaptureTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val instrumentation: Instrumentation = InstrumentationRegistry.getInstrumentation()
    private val display = DisplayFrame(instrumentation)

    @Before
    fun onlyWhenAsked() {
        assumeTrue(
            "set -e layoutCapture true (scripts/android_layout_capture.py does)",
            InstrumentationRegistry.getArguments().getString("layoutCapture") == "true",
        )
    }

    @After
    fun putTheDisplayBack() {
        display.reset()
    }

    @Test
    fun phone412x892() = captureAll(Frame(412, 892), captureCases)

    @Test
    fun smallPhone360x640() = captureAll(Frame(360, 640), captureCases)

    @Test
    fun phone412x892AtFontScale2() = captureAll(Frame(412, 892, fontScale = 2f), largeFontCases())

    @Test
    fun smallPhone360x640AtFontScale2() = captureAll(Frame(360, 640, fontScale = 2f), largeFontCases())

    private fun largeFontCases() = captureCases.filter { it.screen in largeFontScreens }

    private fun captureAll(frame: Frame, cases: List<CaptureCase>) {
        val folder = File(
            ApplicationProvider.getApplicationContext<Context>().getExternalFilesDir(OUTPUT_FOLDER),
            frame.name,
        ).also {
            it.deleteRecursively()
            check(it.mkdirs()) { "cannot create ${it.absolutePath}" }
        }
        display.apply(frame)

        val failures = cases.mapNotNull { case ->
            try {
                capture(case, frame, folder)
                null
            } catch (e: Throwable) {
                "${case.id}: ${e.message ?: e}"
            }
        }
        assertTrue(
            "${failures.size} of ${cases.size} states could not be captured at ${frame.name}:\n" +
                failures.joinToString("\n"),
            failures.isEmpty(),
        )
    }

    private fun capture(case: CaptureCase, frame: Frame, folder: File) {
        val first = showAndMeasure(case, frame, screenshot = true)
        val second = showAndMeasure(case, frame, screenshot = false)

        val differences = describeDifferences(first.bounds, second.bounds)
        assertTrue("two runs measured different bounds:\n" + differences.joinToString("\n"), differences.isEmpty())
        assertTrue("no tagged element is on the screen", first.bounds.isNotEmpty())

        File(folder, "${case.id}.json").writeText(boundsFileText(case.screen, case.state, captureCases.indexOf(case), frame, first.bounds))
        File(folder, "${case.id}.png").outputStream().use { first.screenshot!!.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    private class Measured(val bounds: Map<String, TaggedBounds>, val screenshot: Bitmap?)

    // Launches the activity fresh, as the app does (edge to edge, the app's root around the screen), puts the state on
    // screen, lets it settle and measures it.
    private fun showAndMeasure(case: CaptureCase, frame: Frame, screenshot: Boolean): Measured {
        ActivityScenario.launch(ComponentActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                activity.enableEdgeToEdge()
                activity.setContent { RigCheckApp { case.content() } }
            }
            lateinit var scope: CaptureScope
            scenario.onActivity { activity -> scope = CaptureScope(composeRule, activity) }
            try {
                composeRule.waitForIdle()
                case.setUp(scope)
                composeRule.waitForIdle()
                Thread.sleep(SETTLE_MS)
                composeRule.waitForIdle()

                scenario.onActivity { activity ->
                    assertEquals(
                        "font scale", frame.fontScale, activity.resources.configuration.fontScale, 0.001f,
                    )
                }
                val bounds = composeRule.measureTaggedElements(Frame.PX_PER_DP)
                val picture = if (screenshot) instrumentation.uiAutomation.takeScreenshot() else null
                if (picture != null) {
                    assertEquals("screenshot width (px)", frame.widthPx, picture.width)
                    assertEquals("screenshot height (px)", frame.heightPx, picture.height)
                }
                return Measured(bounds, picture)
            } finally {
                // A filled-in form leaves an autofill session open, which holds the next test's keyboard back.
                scenario.onActivity { it.getSystemService(AutofillManager::class.java)?.cancel() }
            }
        }
    }

    private companion object {
        const val OUTPUT_FOLDER = "layout-capture"
        const val SETTLE_MS = 400L
    }
}
