package com.rigcheck.app.ui.navigation

import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.positionInWindow
import androidx.compose.ui.layout.positionOnScreen
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.layoutcapture.DisplayFrame
import com.rigcheck.app.layoutcapture.Frame
import com.rigcheck.app.layoutcapture.captureCases
import com.rigcheck.app.testsupport.LayoutStateRunner
import com.rigcheck.app.testsupport.NavigationMode
import com.rigcheck.app.testsupport.Probe
import com.rigcheck.app.ui.UiTags
import org.junit.After
import org.junit.AfterClass
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.BeforeClass
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #197: with 3-button navigation on, no element is covered by the navigation bar on any screen. SystemBarsTest holds the
// one rule that does it (RigCheckApp pads every screen inside the bars) for two screens; this opens every screen state
// of the layout capture (docs/android-redesign/ui-inventory.json, the dialogs and the account sheet included) on a
// 360 x 640 dp phone, where there is least room, with the 3-button bar really on (the test sets it and puts the
// device's setting back), and checks that no tagged element, as much of it as is on show, reaches into the bar.
// An element scrolled out of sight is not on show and is not checked; the one that scrolls into view stops at the bar.
@RunWith(AndroidJUnit4::class)
class ThreeButtonNavigationTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val display = DisplayFrame(instrumentation)
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-197-three-button")

    @After
    fun putTheDisplayBack() {
        display.reset()
    }

    // One test per screen of the inventory (each is its states, under the 90 s one test may run), and a test that no screen
    // of the capture was left out.
    @Test
    fun rigPickerIsNotCoveredByTheBar() = check("rig_picker")

    @Test
    fun chooserIsNotCoveredByTheBar() = check("chooser")

    @Test
    fun photoSourceDialogIsNotCoveredByTheBar() = check("photo_source_dialog")

    @Test
    fun truckTagEntryIsNotCoveredByTheBar() = check("truck_tag_entry")

    @Test
    fun trailerTagEntryIsNotCoveredByTheBar() = check("trailer_tag_entry")

    @Test
    fun scaleTicketEntryIsNotCoveredByTheBar() = check("scale_ticket_entry")

    @Test
    fun disclaimerIsNotCoveredByTheBar() = check("disclaimer")

    @Test
    fun resultsIsNotCoveredByTheBar() = check("results")

    @Test
    fun historyIsNotCoveredByTheBar() = check("history")

    @Test
    fun paywallIsNotCoveredByTheBar() = check("paywall")

    @Test
    fun accountIsNotCoveredByTheBar() = check("account")

    @Test
    fun scanErrorDialogIsNotCoveredByTheBar() = check("scan_error_dialog")

    @Test
    fun lateScanDialogIsNotCoveredByTheBar() = check("late_scan_dialog")

    @Test
    fun deleteRigDialogIsNotCoveredByTheBar() = check("delete_rig_dialog")

    @Test
    fun crashReportDialogIsNotCoveredByTheBar() = check("crash_report_dialog")

    @Test
    fun everyScreenOfTheCaptureHasATestAbove() {
        val tested = setOf("rig_picker", "chooser", "photo_source_dialog", "truck_tag_entry", "trailer_tag_entry", "scale_ticket_entry", "disclaimer", "results", "history", "paywall", "account", "scan_error_dialog", "late_scan_dialog", "delete_rig_dialog", "crash_report_dialog")
        assertEquals(tested, captureCases.map { it.screen }.toSet())
    }

    private fun check(screen: String) {
        val frame = Frame(360, 640)
        runner.frameName = frame.name
        display.apply(frame)

        val cases = captureCases.filter { it.screen == screen }
        assertTrue("no captured state for $screen", cases.isNotEmpty())
        val problems = cases.flatMap { case -> runner.inState(case.id, case.content, case.setUp) { p -> coveredByTheBar(p, frame) } }

        assertTrue(
            "${problems.size} problems in ${cases.size} states of $screen with 3-button navigation:\n" + problems.joinToString("\n"),
            problems.isEmpty(),
        )
    }

    // Each tagged element's bottom edge, as much of it as is on show (cut by the scroll area it is in), on the display.
    private fun coveredByTheBar(p: Probe, frame: Frame): List<String> {
        val bar = p.navigationBarDp()
        if (bar < MIN_BAR_DP) return listOf("the navigation bar is $bar dp, so 3-button navigation is not on and this proves nothing")
        // The display's height is the frame the test set, not p.heightDp: before Android 11 (API 30) the activity's display
        // metrics leave the navigation bar out, so p.heightDp - bar took the bar off twice on API 26 (#225).
        val barTop = frame.heightDp - bar
        val nodes = p.rule.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsProperties.TestTag), useUnmergedTree = true)
            .fetchSemanticsNodes()
        return nodes.mapNotNull { node ->
            // The sheet's surface is painted to the foot of the screen, behind the bar, on purpose (the design: "64 dp that
            // clears the 3-button bar"); what is on it, its buttons and texts, is checked like everything else.
            if (node.config[SemanticsProperties.TestTag] in SURFACES_BEHIND_THE_BAR) return@mapNotNull null
            val coordinates = node.layoutInfo.coordinates
            val shown = coordinates.boundsInWindow()
            if (shown.width <= 0f || shown.height <= 0f) return@mapNotNull null
            // A dialog is a window of its own, so the window's top edge is not always the display's.
            val windowTop = coordinates.positionOnScreen().y - coordinates.positionInWindow().y
            val bottom = (shown.bottom + windowTop) / Frame.PX_PER_DP
            "${node.config[SemanticsProperties.TestTag]} reaches ${"%.1f".format(bottom)} dp, into the navigation bar that starts at ${"%.1f".format(barTop)} dp"
                .takeIf { bottom > barTop + 0.5 }
        }
    }

    companion object {
        // The 3-button bar is 48 dp; the gesture handle is under half of that.
        private const val MIN_BAR_DP = 40.0

        private val SURFACES_BEHIND_THE_BAR = setOf(UiTags.PICKER_ACCOUNT_MENU)

        // Set once for the class and put back after it: the switch takes a few seconds, and each test is one screen.
        private val navigation by lazy { NavigationMode(InstrumentationRegistry.getInstrumentation()) }

        @BeforeClass
        @JvmStatic
        fun useThreeButtons() = navigation.use3Buttons()

        @AfterClass
        @JvmStatic
        fun putTheNavigationBack() = navigation.restore()
    }
}
