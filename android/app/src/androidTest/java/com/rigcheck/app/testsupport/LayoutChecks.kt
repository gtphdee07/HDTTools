package com.rigcheck.app.testsupport

import android.app.UiAutomation
import android.graphics.Bitmap
import android.os.Build
import android.os.ParcelFileDescriptor
import android.view.WindowManager
import android.view.autofill.AutofillManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.junit4.ComposeTestRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.layoutcapture.CaptureScope
import com.rigcheck.app.layoutcapture.Frame
import com.rigcheck.app.layoutcapture.TaggedBounds
import com.rigcheck.app.layoutcapture.measureTaggedElements
import com.rigcheck.app.ui.navigation.RigCheckApp
import java.io.ByteArrayOutputStream
import kotlin.math.abs

// What the re-skin tickets' layout tests (RigPickerChooserLayoutTest #192, EntryScreensLayoutTest #193) share: putting
// a state on a screen the way the app does, and the checks against the designer's map. See those tests for what each
// map value means and the tolerance they hold it to.

/** What `check` is given: the measured tagged elements of the screen and the size of the display. */
class Probe(
    val rule: ComposeTestRule,
    val widthDp: Double,
    val heightDp: Double,
    // The font scale the activity runs at (the system setting of the display frame).
    val fontScale: Float,
    private val imePx: () -> Int,
    private val navigationBarPx: () -> Int = { 0 },
) {
    fun bounds(): Map<String, TaggedBounds> = rule.measureTaggedElements(Frame.PX_PER_DP)
    fun imeDp(): Double = imePx() / Frame.PX_PER_DP

    // The height of the navigation bar (the 3-button keys or the gesture handle) the system reports for the window.
    fun navigationBarDp(): Double = navigationBarPx() / Frame.PX_PER_DP
}

sealed interface Dim {
    // A size the map gives: `dp`, within `tolerance`.
    data class Exact(val dp: Double, val tolerance: Double) : Dim

    // The full width of the column the element is in: the screen less `inset` (the margins around the column).
    data class Fill(val inset: Int, val tolerance: Double = 1.5) : Dim

    // "wrap": nothing to check.
    data object Any : Dim
}

data class Size(val width: Dim, val height: Dim)

fun fixed(dp: Int) = Dim.Exact(dp.toDouble(), 1.5)
fun about(dp: Int, tolerance: Int = 4) = Dim.Exact(dp.toDouble(), tolerance.toDouble())
fun square(dp: Int) = Size(fixed(dp), fixed(dp))

/**
 * Launches the activity as the app does (edge to edge, the app's root around the screen), puts the state on the screen,
 * lets it settle and hands it to `check`, which returns the problems it found (named by the state). With
 * `-Pandroid.testInstrumentationRunnerArguments.layoutScreenshots=true` each state's screenshot is kept
 * (/data/local/tmp/<screenshotFolder>/<frame>/ on the device, to `adb pull`), for the owner to compare with the
 * designer's frames on a phone. Not part of a normal run.
 */
class LayoutStateRunner(private val rule: ComposeTestRule, private val screenshotFolder: String) {

    var frameName = ""

