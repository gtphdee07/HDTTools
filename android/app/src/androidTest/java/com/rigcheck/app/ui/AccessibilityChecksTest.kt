package com.rigcheck.app.ui

import androidx.compose.ui.test.isRoot
import androidx.compose.ui.test.junit4.accessibility.disableAccessibilityChecks
import androidx.compose.ui.test.junit4.accessibility.enableAccessibilityChecks
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.tryPerformAccessibilityChecks
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.google.android.apps.common.testing.accessibility.framework.integrations.espresso.AccessibilityValidator
import com.rigcheck.app.layoutcapture.DisplayFrame
import com.rigcheck.app.layoutcapture.Frame
import com.rigcheck.app.layoutcapture.captureCases
import com.rigcheck.app.testsupport.LayoutStateRunner
import com.rigcheck.app.testsupport.Probe
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #197: Compose's accessibility checks (the Accessibility Test Framework: touch-target size, a content description on
// every icon that does something, text and image contrast, duplicate click areas) run on every screen state of the
// layout capture (docs/android-redesign/ui-inventory.json: the screens, the dialogs and the sheet, 92 states) and
// report no error. The framework looks at the pixels for contrast, so this is the contrast of what is really drawn, over
// the TextFillPairsTest table of what the design says. On the 412 x 892 reference phone; the small phone and the large
// font are the layout tests' (every one of them also holds the 48 dp touch target).
@RunWith(AndroidJUnit4::class)
class AccessibilityChecksTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-197-accessibility")

    @After
    fun putTheDisplayBack() {
        display.reset()
        composeRule.disableAccessibilityChecks()
    }

    // One test per screen of the inventory (each is its states, under the 90 s one test may run), and a test that no screen
    // of the capture was left out.
    @Test
    fun rigPickerHasNoAccessibilityError() = check("rig_picker")

    @Test
    fun chooserHasNoAccessibilityError() = check("chooser")

    @Test
    fun photoSourceDialogHasNoAccessibilityError() = check("photo_source_dialog")

    @Test
    fun truckTagEntryHasNoAccessibilityError() = check("truck_tag_entry")

    @Test
    fun trailerTagEntryHasNoAccessibilityError() = check("trailer_tag_entry")

    @Test
    fun scaleTicketEntryHasNoAccessibilityError() = check("scale_ticket_entry")

    @Test
    fun disclaimerHasNoAccessibilityError() = check("disclaimer")

    @Test
    fun resultsHasNoAccessibilityError() = check("results")

    @Test
    fun historyHasNoAccessibilityError() = check("history")

    @Test
    fun paywallHasNoAccessibilityError() = check("paywall")

    @Test
    fun accountHasNoAccessibilityError() = check("account")

    @Test
    fun scanErrorDialogHasNoAccessibilityError() = check("scan_error_dialog")

    @Test
    fun lateScanDialogHasNoAccessibilityError() = check("late_scan_dialog")

    @Test
    fun deleteRigDialogHasNoAccessibilityError() = check("delete_rig_dialog")

    @Test
    fun crashReportDialogHasNoAccessibilityError() = check("crash_report_dialog")

    @Test
    fun everyScreenOfTheCaptureHasATestAbove() {
        val tested = setOf("rig_picker", "chooser", "photo_source_dialog", "truck_tag_entry", "trailer_tag_entry", "scale_ticket_entry", "disclaimer", "results", "history", "paywall", "account", "scan_error_dialog", "late_scan_dialog", "delete_rig_dialog", "crash_report_dialog")
        assertEquals(tested, captureCases.map { it.screen }.toSet())
    }

    private fun check(screen: String) {
        val frame = Frame(412, 892)
        runner.frameName = frame.name
        display.apply(frame)

        val cases = captureCases.filter { it.screen == screen }
        assertTrue("no captured state for $screen", cases.isNotEmpty())
        val problems = cases.flatMap { case -> runner.inState(case.id, case.content, case.setUp) { p -> accessibilityErrors(p) } }

        assertTrue(
            "${problems.size} accessibility errors in ${cases.size} states of $screen:\n" + problems.joinToString("\n"),
            problems.isEmpty(),
        )
    }

    // The checks run once for each window the state has (a dialog is a window of its own). They throw for an error;
    // a warning does not fail the state.
    private fun accessibilityErrors(p: Probe): List<String> {
        p.rule.enableAccessibilityChecks(AccessibilityValidator().setRunChecksFromRootView(true))
        val roots = p.rule.onAllNodes(isRoot()).fetchSemanticsNodes().size
        return (0 until roots).mapNotNull { index ->
            try {
                p.rule.onAllNodes(isRoot())[index].tryPerformAccessibilityChecks()
                null
            } catch (e: Throwable) {
                "window $index: ${e.message ?: e}"
            }
        }
    }
}
