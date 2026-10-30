package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.layoutcapture.DisplayFrame
import com.rigcheck.app.layoutcapture.Frame
import com.rigcheck.app.layoutcapture.captureCases
import com.rigcheck.app.testsupport.LayoutStateRunner
import com.rigcheck.app.testsupport.noneWiderThanTheScreen
import com.rigcheck.app.testsupport.reach
import com.rigcheck.app.testsupport.touchTargets
import com.rigcheck.app.ui.UiTags
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #197: the two dialogs over the Rig picker that no layout test of #192 to #196 put on a small phone: "Delete <nickname>?"
// (#192's follow-up) and the crash report question (#184). On a 360 x 640 dp phone, also at font scale 2.0, each of their
// actions can be reached (scrolled to) and is then wholly on show, nothing is wider than the screen, and the 48 dp
// touch-target rule holds. The other screens' and dialogs' primary actions are reached by their own layout tests
// (RigPickerChooserLayoutTest, EntryScreensLayoutTest, DisclaimerResultsLayoutTest, HistoryLayoutTest,
// PaywallAccountLayoutTest, each with a 360 x 640 test at font scale 1 and 2.0). The states are the layout capture's
// (layoutcapture/CaptureCases.kt).
@RunWith(AndroidJUnit4::class)
class RigPickerDialogsLayoutTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-197-dialog-screenshots")

    @After
    fun putTheDisplayBack() {
        display.reset()
    }

    @Test
    fun aSmallPhone360x640ReachesTheDialogsActions() = reachEverything(Frame(360, 640))

    @Test
    fun aSmallPhone360x640AtFontScale2ReachesTheDialogsActions() = reachEverything(Frame(360, 640, fontScale = 2f))

    private fun reachEverything(frame: Frame) {
        runner.frameName = frame.name
        display.apply(frame)
        val deleteActions = arrayOf(UiTags.DELETE_RIG_TITLE, UiTags.DELETE_RIG_CONFIRM, UiTags.DELETE_RIG_CANCEL)
        val states = listOf(
            "delete_rig_dialog__question" to deleteActions,
            "delete_rig_dialog__delete_failed" to arrayOf(*deleteActions, UiTags.DELETE_RIG_ERROR),
            "crash_report_dialog__question" to
                arrayOf(UiTags.CRASH_PROMPT_QUESTION, UiTags.CRASH_PROMPT_DETAILS, UiTags.CRASH_PROMPT_SEND, UiTags.CRASH_PROMPT_DISMISS),
            "crash_report_dialog__no_email_app" to arrayOf(UiTags.CRASH_PROMPT_NO_MAIL_APP, UiTags.CRASH_PROMPT_DISMISS),
        )

        val problems = states.flatMap { (id, tags) ->
            val case = captureCases.single { it.id == id }
            runner.inState(id, case.content, case.setUp) { p -> reach(p, *tags) + noneWiderThanTheScreen(p) + touchTargets(p) }
        }

        assertTrue("${frame.name}:\n" + problems.joinToString("\n"), problems.isEmpty())
    }
}
