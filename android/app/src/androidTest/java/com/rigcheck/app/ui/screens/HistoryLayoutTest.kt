package com.rigcheck.app.ui.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.performScrollToIndex
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.layoutcapture.DisplayFrame
import com.rigcheck.app.layoutcapture.Frame
import com.rigcheck.app.layoutcapture.TaggedBounds
import com.rigcheck.app.testsupport.Dim
import com.rigcheck.app.testsupport.LayoutStateRunner
import com.rigcheck.app.testsupport.Probe
import com.rigcheck.app.testsupport.Size
import com.rigcheck.app.testsupport.about
import com.rigcheck.app.testsupport.absent
import com.rigcheck.app.testsupport.fixed
import com.rigcheck.app.testsupport.noneWiderThanTheScreen
import com.rigcheck.app.testsupport.nodesWithTagShowing
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.order
import com.rigcheck.app.testsupport.reach
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.testsupport.shown
import com.rigcheck.app.testsupport.sizes
import com.rigcheck.app.testsupport.square
import com.rigcheck.app.testsupport.touchTargets
import com.rigcheck.app.ui.UiTags
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #195: the History screen, checked against the designer's map (docs/android-redesign/design-return/ui-redesign-map.json).
// For every element of the screen, in the states below (the frames of annotation-legends.json: history few_entries,
// limit_notice and empty, and the map's "many entries (scrolls)"):
//   - it is displayed (found by its UiTags tag, scrolled into view if it is in the list, and then wholly on the screen);
//   - the reading order is the frame's: the bands, one per row or block, come one after the other by their tops (see
//     `order` in testsupport/LayoutChecks.kt): the top bar's Back and title, the subtitle, the notice and Upgrade to Pro,
//     then the entries (or the empty state); and what is stacked is in order by its top (the Rig's name over the day);
//   - its measured width and height are the map's `new_width` and `new_height`. TOLERANCE: 1.5 dp where the map gives a
//     fixed size, 2 dp on a single line of text (the subtitle's ~22, the name's ~22 and the day's ~18), 4 dp on the
//     title's ~30 and the entry card's ~72, 10 dp on the limit notice's ~86 (three lines of copy that wrap a little differently in the
//     bundled font than in the browser the frames were drawn in); "fill" is the screen less the 16 dp margins of the
//     page, "wrap" has no width to check. A repeated element (the entry and its parts) is measured on its first instance;
//   - every clickable element is at least 48 x 48 dp.
// And on a 360 x 640 dp phone, at font scale 2.0, the screen has no primary action of its own (nothing is pinned at the
// bottom): its one action, Upgrade to Pro, and all the rest can be scrolled to, a long list scrolls to its last entry,
// nothing is wider than the screen, and at a large font the verdict goes under the Rig's name rather than squeezing it.
//
// It changes the display's size, density and font scale for the run and puts them back (as LayoutCaptureTest does),
// and sends no Scan and calls no network.
@RunWith(AndroidJUnit4::class)
class HistoryLayoutTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-195-screenshots")

    private fun putOnTheDisplay(frame: Frame) {
        runner.frameName = frame.name
        display.apply(frame)
    }

    @After
    fun putTheDisplayBack() {
        display.reset()
    }

    private fun inState(
        name: String,
        content: @Composable () -> Unit,
        check: (Probe) -> List<String>,
    ): List<String> = runner.inState(name, content, check = check)

    // --- 412 x 892 --------------------------------------------------------------------------------------------

    @Test
    fun theHistoryFrames412x892MatchTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        // history__few_entries: seven checks, all four verdict words among them.
        problems += inState("history: few_entries", history(sevenEntries)) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, historySizes.only(header + subtitle + entryParts)) +
                absent(b, listOf(UiTags.HISTORY_LIMIT_NOTICE, UiTags.HISTORY_UPGRADE, UiTags.HISTORY_EMPTY)) +
                order(b, headerBand + listOf(subtitle) + listOf(entryBand, entryRow), entryStacks) +
                entryCount(p, 7) +
                words(p, "Safe to Tow", 3) + words(p, "Over Limit", 2) + words(p, "Partially Checked", 1) + words(p, "Not Enough Info", 1) +
                reach(p, *(header + subtitle + entryParts).toTypedArray()) + touchTargets(p)
        }
        // history__limit_notice: the Free plan's notice with Upgrade to Pro under it, then the entries.
        problems += inState("history: limit_notice", history(sevenEntries, limitNotice = limitText)) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, historySizes.only(header + subtitle + noticeParts + entryParts)) +
                order(b, headerBand + listOf(subtitle) + noticeParts.map { listOf(it) } + listOf(entryBand, entryRow), entryStacks) +
                absent(b, listOf(UiTags.HISTORY_EMPTY)) +
                reach(p, *(header + subtitle + noticeParts + entryParts).toTypedArray()) + touchTargets(p)
        }
        // history__empty: no checks, so the one line with the logo and nothing else of the list or the notice.
        problems += inState("history: empty", history(emptyList())) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, historySizes.only(header + subtitle + UiTags.HISTORY_EMPTY)) +
                absent(b, listOf(UiTags.HISTORY_ENTRY, UiTags.HISTORY_LIMIT_NOTICE, UiTags.HISTORY_UPGRADE)) +
                order(b, headerBand + listOf(subtitle, listOf(UiTags.HISTORY_EMPTY))) +
                reach(p, *(header + subtitle + UiTags.HISTORY_EMPTY).toTypedArray()) + touchTargets(p)
        }

        assertTrue("the History frames differ from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- A small phone and a large font ---------------------------------------------------------------------

    @Test
    fun aSmallPhone360x640ReachesEverything() = reachEverything(Frame(360, 640))

    @Test
    fun aSmallPhone360x640AtFontScale2ReachesEverything() = reachEverything(Frame(360, 640, fontScale = 2f))

    private fun reachEverything(frame: Frame) {
        putOnTheDisplay(frame)
        val problems = mutableListOf<String>()
        // At font scale 2.0 the notice's copy is taller than a short phone has room for above what follows it: it is scrolled
        // to, not wholly on show.
        val tall = if (frame.fontScale >= 2f) listOf(UiTags.HISTORY_LIMIT_NOTICE) else emptyList()

        problems += inState("history: limit_notice ${frame.name}", history(sevenEntries, limitNotice = limitText)) { p ->
            val everything = header + subtitle + noticeParts + entryParts - tall
            reach(p, *everything.toTypedArray()) + reachSome(p, *tall.toTypedArray()) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        // With no notice above them the first entry is on the screen from the start, so its parts are the first ones measured.
        problems += inState("history: few_entries ${frame.name}", history(sevenEntries)) { p ->
            val underTheName = if (frame.fontScale >= 1.6f) verdictUnderTheName(p.bounds()) else emptyList()
            underTheName + reach(p, *(header + subtitle + entryParts).toTypedArray()) + noneWiderThanTheScreen(p)
        }
        problems += inState("history: empty ${frame.name}", history(emptyList())) { p ->
            reach(p, *(header + subtitle + UiTags.HISTORY_EMPTY).toTypedArray()) + noneWiderThanTheScreen(p)
        }
        // The map's "many entries (scrolls)": twenty checks are more than the screen holds, and the list scrolls to the last.
        problems += inState("history: many_entries ${frame.name}", history(twentyEntries)) { p ->
            val last = twentyEntries.last().rigNickname
            p.rule.onNode(hasScrollAction(), useUnmergedTree = true).performScrollToIndex(twentyEntries.size)
            p.rule.waitForIdle()
            p.rule.onNodeWithTagText(UiTags.HISTORY_ENTRY, last).assertIsDisplayed()
            // The top bar is pinned: Back is still where it was with the list at its end.
            shown(p.bounds(), listOf(UiTags.HISTORY_BACK, UiTags.HISTORY_TITLE)) + noneWiderThanTheScreen(p)
        }

        assertTrue("${frame.name}:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Checks of this screen --------------------------------------------------------------------------

    private fun Map<String, Size>.only(tags: List<String>): Map<String, Size> = filterKeys { it in tags }

    private fun entryCount(p: Probe, expected: Int): List<String> {
        val found = p.rule.onAllNodesWithTag(UiTags.HISTORY_ENTRY, useUnmergedTree = true).fetchSemanticsNodes().size
        return listOfNotNull("$found entries are on the screen, not $expected".takeIf { found != expected })
    }

    // At least `times` pills say the words: each verdict has its own, so the check cannot tell them apart by colour alone.
    private fun words(p: Probe, text: String, times: Int): List<String> {
        val found = p.rule.nodesWithTagShowing(UiTags.HISTORY_ENTRY_VERDICT, text)
        return listOfNotNull("${UiTags.HISTORY_ENTRY_VERDICT} says \"$text\" $found times, not $times".takeIf { found != times })
    }

    // An element taller than the room on a short phone at a large font cannot be wholly on show whatever the scroll: it is
    // scrolled to, and some of it is on show, starting from its top.
    private fun reachSome(p: Probe, vararg tags: String): List<String> = tags.mapNotNull { tag ->
        val nodes = p.rule.onAllNodesWithTag(tag, useUnmergedTree = true)
        if (nodes.fetchSemanticsNodes().isEmpty()) return@mapNotNull "$tag is not on the screen"
        nodes.onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val b = p.bounds()[tag] ?: return@mapNotNull "$tag is not on the screen after scrolling to it"
        "$tag cannot be scrolled into view".takeIf { !b.visible || b.y >= p.heightDp }
    }

    // From font scale 1.6 the pill goes on a line of its own under the name and the day (as a Results row does), so a long
    // verdict does not squeeze the name to a letter a line.
    private fun verdictUnderTheName(b: Map<String, TaggedBounds>): List<String> {
        val date = b[UiTags.HISTORY_ENTRY_DATE] ?: return listOf("the entry's day is not on the screen")
        val verdict = b[UiTags.HISTORY_ENTRY_VERDICT] ?: return listOf("the entry's verdict is not on the screen")
        return listOfNotNull(
            "the verdict (top ${verdict.y} dp) is not under the day (bottom ${date.y + date.height} dp)"
                .takeIf { verdict.y < date.y + date.height - 0.5 },
        )
    }

    // --- What the map says ------------------------------------------------------------------------------

    private val header = listOf(UiTags.HISTORY_BACK, UiTags.HISTORY_TITLE)
    private val subtitle = listOf(UiTags.HISTORY_SUBTITLE)
    private val noticeParts = listOf(UiTags.HISTORY_LIMIT_NOTICE, UiTags.HISTORY_UPGRADE)
    private val entryParts = listOf(
        UiTags.HISTORY_ENTRY, UiTags.HISTORY_ENTRY_RIG, UiTags.HISTORY_ENTRY_DATE, UiTags.HISTORY_ENTRY_VERDICT,
    )

    // The top bar's row: Back and the title beside it.
    private val headerBand = listOf(header)
    private val entryBand = listOf(UiTags.HISTORY_ENTRY)
    private val entryRow = listOf(UiTags.HISTORY_ENTRY_RIG, UiTags.HISTORY_ENTRY_VERDICT)

    // Stacked in an entry: the card over the Rig's name over the day.
    private val entryStacks = listOf(listOf(UiTags.HISTORY_ENTRY, UiTags.HISTORY_ENTRY_RIG, UiTags.HISTORY_ENTRY_DATE))

    // The page has 16 dp side margins, as on every screen. The map's heights for the text lines are the line heights of
    // its styles (22 for the subtitle's 16/22, 22 for the name's 18/22, 18 for the day's 13/18); the title's ~30 is its
    // 26/30 line. The empty state's words are two lines of 16/22.
    private val historySizes: Map<String, Size> = mapOf(
        UiTags.HISTORY_BACK to square(48),
        UiTags.HISTORY_TITLE to Size(Dim.Any, about(30)),
        UiTags.HISTORY_SUBTITLE to Size(Dim.Fill(32), about(22, 2)),
        UiTags.HISTORY_LIMIT_NOTICE to Size(Dim.Fill(32), about(86, 10)),
        UiTags.HISTORY_UPGRADE to Size(Dim.Fill(32), fixed(48)),
        UiTags.HISTORY_EMPTY to Size(Dim.Any, about(44, 4)),
        UiTags.HISTORY_ENTRY to Size(Dim.Fill(32), about(72)),
        UiTags.HISTORY_ENTRY_RIG to Size(Dim.Any, about(22, 2)),
        UiTags.HISTORY_ENTRY_DATE to Size(Dim.Any, about(18, 2)),
        UiTags.HISTORY_ENTRY_VERDICT to Size(Dim.Any, about(22, 2)),
    )

    // --- Fixtures -----------------------------------------------------------------------------------------

    private fun entry(id: Int, day: String, rig: String, verdict: VerdictStatus) =
        HistoryEntry("entry-$id", "2026-$day" + "T12:00:00Z", rig, verdict)

    // The seven checks of history__few_entries, in its order: three safe, two over the limit, one partial, one not enough.
    private val sevenEntries = listOf(
        entry(1, "10-27", "Summer rig", VerdictStatus.PASS),
        entry(2, "10-20", "Weekend hauler", VerdictStatus.FAIL),
        entry(3, "10-03", "Old faithful", VerdictStatus.PARTIAL),
        entry(4, "09-14", "Summer rig", VerdictStatus.PASS),
        entry(5, "08-30", "Weekend hauler", VerdictStatus.INSUFFICIENT),
        entry(6, "08-02", "Old faithful", VerdictStatus.PASS),
        entry(7, "07-19", "Summer rig", VerdictStatus.FAIL),
    )

    private val twentyEntries = (1..20).map { entry(it, "07-${(it + 1).toString().padStart(2, '0')}", "Rig $it", VerdictStatus.PASS) }

    // The words of a Free account whose History holds its last 10, as historyLimitNotice says them with the plan's own numbers.
    private val limitText = "The Free plan keeps your last 10 checks, and the oldest drops off as you add more. Pro keeps your last 100."

    private fun history(entries: List<HistoryEntry>, limitNotice: String? = null): @Composable () -> Unit = {
        HistoryScreen(entries = entries, limitNotice = limitNotice)
    }
}
