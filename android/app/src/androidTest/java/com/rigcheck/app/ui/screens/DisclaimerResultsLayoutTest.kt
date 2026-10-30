package com.rigcheck.app.ui.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.layout.positionOnScreen
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.verdictFor
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
import com.rigcheck.app.testsupport.order
import com.rigcheck.app.testsupport.reach
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.testsupport.shown
import com.rigcheck.app.testsupport.sizes
import com.rigcheck.app.testsupport.square
import com.rigcheck.app.testsupport.touchTargets
import com.rigcheck.app.ui.GarageNotice
import com.rigcheck.app.ui.UiTags
import kotlin.math.abs
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #194: the Disclaimer and Results screens, checked against the designer's map
// (docs/android-redesign/design-return/ui-redesign-map.json). For every element of those screens, in the states below
// (the frames of annotation-legends.json: disclaimer default and large_font; results safe, not_safe_row_expanded,
// partially_checked, not_enough_information, notices (with notices_scrolled) and safe_scrolled_to_end):
//   - it is displayed (found by its UiTags tag, scrolled into view if it is in the page, and then wholly on the screen);
//   - the reading order is the frame's: the bands, one per row or block, come one after the other by their tops (see
//     `order` in testsupport/LayoutChecks.kt), and what is stacked in a band is in order by its top. The notices come
//     in the frames' order (the estimate, the Garage notice, Get Pro, the History notice, the breakdown), which is not
//     the map's `new_order` numbers: those count a different frame for each notice, and the frames are the reference
//     (README.md of the hand-back: "the frames are the reference where they differ");
//   - its measured width and height are the map's `new_width` and `new_height`. TOLERANCE: 1.5 dp where the map gives a
//     fixed size, 4 dp on a height the map gives with a "~", 2 dp on a single line of text, up to 10 dp for a short
//     notice and 22 dp for the estimate (15 lines of legal copy, each one 20 dp, that wrap a little differently in the
//     bundled font than in the browser the frames were drawn in), 24 dp for the breakdown card (the sum of its rows,
//     whose labels wrap in the same way; held in `safe` only, the one frame where it has the six rows closed that the
//     map's 659 dp is for); "fill" is the full width of the column the element is in, "wrap" has no width
//     to check. A repeated element (the rows, their parts) is measured on its first instance, as the map says;
//   - every clickable element is at least 48 x 48 dp.
// And on a 360 x 640 dp phone, at font scale 2.0, the primary action of each screen is on show with the page scrolled
// (it is pinned: it does not move when the page does), everything on the page can be scrolled to, nothing is wider than
// the screen, the Results page is one scroll (the breakdown card does not scroll inside itself), and with all the
// notices showing, every one of them can be scrolled to.
//
// It changes the display's size, density and font scale for the run and puts them back (as LayoutCaptureTest does),
// and sends no Scan and calls no network.
@RunWith(AndroidJUnit4::class)
class DisclaimerResultsLayoutTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-194-screenshots")

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
        setUp: com.rigcheck.app.layoutcapture.CaptureScope.() -> Unit = {},
        check: (Probe) -> List<String>,
    ): List<String> = runner.inState(name, content, setUp, check)

    // --- Disclaimer, 412 x 892 -----------------------------------------------------------------------------

    @Test
    fun theDisclaimerFrame412x892MatchesTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        problems += inState("disclaimer: default", disclaimer()) { p ->
            val b = p.bounds()
            val tags = disclaimerTags
            sizes(b, p.widthDp, disclaimerSizes) +
                order(b, tags.dropLast(1).map { listOf(it) }) +
                reach(p, *tags.toTypedArray()) + touchTargets(p)
        }

        // disclaimer__large_font: the text is large enough to push the button off the screen of the old page; here the page
        // scrolls and the button does not leave.
        putOnTheDisplay(Frame(412, 892, fontScale = 2f))
        problems += inState("disclaimer: large_font", disclaimer()) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.DISCLAIMER_ICON, UiTags.DISCLAIMER_TITLE, UiTags.DISCLAIMER_BODY_1, UiTags.DISCLAIMER_ACCEPT_BUTTON)) +
                order(b, disclaimerTags.dropLast(1).map { listOf(it) }) +
                pinnedWhileScrolling(p, scrollTo = UiTags.DISCLAIMER_BODY_2, moves = UiTags.DISCLAIMER_TITLE, pinned = listOf(UiTags.DISCLAIMER_ACCEPT_BUTTON)) +
                reach(p, *disclaimerTags.toTypedArray()) + touchTargets(p) + noneWiderThanTheScreen(p)
        }

        assertTrue("the Disclaimer frame differs from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Results, 412 x 892 --------------------------------------------------------------------------------

    @Test
    fun theResultsFrame412x892MatchesTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        // results__safe: six rows, the Combined row among them.
        problems += inState("results: safe", results(safeRows)) { p ->
            val b = p.bounds()
            val tags = resultsHeader + resultsRowParts + UiTags.RESULTS_BREAKDOWN_CARD
            sizes(b, p.widthDp, resultsSizes.only(tags + UiTags.RESULTS_ROW_CHEVRON + UiTags.RESULTS_START_ANOTHER_BUTTON)) +
                order(b, resultsHeaderBands + resultsBodyBands, resultsStacks) +
                rowCount(b, 6) + chevronsOnlyWhereThereIsANote(b, 3) +
                pinnedWhileScrolling(p, scrollTo = UiTags.RESULTS_FOOTER_NOTE, moves = UiTags.RESULTS_VERDICT, pinned = resultsPinned) +
                onePageScroll(p) +
                reach(p, *(tags + UiTags.RESULTS_ROW_CHEVRON + UiTags.RESULTS_FOOTER_NOTE + UiTags.RESULTS_START_ANOTHER_BUTTON).toTypedArray()) +
                touchTargets(p)
        }
        // results__not_safe_row_expanded: the Tow Vehicle row is over its limit and its note is open under it.
        problems += inState(
            "results: not_safe_row_expanded", results(notSafeRows),
            setUp = { tap(UiTags.RESULTS_ROW_CHEVRON) },
        ) { p ->
            val b = p.bounds()
            val tags = resultsHeader + listOf(UiTags.RESULTS_ROW_NOTE, UiTags.RESULTS_BREAKDOWN_CARD)
            sizes(b, p.widthDp, resultsSizes.only(tags - UiTags.RESULTS_VERDICT - UiTags.RESULTS_BREAKDOWN_CARD)) +
                shown(b, listOf(UiTags.RESULTS_VERDICT, UiTags.RESULTS_ROW_NOTE)) +
                order(b, resultsHeaderBands + resultsBodyBands + listOf(listOf(UiTags.RESULTS_ROW_NOTE)), resultsStacks) +
                reach(p, UiTags.RESULTS_ROW_NOTE, UiTags.RESULTS_START_ANOTHER_BUTTON) + touchTargets(p)
        }
        // results__partially_checked: five rows (no GCWR), the trailer's two not checked.
        problems += inState("results: partially_checked", results(partialRows)) { p ->
            val b = p.bounds()
            val tags = resultsHeader + resultsRowParts + UiTags.RESULTS_BREAKDOWN_CARD
            sizes(b, p.widthDp, resultsSizes.only(tags - UiTags.RESULTS_VERDICT - UiTags.RESULTS_BREAKDOWN_CARD)) +
                order(b, resultsHeaderBands + resultsBodyBands, resultsStacks) +
                rowCount(b, 5) + words(p, UiTags.RESULTS_VERDICT, "Partially Checked") + words(p, UiTags.RESULTS_ROW_BADGE, "Not checked", times = 2) +
                reach(p, *(tags + UiTags.RESULTS_START_ANOTHER_BUTTON).toTypedArray()) + touchTargets(p)
        }
        // results__not_enough_information: five rows, none checked.
        problems += inState("results: not_enough_information", results(nothingCheckedRows)) { p ->
            val b = p.bounds()
            val tags = resultsHeader + resultsRowParts + UiTags.RESULTS_BREAKDOWN_CARD
            sizes(b, p.widthDp, resultsSizes.only(tags - UiTags.RESULTS_VERDICT - UiTags.RESULTS_BREAKDOWN_CARD)) +
                order(b, resultsHeaderBands + resultsBodyBands, resultsStacks) +
                rowCount(b, 5) + words(p, UiTags.RESULTS_VERDICT, "Not Enough Information") + words(p, UiTags.RESULTS_ROW_BADGE, "Not checked", times = 5) +
                reach(p, *(tags + UiTags.RESULTS_START_ANOTHER_BUTTON).toTypedArray()) + touchTargets(p)
        }
        // results__notices and results__notices_scrolled: the estimate, then the Garage notice with Get Pro under it, then the
        // History notice, and the breakdown under all of them.
        problems += inState("results: notices", results(safeRows.map { it.copy(estimated = true) }, garage = fullGarage, history = historyText)) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, resultsSizes.only(resultsHeader + noticeTags + UiTags.RESULTS_BREAKDOWN_CARD)) +
                order(
                    b, resultsHeaderBands + listOf(UiTags.RESULTS_ESTIMATED_NOTICE, UiTags.GARAGE_NOTICE, UiTags.GARAGE_NOTICE_GET_PRO, UiTags.HISTORY_NOTICE, UiTags.RESULTS_BREAKDOWN_CARD).map { listOf(it) },
                    resultsStacks,
                ) +
                reach(p, *(noticeTags + UiTags.RESULTS_BREAKDOWN_CARD + UiTags.RESULTS_START_ANOTHER_BUTTON).toTypedArray()) + touchTargets(p)
        }
        // results__notices_scrolled: the page is scrolled to the first row, so the History notice is above it, Get Pro above
        // that (cut by the bar), and the breakdown card starts under the History notice.
        problems += inState(
            "results: notices_scrolled", results(safeRows.map { it.copy(estimated = true) }, garage = fullGarage, history = historyText),
            setUp = { node(UiTags.RESULTS_ROW) },
        ) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.RESULTS_BACK, UiTags.HISTORY_NOTICE, UiTags.RESULTS_BREAKDOWN_CARD, UiTags.RESULTS_START_ANOTHER_BUTTON)) +
                order(b, listOf(UiTags.GARAGE_NOTICE_GET_PRO, UiTags.HISTORY_NOTICE, UiTags.RESULTS_BREAKDOWN_CARD).map { listOf(it) }) +
                reach(p, UiTags.HISTORY_NOTICE, UiTags.RESULTS_START_ANOTHER_BUTTON)
        }
        // The map's other notice states, which no frame draws on their own: on a Pro or unknown account the Garage notice has
        // no Get Pro under it ("Pro/unknown: without"), and the History notice can show alone. Same cards, same place under
        // the verdict, and nothing else of the notices on the page.
        problems += inState("results: garage_notice_without_get_pro", results(safeRows, garage = fullGarageProOrUnknown)) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, resultsSizes.only(listOf(UiTags.GARAGE_NOTICE))) +
                absent(b, listOf(UiTags.GARAGE_NOTICE_GET_PRO, UiTags.HISTORY_NOTICE, UiTags.RESULTS_ESTIMATED_NOTICE)) +
                order(b, resultsHeaderBands + listOf(UiTags.GARAGE_NOTICE, UiTags.RESULTS_BREAKDOWN_CARD).map { listOf(it) }, resultsStacks) +
                reach(p, UiTags.GARAGE_NOTICE, UiTags.RESULTS_START_ANOTHER_BUTTON) + touchTargets(p)
        }
        problems += inState("results: history_notice_alone", results(safeRows, history = historyText)) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, resultsSizes.only(listOf(UiTags.HISTORY_NOTICE))) +
                absent(b, listOf(UiTags.GARAGE_NOTICE, UiTags.GARAGE_NOTICE_GET_PRO, UiTags.RESULTS_ESTIMATED_NOTICE)) +
                order(b, resultsHeaderBands + listOf(UiTags.HISTORY_NOTICE, UiTags.RESULTS_BREAKDOWN_CARD).map { listOf(it) }, resultsStacks) +
                reach(p, UiTags.HISTORY_NOTICE, UiTags.RESULTS_START_ANOTHER_BUTTON) + touchTargets(p)
        }
        // results__safe_scrolled_to_end: the page is scrolled to its footer note; the card ends above it.
        problems += inState("results: safe_scrolled_to_end", results(safeRows), setUp = { node(UiTags.RESULTS_FOOTER_NOTE) }) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, resultsSizes.only(listOf(UiTags.RESULTS_FOOTER_NOTE, UiTags.RESULTS_START_ANOTHER_BUTTON, UiTags.RESULTS_BACK))) +
                shown(b, listOf(UiTags.RESULTS_BACK, UiTags.RESULTS_RIG_NAME, UiTags.RESULTS_FOOTER_NOTE, UiTags.RESULTS_START_ANOTHER_BUTTON)) +
                order(b, listOf(listOf(UiTags.RESULTS_BREAKDOWN_CARD), listOf(UiTags.RESULTS_FOOTER_NOTE))) +
                reach(p, UiTags.RESULTS_FOOTER_NOTE, UiTags.RESULTS_START_ANOTHER_BUTTON)
        }

        assertTrue("the Results frame differs from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- A small phone and a large font ---------------------------------------------------------------------

    @Test
    fun aSmallPhone360x640ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640))

    @Test
    fun aSmallPhone360x640AtFontScale2ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640, fontScale = 2f))

    // Both screens: the primary action (I Understand, Continue; Start another check) stays on the screen while the page
    // scrolls, every part of the page can be scrolled to, nothing is wider than the screen and the 48 dp rule holds. On
    // the Results page with all the notices showing there is exactly one scroll, the page's own.
    private fun reachEverything(frame: Frame) {
        putOnTheDisplay(frame)
        val problems = mutableListOf<String>()
        // At font scale 2.0 a paragraph is taller than the 640 dp phone's room for it: it is scrolled to, not wholly on show.
        val tall = if (frame.fontScale >= 2f) listOf(UiTags.DISCLAIMER_TITLE, UiTags.DISCLAIMER_BODY_1, UiTags.DISCLAIMER_BODY_2) else emptyList()

        problems += inState("disclaimer: ${frame.name}", disclaimer()) { p ->
            shown(p.bounds(), listOf(UiTags.DISCLAIMER_ACCEPT_BUTTON)) +
                pinnedWhileScrolling(p, scrollTo = UiTags.DISCLAIMER_BODY_2, moves = UiTags.DISCLAIMER_TITLE, pinned = listOf(UiTags.DISCLAIMER_ACCEPT_BUTTON)) +
                reach(p, *(disclaimerTags - tall).toTypedArray()) + reachSome(p, *tall.toTypedArray()) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState("results: all the notices ${frame.name}", results(safeRows.map { it.copy(estimated = true) }, garage = fullGarage, history = historyText)) { p ->
            // The estimate and the card are taller than the room the page has on a phone this small.
            val tallOnes = listOf(UiTags.RESULTS_ESTIMATED_NOTICE, UiTags.RESULTS_BREAKDOWN_CARD)
            val everything = resultsHeader + resultsRowParts + noticeTags + listOf(
                UiTags.RESULTS_ROW_CHEVRON, UiTags.RESULTS_FOOTER_NOTE, UiTags.RESULTS_START_ANOTHER_BUTTON,
            ) - tallOnes
            shown(p.bounds(), listOf(UiTags.RESULTS_BACK, UiTags.RESULTS_START_ANOTHER_BUTTON)) +
                pinnedWhileScrolling(p, scrollTo = UiTags.RESULTS_FOOTER_NOTE, moves = UiTags.RESULTS_VERDICT, pinned = resultsPinned) +
                onePageScroll(p) + cardScrollsWithThePage(p) +
                reach(p, *everything.toTypedArray()) + reachSome(p, *tallOnes.toTypedArray()) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        // The smallest room for the verdict and the row: the band stacks its icon above its words below 380 dp of width
        // (resize-rules.md, "360 x 640"), and from font scale 1.6 a row puts its badge on a line under the label.
        problems += inState("results: safe ${frame.name}", results(safeRows)) { p ->
            val b = p.bounds()
            verdictStacks(p).takeIf { p.widthDp < 380 }.orEmpty() +
                (if (frame.fontScale >= 1.6f) badgeUnderTheLabel(b) else emptyList()) +
                reach(p, UiTags.RESULTS_VERDICT, UiTags.RESULTS_ROW, UiTags.RESULTS_START_ANOTHER_BUTTON) + noneWiderThanTheScreen(p)
        }

        assertTrue("${frame.name}:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Checks of this screen group --------------------------------------------------------------------

    private fun Map<String, Size>.only(tags: List<String>): Map<String, Size> = filterKeys { it in tags }

    // The page scrolls and the pinned parts do not: scrolls to `scrollTo`, and the page's `moves` element really moved (so
    // this is not vacuous) while each pinned element is where it was.
    private fun pinnedWhileScrolling(p: Probe, scrollTo: String, moves: String, pinned: List<String>): List<String> {
        // From the top of the page, whatever an earlier check scrolled to.
        p.rule.onAllNodesWithTag(moves, useUnmergedTree = true).onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val before = p.bounds()
        p.rule.onAllNodesWithTag(scrollTo, useUnmergedTree = true).onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val after = p.bounds()
        val moved = before[moves]?.y != after[moves]?.y
        return listOfNotNull("the page did not scroll to $scrollTo, so what is pinned was not tested".takeIf { !moved }) +
            pinned.mapNotNull { tag ->
                val was = before[tag]
                val now = after[tag]
                when {
                    was == null || now == null -> "$tag is not on the screen"
                    abs(was.y - now.y) > 0.5 -> "$tag moved from ${was.y} to ${now.y} dp when the page scrolled: it should be pinned"
                    !now.visible -> "$tag is not on show after the page scrolled"
                    else -> null
                }
            }
    }

    // resize-rules.md: "The whole body scrolls as one column, including the Results breakdown (the breakdown card no
    // longer scrolls inside itself)". There is one element that scrolls, and it is the page.
    private fun onePageScroll(p: Probe): List<String> {
        val scrollers = p.rule.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsActions.ScrollBy), useUnmergedTree = true)
            .fetchSemanticsNodes().size
        return listOfNotNull("$scrollers elements scroll on the Results screen, not one (a list inside a card?)".takeIf { scrollers != 1 })
    }

    // The card is in the page: scrolling the page to its end moves the card (a card that scrolled inside itself would stay).
    private fun cardScrollsWithThePage(p: Probe): List<String> {
        p.rule.onAllNodesWithTag(UiTags.RESULTS_VERDICT, useUnmergedTree = true).onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val before = p.bounds()[UiTags.RESULTS_BREAKDOWN_CARD]?.y ?: return listOf("the breakdown card is not on the screen")
        p.rule.onAllNodesWithTag(UiTags.RESULTS_FOOTER_NOTE, useUnmergedTree = true).onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val after = p.bounds()[UiTags.RESULTS_BREAKDOWN_CARD]?.y ?: return listOf("the breakdown card is not on the screen after scrolling")
        return listOfNotNull("the breakdown card stayed at $before dp when the page scrolled".takeIf { abs(before - after) < 0.5 })
    }

    // An element taller than the room above the pinned footer (the estimate's 15 lines, a long paragraph or the card at a
    // large font on 640 dp) cannot be wholly on show whatever the scroll: it is scrolled to, and some of it is on show,
    // starting from its top.
    private fun reachSome(p: Probe, vararg tags: String): List<String> = tags.mapNotNull { tag ->
        val nodes = p.rule.onAllNodesWithTag(tag, useUnmergedTree = true)
        if (nodes.fetchSemanticsNodes().isEmpty()) return@mapNotNull "$tag is not on the screen"
        nodes.onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val b = p.bounds()[tag] ?: return@mapNotNull "$tag is not on the screen after scrolling to it"
        "$tag cannot be scrolled into view".takeIf { !b.visible || b.y >= p.heightDp }
    }

    private fun rowCount(b: Map<String, TaggedBounds>, expected: Int): List<String> {
        val found = b[UiTags.RESULTS_ROW]?.count ?: 0
        return listOfNotNull("$found breakdown rows are on the screen, not $expected".takeIf { found != expected })
    }

    // The chevron is only on a row with a note (the map: "Only on rows that have a note").
    private fun chevronsOnlyWhereThereIsANote(b: Map<String, TaggedBounds>, withNotes: Int): List<String> {
        val found = b[UiTags.RESULTS_ROW_CHEVRON]?.count ?: 0
        return listOfNotNull("$found chevrons are on the screen, not $withNotes (one for each row that has a note)".takeIf { found != withNotes })
    }

    // At least `times` elements with the tag say the words (a tag on a container has the words in it).
    private fun words(p: Probe, tag: String, text: String, times: Int = 1): List<String> {
        val found = p.rule.nodesWithTagShowing(tag, text)
        return listOfNotNull("$tag says \"$text\" $found times, not $times".takeIf { found != times })
    }

    // resize-rules.md, "360 x 640": the icon above the words, not beside them.
    private fun verdictStacks(p: Probe): List<String> {
        val icon = p.bounds()[UiTags.RESULTS_VERDICT_ICON] ?: return listOf("the verdict icon is not on the screen")
        val headline = p.rule.onNode(hasAnyAncestor(hasTestTag(UiTags.RESULTS_VERDICT)) and hasText("Safe to Tow"), useUnmergedTree = true)
            .fetchSemanticsNode().layoutInfo.coordinates.positionOnScreen().y / Frame.PX_PER_DP
        return listOfNotNull(
            "the verdict icon (${icon.y} to ${icon.y + icon.height} dp) is not above the headline (at $headline dp)"
                .takeIf { icon.y + icon.height > headline + 0.5 },
        )
    }

    // resize-rules.md, "Font scale 2.0": "label on its own line, badge on the next line".
    private fun badgeUnderTheLabel(b: Map<String, TaggedBounds>): List<String> {
        val label = b[UiTags.RESULTS_ROW_LABEL] ?: return listOf("the row label is not on the screen")
        val badge = b[UiTags.RESULTS_ROW_BADGE] ?: return listOf("the row badge is not on the screen")
        return listOfNotNull(
            "the badge (top ${badge.y} dp) is not under the label (bottom ${label.y + label.height} dp)"
                .takeIf { badge.y < label.y + label.height - 0.5 },
        )
    }

    // --- What the map says ------------------------------------------------------------------------------

    private val disclaimerTags = listOf(
        UiTags.DISCLAIMER_ICON, UiTags.DISCLAIMER_TITLE, UiTags.DISCLAIMER_BODY_1, UiTags.DISCLAIMER_BODY_2,
        UiTags.DISCLAIMER_ACCEPT_BUTTON,
    )

    // The page has 20 dp side margins (the frame's text starts at 20 dp); the footer's button has the usual 16.
    private val disclaimerSizes: Map<String, Size> = mapOf(
        UiTags.DISCLAIMER_ICON to square(72),
        UiTags.DISCLAIMER_TITLE to Size(Dim.Fill(40), about(68)),
        UiTags.DISCLAIMER_BODY_1 to Size(Dim.Fill(40), about(144)),
        UiTags.DISCLAIMER_BODY_2 to Size(Dim.Fill(40), about(168)),
        UiTags.DISCLAIMER_ACCEPT_BUTTON to Size(Dim.Fill(32), fixed(56)),
    )

    private val resultsHeader = listOf(
        UiTags.RESULTS_BACK, UiTags.RESULTS_RIG_NAME, UiTags.RESULTS_DATE, UiTags.RESULTS_VERDICT, UiTags.RESULTS_VERDICT_ICON,
    )

    // The parts of the first row, in the frames' numbers 7 to 13 (the chevron, the 14th, is on the third row's line: the
    // first row has no note).
    private val resultsRowParts = listOf(
        UiTags.RESULTS_ROW, UiTags.RESULTS_ROW_ICON, UiTags.RESULTS_ROW_LABEL, UiTags.RESULTS_ROW_BADGE, UiTags.RESULTS_ROW_BAR,
        UiTags.RESULTS_ROW_VALUES, UiTags.RESULTS_ROW_PCT,
    )

    private val noticeTags = listOf(
        UiTags.RESULTS_ESTIMATED_NOTICE, UiTags.GARAGE_NOTICE, UiTags.GARAGE_NOTICE_GET_PRO, UiTags.HISTORY_NOTICE,
    )

    // What does not move when the page scrolls: the top bar and the footer button.
    private val resultsPinned = listOf(
        UiTags.RESULTS_BACK, UiTags.RESULTS_RIG_NAME, UiTags.RESULTS_DATE, UiTags.RESULTS_START_ANOTHER_BUTTON,
    )

    // The top bar's row (Back, the name and the date beside it), then the band: the verdict and its icon.
    private val resultsHeaderBands = listOf(
        listOf(UiTags.RESULTS_BACK, UiTags.RESULTS_RIG_NAME, UiTags.RESULTS_DATE),
        listOf(UiTags.RESULTS_VERDICT, UiTags.RESULTS_VERDICT_ICON),
    )

    // The card, then in its first row: the line of the icon, the label and the badge, the bar, the line of the values and
    // the percentage (frame numbers 6 to 13).
    private val resultsBodyBands = listOf(
        listOf(UiTags.RESULTS_BREAKDOWN_CARD, UiTags.RESULTS_ROW),
        listOf(UiTags.RESULTS_ROW_ICON, UiTags.RESULTS_ROW_LABEL, UiTags.RESULTS_ROW_BADGE),
        listOf(UiTags.RESULTS_ROW_BAR),
        listOf(UiTags.RESULTS_ROW_VALUES, UiTags.RESULTS_ROW_PCT),
    )

    // Stacked in a band: the name over the date, the verdict over its icon, the card over the row over its bar and values.
    private val resultsStacks = listOf(
        listOf(UiTags.RESULTS_RIG_NAME, UiTags.RESULTS_DATE),
        listOf(UiTags.RESULTS_VERDICT, UiTags.RESULTS_VERDICT_ICON),
        listOf(UiTags.RESULTS_BREAKDOWN_CARD, UiTags.RESULTS_ROW, UiTags.RESULTS_ROW_BAR, UiTags.RESULTS_ROW_VALUES),
    )

    // Side margins of the page are 16 dp, as on every screen; a row's own 16 dp is inside the card.
    private val resultsSizes: Map<String, Size> = mapOf(
        UiTags.RESULTS_BACK to square(48),
        UiTags.RESULTS_RIG_NAME to Size(Dim.Any, about(30)),
        UiTags.RESULTS_DATE to Size(Dim.Any, about(16, 2)),
        UiTags.RESULTS_VERDICT to Size(Dim.Fill(32), about(120)),
        UiTags.RESULTS_VERDICT_ICON to square(64),
        UiTags.RESULTS_ESTIMATED_NOTICE to Size(Dim.Fill(32), about(370, 22)),
        UiTags.GARAGE_NOTICE to Size(Dim.Fill(32), about(66, 10)),
        UiTags.GARAGE_NOTICE_GET_PRO to Size(Dim.Fill(32), fixed(48)),
        UiTags.HISTORY_NOTICE to Size(Dim.Fill(32), about(66, 10)),
        UiTags.RESULTS_BREAKDOWN_CARD to Size(Dim.Fill(32), about(659, 24)),
        UiTags.RESULTS_ROW to Size(Dim.Fill(32), about(104)),
        UiTags.RESULTS_ROW_ICON to square(26),
        UiTags.RESULTS_ROW_LABEL to Size(Dim.Any, about(22, 2)),
        // 112 dp for "Within limit"; 22 dp high.
        UiTags.RESULTS_ROW_BADGE to Size(about(112, 8), about(22, 2)),
        UiTags.RESULTS_ROW_BAR to Size(Dim.Fill(64), fixed(10)),
        UiTags.RESULTS_ROW_VALUES to Size(Dim.Any, about(18, 2)),
        UiTags.RESULTS_ROW_PCT to Size(Dim.Any, about(18, 2)),
        UiTags.RESULTS_ROW_CHEVRON to square(48),
        // Sunken block under the row: as wide as the row's content; its height depends on the words of the note.
        UiTags.RESULTS_ROW_NOTE to Size(Dim.Fill(64), Dim.Any),
        UiTags.RESULTS_FOOTER_NOTE to Size(Dim.Fill(32), about(18, 2)),
        UiTags.RESULTS_START_ANOTHER_BUTTON to Size(Dim.Fill(32), fixed(56)),
    )

    // --- Fixtures -----------------------------------------------------------------------------------------

    private fun row(label: String, tone: Tone, actual: Double, limit: Double, pct: Int, note: String? = null) = BreakdownItem(
        label = label, tone = tone, actual = actual, limit = limit, margin = limit - actual, pct = pct, note = note,
    )

    // The six rows of results__safe: the notes are the app's own words for the three rows that have one.
    private val safeRows = listOf(
        row("Front Axle (Steer)", Tone.SUCCESS, 4_900.0, 6_000.0, 82),
        row("Rear Axle (Drive)", Tone.SUCCESS, 7_600.0, 9_900.0, 77),
        row(
            "Tow Vehicle Total (GVWR)", Tone.SUCCESS, 12_500.0, 14_000.0, 89,
            note = "Steer (4,900) + drive (7,600) = 12,500 lb, which is 1,500 lb under this truck's 14,000 lb GVWR.",
        ),
        row("Trailer Axle(s)", Tone.SUCCESS, 9_600.0, 14_000.0, 69, note = "Trailer axle rating: 2 axle(s) at the tag's per-axle rating."),
        row(
            "Trailer Total (GVWR)", Tone.SUCCESS, 11_100.0, 11_990.0, 93,
            note = "Includes an estimated 1,500 lb pin weight (steer + drive minus your truck's stand-alone weight).",
        ),
        row("Combined Rig Weight", Tone.SUCCESS, 22_100.0, 26_000.0, 85),
    )

    // results__not_safe_row_expanded: the Tow Vehicle row is over its limit.
    private val notSafeRows = safeRows.mapIndexed { index, item ->
        if (index == 2) {
            row(
                item.label, Tone.WARNING, 14_300.0, 14_000.0, 102,
                note = "Steer (5,200) + drive (9,100) = 14,300 lb, which is 300 lb over this truck's 14,000 lb GVWR.",
            )
        } else {
            item
        }
    }

    // results__partially_checked: no GCWR (five rows), the trailer's two rows not checked.
    private val partialRows = listOf(
        safeRows[0], safeRows[1], safeRows[2],
        row("Trailer Axle(s)", Tone.INSUFFICIENT, 0.0, 14_000.0, 0, note = "Trailer axle rating: 2 axle(s) at the tag's per-axle rating."),
        row("Trailer Total (GVWR)", Tone.INSUFFICIENT, 0.0, 11_990.0, 0, note = "No trailer reading yet."),
    )

    // results__not_enough_information: five rows, none checked.
    private val nothingCheckedRows = listOf(
        row("Front Axle (Steer)", Tone.INSUFFICIENT, 0.0, 6_000.0, 0),
        row("Rear Axle (Drive)", Tone.INSUFFICIENT, 0.0, 9_900.0, 0),
        row("Tow Vehicle Total (GVWR)", Tone.INSUFFICIENT, 0.0, 14_000.0, 0, note = "No scale reading yet."),
        row("Trailer Axle(s)", Tone.INSUFFICIENT, 0.0, 14_000.0, 0, note = "Trailer axle rating: 2 axle(s) at the tag's per-axle rating."),
        row("Trailer Total (GVWR)", Tone.INSUFFICIENT, 0.0, 11_990.0, 0, note = "No trailer reading yet."),
    )

    private fun disclaimer(): @Composable () -> Unit = { DisclaimerScreen(onAcknowledge = {}) }

    // A full Garage on a Free account (with Get Pro), the same on a Pro or unknown account (without), and a History
    // that did not save: the map's states for the three notices.
    private val fullGarage = GarageNotice("Your Garage is full (3 of 3), so \"Lakeside\" wasn't saved to it. Your check is not affected.", offerPro = true)
    private val fullGarageProOrUnknown = fullGarage.copy(offerPro = false)
    private val historyText = "We couldn't save this check to your History. Your check is not affected."

    private fun results(rows: List<BreakdownItem>, garage: GarageNotice? = null, history: String? = null): @Composable () -> Unit = {
        ResultsScreen(
            rigNickname = "Summer rig",
            breakdown = rows,
            verdict = verdictFor(rows),
            onStartAnother = {},
            garageNotice = garage,
            historyNotice = history,
        )
    }
}