    fun inState(
        name: String,
        content: @Composable () -> Unit,
        setUp: CaptureScope.() -> Unit = {},
        check: (Probe) -> List<String>,
    ): List<String> {
        ActivityScenario.launch(ComponentActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                activity.enableEdgeToEdge()
                // As MainActivity declares it: the window resizes for the keyboard (left unspecified, the system pans it).
                activity.window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
                activity.setContent { RigCheckApp { content() } }
            }
            lateinit var scope: CaptureScope
            lateinit var probe: Probe
            scenario.onActivity { activity ->
                scope = CaptureScope(rule, activity)
                val metrics = activity.resources.displayMetrics
                probe = Probe(
                    rule,
                    widthDp = metrics.widthPixels / Frame.PX_PER_DP,
                    heightDp = metrics.heightPixels / Frame.PX_PER_DP,
                    fontScale = activity.resources.configuration.fontScale,
                    imePx = {
                        ViewCompat.getRootWindowInsets(activity.window.decorView)?.getInsets(WindowInsetsCompat.Type.ime())?.bottom ?: 0
                    },
                    navigationBarPx = {
                        ViewCompat.getRootWindowInsets(activity.window.decorView)?.getInsets(WindowInsetsCompat.Type.navigationBars())?.bottom ?: 0
                    },
                )
            }
            try {
                rule.waitForIdle()
                scope.setUp()
                rule.waitForIdle()
                Thread.sleep(SETTLE_MS)
                rule.waitForIdle()
                saveScreenshotWhenAsked(name)
                return try {
                    check(probe).map { "$name: $it" }
                } catch (e: Throwable) {
                    listOf("$name: ${e.message ?: e}")
                }
            } finally {
                // A filled-in form leaves an autofill session open, which holds the next test's keyboard back.
                scenario.onActivity { it.getSystemService(AutofillManager::class.java)?.cancel() }
            }
        }
    }

    // Written to /data/local/tmp (through the shell, as the instrumentation can), not to the app's own files: Gradle's
    // connected run uninstalls the app when it ends, and with it anything in its files directory.
    private fun saveScreenshotWhenAsked(name: String) {
        if (InstrumentationRegistry.getArguments().getString("layoutScreenshots") != "true") return
        val automation = InstrumentationRegistry.getInstrumentation().uiAutomation
        val folder = "/data/local/tmp/$screenshotFolder/$frameName"
        val file = name.replace(": ", "__").replace(" ", "_").replace("(", "").replace(")", "") + ".png"
        shell(automation, "mkdir -p $folder")
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            // executeShellCommandRw (a shell that takes input) needs API 30, so below it the device takes the picture itself:
            // the same screen, written by the shell (#225).
            shell(automation, "screencap -p $folder/$file")
            return
        }
        val png = ByteArrayOutputStream().also { automation.takeScreenshot().compress(Bitmap.CompressFormat.PNG, 100, it) }
        val (output, input) = automation.executeShellCommandRw("dd of=$folder/$file")
        ParcelFileDescriptor.AutoCloseOutputStream(input).use { it.write(png.toByteArray()) }
        ParcelFileDescriptor.AutoCloseInputStream(output).use { it.readBytes() }
    }

    // The output is read to the end, or the command may not have finished when the next one starts.
    private fun shell(automation: UiAutomation, command: String) {
        ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand(command)).use { it.readBytes() }
    }

    private companion object {
        const val SETTLE_MS = 400L
    }
}

fun shown(b: Map<String, TaggedBounds>, tags: List<String>): List<String> = tags.mapNotNull { tag ->
    val found = b[tag]
    when {
        found == null -> "$tag is not on the screen"
        !found.visible -> "$tag is on the screen but not on show"
        else -> null
    }
}

fun absent(b: Map<String, TaggedBounds>, tags: List<String>): List<String> =
    tags.filter { it in b }.map { "$it is on the screen but should not be" }

fun sizes(b: Map<String, TaggedBounds>, screenWidth: Double, table: Map<String, Size>): List<String> =
    table.flatMap { (tag, size) ->
        val found = b[tag] ?: return@flatMap listOf("$tag is not on the screen, so its size is not checked")
        listOfNotNull(
            dimProblem(tag, "width", found.width, size.width, screenWidth),
            dimProblem(tag, "height", found.height, size.height, screenWidth),
        )
    }

private fun dimProblem(tag: String, what: String, measured: Double, dim: Dim, screenWidth: Double): String? = when (dim) {
    Dim.Any -> null
    is Dim.Exact -> "$tag $what is $measured dp, the map says ${dim.dp} (tolerance ${dim.tolerance})"
        .takeIf { abs(measured - dim.dp) > dim.tolerance }
    is Dim.Fill -> "$tag $what is $measured dp, the map says fill: ${screenWidth - dim.inset} (tolerance ${dim.tolerance})"
        .takeIf { abs(measured - (screenWidth - dim.inset)) > dim.tolerance }
}

// ORDER. The map numbers an element's `new_order` in the reading order of its frame, which counts left to right
// across a row (the avatar, then the text beside it, then the bin; the logo, the name, the tagline, the chip), so
// the numbers are not a sort of the elements' tops. The check is therefore: the bands, one per row or block, come
// one after the other (nothing in a band starts above the lowest start of the band before it), and the `stacks`,
// elements one above the other in a band (the nickname, the subtitle, the last-checked line), come in order by
// their tops.
fun order(
    b: Map<String, TaggedBounds>,
    bands: List<List<String>>,
    stacks: List<List<String>> = emptyList(),
): List<String> {
    val found = mutableListOf<String>()
    stacks.forEach { stack ->
        stack.zipWithNext().forEach { (above, below) ->
            val a = b[above]
            val c = b[below]
            if (a != null && c != null && a.y > c.y + 0.5) found += "$above (top ${a.y}) is below $below (top ${c.y})"
        }
    }
    bands.zipWithNext().forEach { (before, after) ->
        val lowestTop = before.mapNotNull { b[it]?.y }.maxOrNull()
        val firstTop = after.mapNotNull { b[it]?.y }.minOrNull()
        if (lowestTop != null && firstTop != null && firstTop < lowestTop - 0.5) {
            found += "$after starts at $firstTop dp, above $before at $lowestTop dp"
        }
    }
    return found
}

// Every clickable element (found in the merged tree, so a card is one) has a touch area of at least 48 x 48 dp.
fun touchTargets(p: Probe): List<String> {
    val nodes = p.rule.onAllNodes(hasClickAction()).fetchSemanticsNodes()
    if (nodes.isEmpty()) return listOf("no clickable element was found")
    return nodes.mapNotNull { node ->
        // The touch area is the node as laid out, or more where a Material control inflates a small one to 48 dp. A node
        // partly or wholly scrolled out of sight has a touch area cut to what is on show; its laid-out size is what a
        // finger would find once it is scrolled to.
        val touch = node.touchBoundsInRoot
        val width = maxOf(if (touch.isEmpty) 0f else touch.width, node.size.width.toFloat()) / Frame.PX_PER_DP
        val height = maxOf(if (touch.isEmpty) 0f else touch.height, node.size.height.toFloat()) / Frame.PX_PER_DP
        "a clickable element is $width x $height dp, under 48 x 48: ${node.config}".takeIf { width < 47.5 || height < 47.5 }
    }
}

// Scrolls to each tag (an element in a scroll column; a pinned one is left where it is) and checks it is wholly on
// the screen, above the keyboard if it is open.
fun reach(p: Probe, vararg tags: String): List<String> = tags.mapNotNull { tag ->
    val nodes = p.rule.onAllNodesWithTag(tag, useUnmergedTree = true)
    if (nodes.fetchSemanticsNodes().isEmpty()) return@mapNotNull "$tag is not on the screen"
    nodes.onFirst().scrollToIfScrollable()
    p.rule.waitForIdle()
    val b = p.bounds()[tag] ?: return@mapNotNull "$tag is not on the screen after scrolling to it"
    val bottomOfScreen = p.heightDp - p.imeDp()
    when {
        !b.visible -> "$tag cannot be scrolled into view"
        b.y < -0.5 || b.y + b.height > bottomOfScreen + 0.5 ->
            "$tag is not wholly on show after scrolling: ${b.y} to ${b.y + b.height} dp of $bottomOfScreen dp"
        else -> null
    }
}

// By width alone: a tag's x is where its content starts (inside any padding it has), and its width is the whole
// element's, so x + width would count the padding twice.
fun noneWiderThanTheScreen(p: Probe): List<String> = p.bounds().mapNotNull { (tag, b) ->
    "$tag is ${b.width} dp wide on a ${p.widthDp} dp screen".takeIf { b.width > p.widthDp + 0.5 }
}
