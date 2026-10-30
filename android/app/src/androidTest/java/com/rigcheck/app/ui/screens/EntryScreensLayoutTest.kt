package com.rigcheck.app.ui.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.text.TextLayoutResult
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
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
import com.rigcheck.app.testsupport.order
import com.rigcheck.app.testsupport.reach
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.testsupport.shown
import com.rigcheck.app.testsupport.sizes
import com.rigcheck.app.testsupport.square
import com.rigcheck.app.testsupport.touchTargets
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.applyScan
import com.rigcheck.app.ui.navigation.EntryModule
import kotlin.math.abs
import kotlinx.serialization.json.JsonObject
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #193: the Truck Tag, Trailer Tag and Scale Ticket entry screens, checked against the designer's map
// (docs/android-redesign/design-return/ui-redesign-map.json). For every element of those screens, in the states below
// (the frames' states in annotation-legends.json):
//   - it is displayed (found by its UiTags tag, scrolled into view if it is in the form, and then wholly on the screen);
//   - the reading order is the frame's: the bands, one per row or block, come one after the other by their tops (see
//     `order` in testsupport/LayoutChecks.kt). Measured before any scrolling, so the form's own order is what is
//     compared; the pinned parts (the reference card, the footer) are held to the region instead: they do not move when
//     the form scrolls;
//   - its measured width and height are the map's `new_width` and `new_height`. TOLERANCE: 1.5 dp where the map gives a
//     fixed size, 4 dp (2 dp on a single line of text) on a height the map gives with a "~", up to 10 dp for a
//     notice, whose lines wrap a little differently in the bundled font than in the browser the frames were drawn in;
//     "fill" is the full width of the column the element is in, "wrap" has no width to check;
//   - every clickable element is at least 48 x 48 dp.
// And on a 360 x 640 dp phone, at font scale 2.0, with the keyboard open on the screens that have fields, the screen's
// primary action (and each field the user has to reach) can be scrolled to and is then wholly on show, with nothing
// wider than the screen.
//
// It changes the display's size, density and font scale for the run and puts them back (as LayoutCaptureTest does),
// and no state sends a Scan or calls the network.
//
// #199: with a field that has a line on the label focused, the pinned card also shows the map's `reference_focus_badge`
// (its name, at the right of the caption row beside the hint, above the photo); the "gvwr focused" states below are the
// designer's `filled` frames (the field has focus, the keyboard is closed) and the keyboard states show it with the
// keyboard open. The badge's text is never cut off, also on a small phone at font scale 2.0.
@RunWith(AndroidJUnit4::class)
class EntryScreensLayoutTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-193-screenshots")

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

    // --- Truck Tag, 412 x 892 -----------------------------------------------------------------------------

    @Test
    fun theTruckTagFrame412x892MatchesTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        problems += inState("truck_tag_entry: blank", truck()) { p ->
            val b = p.bounds()
            val tags = truckHeader + UiTags.TRUCK_INSTRUCTIONS + UiTags.TRUCK_DESCRIPTION + UiTags.TRUCK_NAME_FIELD +
                UiTags.TRUCK_GVWR_FIELD + UiTags.TRUCK_NEXT_BUTTON
            sizes(b, p.widthDp, truckSizes.only(tags)) +
                order(b, truckHeaderBands + listOf(listOf(UiTags.TRUCK_INSTRUCTIONS), listOf(UiTags.TRUCK_DESCRIPTION), listOf(UiTags.TRUCK_NAME_FIELD), listOf(UiTags.TRUCK_GVWR_FIELD))) +
                pinned(p, UiTags.SCAN_STANDALONE_TICKET, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_IMAGE, UiTags.TRUCK_NEXT_BUTTON) +
                reach(p, *tags.toTypedArray()) + touchTargets(p)
        }
        problems += inState("truck_tag_entry: filled", truck(filledTruck), setUp = { node(UiTags.TRUCK_GVWR_FIELD) }) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.TRUCK_GVWR_FIELD, UiTags.TRUCK_FRONT_GAWR_FIELD, UiTags.TRUCK_REAR_GAWR_FIELD, UiTags.TRUCK_GCWR)
            sizes(b, p.widthDp, truckSizes.only(tags)) +
                order(b, tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState("truck_tag_entry: scan_notice", truck(notice = noticeFor(EntryModule.TRUCK))) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.SCAN_NOTICE, UiTags.TRUCK_INSTRUCTIONS, UiTags.TRUCK_DESCRIPTION, UiTags.TRUCK_NAME_FIELD)
            sizes(b, p.widthDp, truckSizes.only(tags)) +
                order(b, truckHeaderBands + tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        // The states below start scrolled to the part of the form the designer's frame shows (its `scroll_to`), so the
        // screenshot beside the frame is the same view; the order of the form is then compared without the pinned parts.
        problems += inState(
            "truck_tag_entry: gcwr_warning", truck(TruckTag(gvwrLb = 14_000.0, gcwrLb = 13_000.0)),
            setUp = { node(UiTags.TRUCK_GCWR) },
        ) { p ->
            val b = p.bounds()
            val tags = listOf(
                UiTags.TRUCK_GCWR, UiTags.TRUCK_GCWR_HELP, UiTags.TRUCK_GCWR_WARNING, UiTags.TRUCK_STANDALONE_PANEL_TITLE,
                UiTags.TRUCK_STANDALONE_PANEL_BODY, UiTags.SCAN_STANDALONE_TICKET,
            )
            sizes(b, p.widthDp, truckSizes.only(tags)) +
                order(b, tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        val pinWeight = listOf(UiTags.TRUCK_PIN_WEIGHT_LABEL, UiTags.PIN_WEIGHT_PCT_SLIDER, UiTags.TRUCK_PIN_WEIGHT_CAPTION)
        problems += inState("truck_tag_entry: standalone_blank", truck(), setUp = { node(UiTags.TRUCK_STANDALONE_PANEL) }) { p ->
            val b = p.bounds()
            val tags = standalonePanel + pinWeight
            sizes(b, p.widthDp, truckSizes.only(tags + UiTags.TRUCK_GCWR_HELP)) +
                order(b, standaloneBands + pinWeight.map { listOf(it) }) +
                reach(p, UiTags.TRUCK_GCWR_HELP, *tags.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState("truck_tag_entry: standalone_pin_weight", truck(), setUp = { node(UiTags.TRUCK_PIN_WEIGHT_CAPTION) }) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.SCAN_STANDALONE_TICKET, UiTags.TRUCK_STANDALONE_LABEL, UiTags.TRUCK_STANDALONE_INFO, UiTags.TRUCK_STANDALONE_FIELD) + pinWeight
            sizes(b, p.widthDp, truckSizes.only(tags + UiTags.TRUCK_STANDALONE_PANEL)) +
                order(b, standaloneBands.drop(4) + pinWeight.map { listOf(it) }) +
                pinned(p, UiTags.TRUCK_GCWR, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_IMAGE, UiTags.TRUCK_NEXT_BUTTON) +
                reach(p, *tags.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState("truck_tag_entry: standalone_info", truck(), setUp = { tap(UiTags.TRUCK_STANDALONE_INFO) }) { p ->
            val b = p.bounds()
            // The panel is taller than its blank 480 dp with the info text in it (and no taller than the screen can show
            // whole): what is in it is checked, and the panel's own height only in the blank state.
            val tags = standalonePanel - UiTags.TRUCK_STANDALONE_PANEL + UiTags.TRUCK_STANDALONE_INFO_TEXT
            sizes(b, p.widthDp, truckSizes.only(tags)) +
                order(b, truckHeaderBands + standaloneBands.take(5) +
                    listOf(listOf(UiTags.TRUCK_STANDALONE_LABEL, UiTags.TRUCK_STANDALONE_INFO), listOf(UiTags.TRUCK_STANDALONE_INFO_TEXT), listOf(UiTags.TRUCK_STANDALONE_FIELD))) +
                reach(p, *tags.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState(
            "truck_tag_entry: standalone_filled", truck(TruckTag(standaloneWeightLb = 9_500.0)),
            setUp = { node(UiTags.TRUCK_STANDALONE_PANEL) },
        ) { p ->
            val b = p.bounds()
            // The pin-weight estimate is only for a weight that is not known: the slider, its label and its caption are gone.
            absent(b, listOf(UiTags.TRUCK_PIN_WEIGHT_LABEL, UiTags.PIN_WEIGHT_PCT_SLIDER, UiTags.TRUCK_PIN_WEIGHT_CAPTION)) +
                sizes(b, p.widthDp, truckSizes.only(standalonePanel - UiTags.TRUCK_STANDALONE_PANEL)) +
                reach(p, *(standalonePanel - UiTags.TRUCK_STANDALONE_PANEL).toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState(
            "truck_tag_entry: standalone_scan_in_flight", truck(scanState = ScanUiState.Loading),
            setUp = { node(UiTags.TRUCK_STANDALONE_PANEL) },
        ) { p ->
            // The Scan button reads "Reading…" and is off (its test), and Back is off too: nothing starts a second Scan or leaves.
            p.rule.onNodeWithTag(UiTags.TRUCK_BACK, useUnmergedTree = true).assertIsNotEnabled()
            p.rule.onNodeWithTag(UiTags.SCAN_STANDALONE_TICKET, useUnmergedTree = true).scrollToIfScrollable().assertIsNotEnabled()
            reach(p, UiTags.SCAN_STANDALONE_TICKET, UiTags.TRUCK_NEXT_BUTTON)
        }
        // truck_tag_entry__filled: the GVWR has focus (the keyboard is closed), so the card is cropped to its line, with its badge.
        problems += inState(
            "truck_tag_entry: gvwr focused", truck(filledTruck),
            setUp = {
                tap(UiTags.TRUCK_GVWR_FIELD)
                awaitKeyboardShown()
                hideKeyboard()
            },
        ) { p ->
            val b = p.bounds()
            val form = listOf(UiTags.TRUCK_GVWR_FIELD, UiTags.TRUCK_FRONT_GAWR_FIELD, UiTags.TRUCK_REAR_GAWR_FIELD, UiTags.TRUCK_GCWR)
            val card = listOf(UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_IMAGE)
            sizes(b, p.widthDp, truckSizes.only(card + form)) +
                order(
                    b,
                    truckHeaderBands.take(2) + listOf(listOf(UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_FOCUS_BADGE), listOf(UiTags.TRUCK_REFERENCE_IMAGE)) +
                        form.map { listOf(it) },
                ) +
                badgeBesideTheHint(b, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_HINT) +
                badgeTextIsNotCutOff(p, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, "GVWR") +
                pinned(p, UiTags.TRUCK_GCWR, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_IMAGE, UiTags.TRUCK_NEXT_BUTTON) +
                reach(p, *form.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState(
            "truck_tag_entry: keyboard_open", truck(filledTruck),
            setUp = {
                tap(UiTags.TRUCK_FRONT_GAWR_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            val b = p.bounds()
            // The bar is compact and drops the step indicator; the card stays pinned, cropped to the field being typed
            // in, with its badge; the field and the footer are above the keyboard.
            absent(b, listOf(UiTags.TRUCK_STEP_BAR)) +
                shown(b, listOf(UiTags.TRUCK_BACK, UiTags.TRUCK_TITLE, UiTags.TRUCK_CREDIT_CHIP, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_IMAGE)) +
                sizes(b, p.widthDp, truckSizes.only(listOf(UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_IMAGE))) +
                badgeBesideTheHint(b, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_HINT) +
                badgeTextIsNotCutOff(p, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, "Front GAWR") +
                pinned(p, UiTags.TRUCK_GCWR, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_IMAGE, UiTags.TRUCK_NEXT_BUTTON) +
                reach(p, UiTags.TRUCK_FRONT_GAWR_FIELD, UiTags.TRUCK_REAR_GAWR_FIELD, UiTags.TRUCK_NEXT_BUTTON)
        }

        assertTrue("the Truck Tag frame differs from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Trailer Tag, 412 x 892 ---------------------------------------------------------------------------

    @Test
    fun theTrailerTagFrame412x892MatchesTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        problems += inState("trailer_tag_entry: blank", trailer()) { p ->
            val b = p.bounds()
            val tags = trailerHeader + listOf(UiTags.TRAILER_INSTRUCTIONS, UiTags.TRAILER_DESCRIPTION, UiTags.TRAILER_NAME_FIELD, UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_NEXT_BUTTON)
            sizes(b, p.widthDp, trailerSizes.only(tags)) +
                order(b, trailerHeaderBands + listOf(UiTags.TRAILER_INSTRUCTIONS, UiTags.TRAILER_DESCRIPTION, UiTags.TRAILER_NAME_FIELD, UiTags.TRAILER_GVWR_FIELD).map { listOf(it) }) +
                pinned(p, UiTags.TRAILER_UVW_FIELD, UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_IMAGE, UiTags.TRAILER_NEXT_BUTTON) +
                reach(p, *tags.toTypedArray()) + touchTargets(p)
        }
        problems += inState("trailer_tag_entry: filled", trailer(filledTrailer), setUp = { node(UiTags.TRAILER_GVWR_FIELD) }) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_GAWR_FIELD, UiTags.TRAILER_AXLE_COUNT_FIELD, UiTags.TRAILER_AXLE_COUNT_HELP, UiTags.TRAILER_UVW_FIELD)
            sizes(b, p.widthDp, trailerSizes.only(tags)) +
                order(b, tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.TRAILER_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState("trailer_tag_entry: scan_notice", trailer(notice = noticeFor(EntryModule.TRAILER))) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.SCAN_NOTICE, UiTags.TRAILER_INSTRUCTIONS, UiTags.TRAILER_DESCRIPTION, UiTags.TRAILER_NAME_FIELD)
            sizes(b, p.widthDp, trailerSizes.only(tags)) +
                order(b, trailerHeaderBands + tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.TRAILER_NEXT_BUTTON) + touchTargets(p)
        }
        // trailer_tag_entry__filled: the GVWR has focus (the keyboard is closed), so the card is cropped to its line, with its badge.
        problems += inState(
            "trailer_tag_entry: gvwr focused", trailer(filledTrailer),
            setUp = {
                tap(UiTags.TRAILER_GVWR_FIELD)
                awaitKeyboardShown()
                hideKeyboard()
            },
        ) { p ->
            val b = p.bounds()
            val form = listOf(UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_GAWR_FIELD, UiTags.TRAILER_AXLE_COUNT_FIELD, UiTags.TRAILER_UVW_FIELD)
            val card = listOf(UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_IMAGE)
            sizes(b, p.widthDp, trailerSizes.only(card + form)) +
                order(
                    b,
                    trailerHeaderBands.take(2) + listOf(listOf(UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_FOCUS_BADGE), listOf(UiTags.TRAILER_REFERENCE_IMAGE)) +
                        form.map { listOf(it) },
                ) +
                badgeBesideTheHint(b, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_HINT) +
                badgeTextIsNotCutOff(p, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, "GVWR") +
                pinned(p, UiTags.TRAILER_UVW_FIELD, UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_IMAGE, UiTags.TRAILER_NEXT_BUTTON) +
                reach(p, *form.toTypedArray(), UiTags.TRAILER_NEXT_BUTTON) + touchTargets(p)
        }
        problems += inState(
            "trailer_tag_entry: keyboard_open", trailer(filledTrailer),
            setUp = {
                tap(UiTags.TRAILER_UVW_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            val b = p.bounds()
            absent(b, listOf(UiTags.TRAILER_STEP_BAR)) +
                shown(b, listOf(UiTags.TRAILER_BACK, UiTags.TRAILER_TITLE, UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_IMAGE)) +
                sizes(b, p.widthDp, trailerSizes.only(listOf(UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_IMAGE))) +
                badgeBesideTheHint(b, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_HINT) +
                badgeTextIsNotCutOff(p, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, "UVW") +
                pinned(p, UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_IMAGE, UiTags.TRAILER_NEXT_BUTTON) +
                reach(p, UiTags.TRAILER_AXLE_COUNT_FIELD, UiTags.TRAILER_AXLE_COUNT_HELP, UiTags.TRAILER_UVW_FIELD, UiTags.TRAILER_NEXT_BUTTON)
        }

        assertTrue("the Trailer Tag frame differs from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Scale Ticket, 412 x 892 ---------------------------------------------------------------------------

    @Test
    fun theScaleTicketFrame412x892MatchesTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        problems += inState("scale_ticket_entry: blank", scale()) { p ->
            val b = p.bounds()
            val tags = scaleHeader + listOf(UiTags.SCALE_INSTRUCTIONS, UiTags.SCALE_REFERENCE_IMAGE, UiTags.SCALE_LEGEND, UiTags.SCALE_LOCATION, UiTags.SCALE_STEER_FIELD, UiTags.SCALE_DRIVE_FIELD, UiTags.SCALE_CHECK_BUTTON)
            sizes(b, p.widthDp, scaleSizes.only(tags)) +
                order(b, scaleHeaderBands + listOf(UiTags.SCALE_INSTRUCTIONS, UiTags.SCALE_REFERENCE_IMAGE, UiTags.SCALE_LEGEND, UiTags.SCALE_LOCATION, UiTags.SCALE_STEER_FIELD, UiTags.SCALE_DRIVE_FIELD).map { listOf(it) }) +
                photoBadges(b) +
                pinned(p, UiTags.SCALE_GROSS_FIELD, UiTags.SCALE_CHECK_BUTTON) +
                reach(p, *tags.toTypedArray()) + touchTargets(p)
        }
        problems += inState("scale_ticket_entry: filled", scale(filledScale), setUp = { node(UiTags.SCALE_LEGEND) }) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.SCALE_LEGEND, UiTags.SCALE_LOCATION, UiTags.SCALE_STEER_FIELD, UiTags.SCALE_DRIVE_FIELD, UiTags.SCALE_TRAILER_FIELD, UiTags.SCALE_GROSS_FIELD)
            sizes(b, p.widthDp, scaleSizes.only(tags)) +
                order(b, tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.SCALE_CHECK_BUTTON) + touchTargets(p)
        }
        problems += inState("scale_ticket_entry: scan_notice", scale(notice = noticeFor(EntryModule.SCALE))) { p ->
            val b = p.bounds()
            val tags = listOf(UiTags.SCAN_NOTICE, UiTags.SCALE_INSTRUCTIONS, UiTags.SCALE_REFERENCE_IMAGE, UiTags.SCALE_LEGEND, UiTags.SCALE_LOCATION, UiTags.SCALE_STEER_FIELD)
            sizes(b, p.widthDp, scaleSizes.only(tags)) +
                order(b, scaleHeaderBands + tags.map { listOf(it) }) +
                reach(p, *tags.toTypedArray(), UiTags.SCALE_CHECK_BUTTON) + touchTargets(p)
        }
        problems += inState(
            "scale_ticket_entry: keyboard_open", scale(filledScale),
            setUp = {
                tap(UiTags.SCALE_STEER_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            val b = p.bounds()
            // The scale screen has no pinned card: its whole form scrolls above the keyboard.
            absent(b, listOf(UiTags.SCALE_STEP_BAR)) +
                shown(b, listOf(UiTags.SCALE_BACK, UiTags.SCALE_TITLE)) +
                pinned(p, UiTags.SCALE_GROSS_FIELD, UiTags.SCALE_CHECK_BUTTON) +
                reach(p, UiTags.SCALE_STEER_FIELD, UiTags.SCALE_DRIVE_FIELD, UiTags.SCALE_TRAILER_FIELD, UiTags.SCALE_GROSS_FIELD, UiTags.SCALE_CHECK_BUTTON)
        }

        assertTrue("the Scale Ticket frame differs from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- A small phone, a large font, the keyboard ----------------------------------------------------------

    @Test
    fun aSmallPhone360x640ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640))

    @Test
    fun aSmallPhone360x640AtFontScale2ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640, fontScale = 2f))

    // The primary action of each screen (Next, Next, Check Weights) and every field and control of its form: a scroll puts
    // it wholly on show, nothing is wider than the screen, and the 48 dp rule holds. With the keyboard open the card
    // that no longer leaves room for the form scrolls with it.
    private fun reachEverything(frame: Frame) {
        putOnTheDisplay(frame)
        val problems = mutableListOf<String>()
        val truckForm = listOf(
            UiTags.TRUCK_DESCRIPTION, UiTags.TRUCK_NAME_FIELD, UiTags.TRUCK_GVWR_FIELD, UiTags.TRUCK_FRONT_GAWR_FIELD,
            UiTags.TRUCK_REAR_GAWR_FIELD, UiTags.TRUCK_GCWR, UiTags.SCAN_STANDALONE_TICKET, UiTags.TRUCK_STANDALONE_INFO,
            UiTags.TRUCK_STANDALONE_FIELD, UiTags.PIN_WEIGHT_PCT_SLIDER,
        )

        problems += inState("truck_tag_entry: blank", truck()) { p ->
            reach(p, *truckForm.toTypedArray(), UiTags.TRUCK_NEXT_BUTTON, UiTags.TRUCK_BACK, UiTags.TRUCK_CREDIT_CHIP) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState(
            "truck_tag_entry: keyboard open", truck(),
            setUp = {
                tap(UiTags.TRUCK_GVWR_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            reach(p, UiTags.TRUCK_GVWR_FIELD, UiTags.TRUCK_NEXT_BUTTON) + noneWiderThanTheScreen(p)
        }
        // The longest badges on the smallest room: Front GAWR (Truck) and GAWR per axle (Trailer), the keyboard closed.
        problems += inState(
            "truck_tag_entry: front gawr focused", truck(),
            setUp = {
                tap(UiTags.TRUCK_FRONT_GAWR_FIELD)
                awaitKeyboardShown()
                hideKeyboard()
            },
        ) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_IMAGE)) +
                badgeBesideTheHint(b, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, UiTags.TRUCK_REFERENCE_HINT) +
                badgeTextIsNotCutOff(p, UiTags.TRUCK_REFERENCE_FOCUS_BADGE, "Front GAWR") +
                noneWiderThanTheScreen(p)
        }
        problems += inState(
            "trailer_tag_entry: gawr focused", trailer(),
            setUp = {
                tap(UiTags.TRAILER_GAWR_FIELD)
                awaitKeyboardShown()
                hideKeyboard()
            },
        ) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_IMAGE)) +
                badgeBesideTheHint(b, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, UiTags.TRAILER_REFERENCE_HINT) +
                badgeTextIsNotCutOff(p, UiTags.TRAILER_REFERENCE_FOCUS_BADGE, "GAWR per axle") +
                noneWiderThanTheScreen(p)
        }
        problems += inState("trailer_tag_entry: blank", trailer()) { p ->
            reach(
                p, UiTags.TRAILER_DESCRIPTION, UiTags.TRAILER_NAME_FIELD, UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_GAWR_FIELD,
                UiTags.TRAILER_AXLE_COUNT_FIELD, UiTags.TRAILER_AXLE_COUNT_HELP, UiTags.TRAILER_UVW_FIELD,
                UiTags.TRAILER_NEXT_BUTTON, UiTags.TRAILER_BACK,
            ) + noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState(
            "trailer_tag_entry: keyboard open", trailer(),
            setUp = {
                tap(UiTags.TRAILER_GVWR_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            reach(p, UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_NEXT_BUTTON) + noneWiderThanTheScreen(p)
        }
        problems += inState("scale_ticket_entry: blank", scale()) { p ->
            reach(
                p, UiTags.SCALE_REFERENCE_IMAGE, UiTags.SCALE_LEGEND, UiTags.SCALE_LOCATION, UiTags.SCALE_STEER_FIELD,
                UiTags.SCALE_DRIVE_FIELD, UiTags.SCALE_TRAILER_FIELD, UiTags.SCALE_GROSS_FIELD, UiTags.SCALE_CHECK_BUTTON,
                UiTags.SCALE_BACK,
            ) + noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState(
            "scale_ticket_entry: keyboard open", scale(),
            setUp = {
                tap(UiTags.SCALE_STEER_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            reach(p, UiTags.SCALE_STEER_FIELD, UiTags.SCALE_CHECK_BUTTON) + noneWiderThanTheScreen(p)
        }

        assertTrue("${frame.name}:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Checks of this screen group --------------------------------------------------------------------

    private fun Map<String, Size>.only(tags: List<String>): Map<String, Size> = filterKeys { it in tags }

    // The pinned parts stay where they are while the form scrolls (and the form really scrolled, so this is not vacuous).
    private fun pinned(p: Probe, scrollTo: String, vararg tags: String): List<String> {
        val before = p.bounds()
        p.rule.onAllNodesWithTag(scrollTo, useUnmergedTree = true).onFirst().scrollToIfScrollable()
        p.rule.waitForIdle()
        val after = p.bounds()
        val moved = before[scrollTo]?.y != after[scrollTo]?.y
        return listOfNotNull("the form did not scroll to $scrollTo, so what is pinned was not tested".takeIf { !moved }) +
            tags.mapNotNull { tag ->
                val was = before[tag]
                val now = after[tag]
                when {
                    was == null || now == null -> "$tag is not on the screen"
                    abs(was.y - now.y) > 0.5 -> "$tag moved from ${was.y} to ${now.y} dp when the form scrolled: it should be pinned"
                    !now.visible -> "$tag is not on show after the form scrolled"
                    else -> null
                }
            }
    }

    // truck.reference_focus_badge, trailer.reference_focus_badge: in the caption row, at the right of the hint, on the
    // same row as it (the map's region "header", the badge after the hint in the reading order).
    private fun badgeBesideTheHint(b: Map<String, TaggedBounds>, badge: String, hint: String): List<String> {
        val badgeBounds = b[badge] ?: return listOf("$badge is not on the screen")
        val hintBounds = b[hint] ?: return listOf("$hint is not on the screen")
        return listOfNotNull(
            "$badge (x ${badgeBounds.x}) is not at the right of $hint (right edge ${hintBounds.x + hintBounds.width})"
                .takeIf { badgeBounds.x < hintBounds.x + hintBounds.width - 0.5 },
            "$badge starts at ${badgeBounds.y} dp, not on the row of $hint (${hintBounds.y} dp)"
                .takeIf { badgeBounds.y > hintBounds.y + hintBounds.height || badgeBounds.y + badgeBounds.height < hintBounds.y },
        )
    }

    // The badge names the field in full: its text is one line, not ellipsised, and the line's right edge and its
    // bottom are inside the box the text is laid out in. (`hasVisualOverflow` is not used: it compares the box with the
    // width the text was offered, so it is true for any text that does not fill its row.)
    private fun badgeTextIsNotCutOff(p: Probe, badge: String, text: String): List<String> {
        val node = p.rule.onNode(hasText(text) and hasAnyAncestor(hasTestTag(badge)), useUnmergedTree = true)
        val results = mutableListOf<TextLayoutResult>()
        val read = node.fetchSemanticsNode().config.getOrNull(SemanticsActions.GetTextLayoutResult)?.action?.invoke(results)
        val layout = results.firstOrNull()
        if (read != true || layout == null) return listOf("$badge: the text layout of \"$text\" cannot be read")
        val whole = layout.lineCount == 1 && !layout.isLineEllipsized(0) && layout.getLineEnd(0) == text.length
        val inside = layout.getLineRight(0) <= layout.size.width + 0.5f && layout.getLineBottom(0) <= layout.size.height + 0.5f
        if (whole && inside) return emptyList()
        return listOf(
            "$badge: the text \"$text\" is cut off or wrapped (${layout.lineCount} lines, the line ends at ${layout.getLineRight(0)} px " +
                "and ${layout.getLineBottom(0)} px in a ${layout.size.width} x ${layout.size.height} px box)",
        )
    }

    // scale.reference_image: numbered badges 1 to 5 drawn on the ticket photo, each wholly on it, in the size of the
    // field badges' set (24 dp), the four weights' badges one below another in the order of the steer, drive, trailer
    // and gross lines.
    private fun photoBadges(b: Map<String, TaggedBounds>): List<String> {
        val image = b[UiTags.SCALE_REFERENCE_IMAGE] ?: return listOf("the ticket photo is not on the screen")
        val badges = (1..5).map { it to b["$SCALE_PHOTO_BADGE_TAG$it"] }
        val found = mutableListOf<String>()
        badges.forEach { (number, badge) ->
            if (badge == null) {
                found += "badge $number is not on the ticket photo"
                return@forEach
            }
            if (abs(badge.width - 24) > 1.5 || abs(badge.height - 24) > 1.5) found += "badge $number is ${badge.width} x ${badge.height} dp, not 24 x 24"
            if (badge.x < image.x - 0.5 || badge.x + badge.width > image.x + image.width + 0.5 ||
                badge.y < image.y - 0.5 || badge.y + badge.height > image.y + image.height + 0.5
            ) {
                found += "badge $number is not wholly on the ticket photo: ${badge.x}, ${badge.y} (${badge.width} x ${badge.height}) on ${image.x}, ${image.y} (${image.width} x ${image.height})"
            }
        }
        val weights = badges.filter { it.first >= 2 }.mapNotNull { it.second }
        weights.zipWithNext().forEach { (above, below) ->
            if (below.y < above.y + 20) found += "two of the weights' badges overlap on the photo (tops ${above.y} and ${below.y} dp)"
        }
        return found
    }

    // --- What the map says ------------------------------------------------------------------------------

    private val truckHeader = listOf(UiTags.TRUCK_BACK, UiTags.TRUCK_TITLE, UiTags.TRUCK_CREDIT_CHIP, UiTags.TRUCK_STEP_BAR, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_REFERENCE_IMAGE)
    private val trailerHeader = listOf(UiTags.TRAILER_BACK, UiTags.TRAILER_TITLE, UiTags.TRAILER_STEP_BAR, UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_REFERENCE_IMAGE)
    private val scaleHeader = listOf(UiTags.SCALE_BACK, UiTags.SCALE_TITLE, UiTags.SCALE_STEP_BAR)

    // The top bar's row, the step indicator, the card's caption, the card's image (the frames' numbers 1 to 6).
    private val truckHeaderBands = listOf(
        listOf(UiTags.TRUCK_BACK, UiTags.TRUCK_TITLE, UiTags.TRUCK_CREDIT_CHIP), listOf(UiTags.TRUCK_STEP_BAR),
        listOf(UiTags.TRUCK_REFERENCE_HINT), listOf(UiTags.TRUCK_REFERENCE_IMAGE),
    )
    private val trailerHeaderBands = listOf(
        listOf(UiTags.TRAILER_BACK, UiTags.TRAILER_TITLE), listOf(UiTags.TRAILER_STEP_BAR),
        listOf(UiTags.TRAILER_REFERENCE_HINT), listOf(UiTags.TRAILER_REFERENCE_IMAGE),
    )
    private val scaleHeaderBands = listOf(listOf(UiTags.SCALE_BACK, UiTags.SCALE_TITLE), listOf(UiTags.SCALE_STEP_BAR))

    private val standalonePanel = listOf(
        UiTags.TRUCK_STANDALONE_PANEL, UiTags.TRUCK_STANDALONE_PANEL_TITLE, UiTags.TRUCK_STANDALONE_PANEL_BODY,
        UiTags.SCAN_STANDALONE_TICKET, UiTags.TRUCK_STANDALONE_LABEL, UiTags.TRUCK_STANDALONE_INFO, UiTags.TRUCK_STANDALONE_FIELD,
    )

    // truck_tag_entry__standalone_blank: the help line above the panel, then the panel's title, text, Scan button, the
    // label with its info control, and the field.
    private val standaloneBands = listOf(
        listOf(UiTags.TRUCK_GCWR_HELP), listOf(UiTags.TRUCK_STANDALONE_PANEL), listOf(UiTags.TRUCK_STANDALONE_PANEL_TITLE),
        listOf(UiTags.TRUCK_STANDALONE_PANEL_BODY), listOf(UiTags.SCAN_STANDALONE_TICKET),
        listOf(UiTags.TRUCK_STANDALONE_LABEL, UiTags.TRUCK_STANDALONE_INFO), listOf(UiTags.TRUCK_STANDALONE_FIELD),
    )

    private val topBar = mapOf(
        "back" to square(48),
        "title" to Size(Dim.Any, about(30)),
        // 2.5 dp: three line heights of text, which the font's own metrics move by a pixel or two.
        "step" to Size(Dim.Fill(32), Dim.Exact(76.0, 2.5)),
    )

    private val field = Size(Dim.Fill(32), fixed(56))
    private val primaryButton = Size(Dim.Fill(32), fixed(56))
    private val notice = Size(Dim.Fill(32), about(84, 10))

    // The map gives 22 dp high and as wide as the field's name ("wrap": 61 dp for GVWR, 114 dp for GAWR per axle).
    private val referenceFocusBadge = Size(Dim.Any, about(22, 2))

    private val truckSizes: Map<String, Size> = mapOf(
        UiTags.TRUCK_BACK to topBar.getValue("back"),
        UiTags.TRUCK_TITLE to topBar.getValue("title"),
        UiTags.TRUCK_CREDIT_CHIP to Size(about(125, 6), fixed(48)),
        UiTags.TRUCK_STEP_BAR to topBar.getValue("step"),
        UiTags.TRUCK_REFERENCE_HINT to Size(Dim.Any, about(20, 2)),
        // 58 dp: the card's 16 dp margin, its 1 dp border and its 12 dp padding, on each side.
        UiTags.TRUCK_REFERENCE_IMAGE to Size(Dim.Fill(58), fixed(116)),
        UiTags.TRUCK_REFERENCE_FOCUS_BADGE to referenceFocusBadge,
        UiTags.SCAN_NOTICE to notice,
        UiTags.TRUCK_INSTRUCTIONS to Size(Dim.Fill(32), about(44)),
        UiTags.TRUCK_DESCRIPTION to field,
        UiTags.TRUCK_NAME_FIELD to field,
        UiTags.TRUCK_GVWR_FIELD to field,
        UiTags.TRUCK_FRONT_GAWR_FIELD to field,
        UiTags.TRUCK_REAR_GAWR_FIELD to field,
        UiTags.TRUCK_GCWR to field,
        UiTags.TRUCK_GCWR_HELP to Size(Dim.Fill(32), about(18, 2)),
        UiTags.TRUCK_GCWR_WARNING to Size(Dim.Fill(32), about(36, 2)),
        UiTags.TRUCK_STANDALONE_PANEL to Size(Dim.Fill(32), about(480, 20)),
        UiTags.TRUCK_STANDALONE_PANEL_TITLE to Size(Dim.Fill(64), about(44)),
        UiTags.TRUCK_STANDALONE_PANEL_BODY to Size(Dim.Fill(64), about(60)),
        UiTags.SCAN_STANDALONE_TICKET to Size(Dim.Fill(64), fixed(52)),
        UiTags.TRUCK_STANDALONE_LABEL to Size(Dim.Any, about(16, 2)),
        UiTags.TRUCK_STANDALONE_INFO to square(48),
        UiTags.TRUCK_STANDALONE_INFO_TEXT to Size(Dim.Fill(64), about(74)),
        UiTags.TRUCK_STANDALONE_FIELD to Size(Dim.Fill(64), fixed(56)),
        UiTags.TRUCK_PIN_WEIGHT_LABEL to Size(Dim.Fill(64), about(40, 2)),
        UiTags.PIN_WEIGHT_PCT_SLIDER to Size(Dim.Fill(64), fixed(48)),
        UiTags.TRUCK_PIN_WEIGHT_CAPTION to Size(Dim.Fill(64), about(32, 2)),
        UiTags.TRUCK_NEXT_BUTTON to primaryButton,
    )

    private val trailerSizes: Map<String, Size> = mapOf(
        UiTags.TRAILER_BACK to topBar.getValue("back"),
        UiTags.TRAILER_TITLE to topBar.getValue("title"),
        UiTags.TRAILER_STEP_BAR to topBar.getValue("step"),
        UiTags.TRAILER_REFERENCE_HINT to Size(Dim.Any, about(20, 2)),
        UiTags.TRAILER_REFERENCE_IMAGE to Size(Dim.Fill(58), fixed(116)),
        UiTags.TRAILER_REFERENCE_FOCUS_BADGE to referenceFocusBadge,
        UiTags.SCAN_NOTICE to notice,
        UiTags.TRAILER_INSTRUCTIONS to Size(Dim.Fill(32), about(44)),
        UiTags.TRAILER_DESCRIPTION to field,
        UiTags.TRAILER_NAME_FIELD to field,
        UiTags.TRAILER_GVWR_FIELD to field,
        UiTags.TRAILER_GAWR_FIELD to field,
        UiTags.TRAILER_AXLE_COUNT_FIELD to field,
        UiTags.TRAILER_AXLE_COUNT_HELP to Size(Dim.Fill(32), about(18, 2)),
        UiTags.TRAILER_UVW_FIELD to field,
        UiTags.TRAILER_NEXT_BUTTON to primaryButton,
    )

    private val scaleSizes: Map<String, Size> = mapOf(
        UiTags.SCALE_BACK to topBar.getValue("back"),
        UiTags.SCALE_TITLE to topBar.getValue("title"),
        UiTags.SCALE_STEP_BAR to topBar.getValue("step"),
        UiTags.SCAN_NOTICE to notice,
        UiTags.SCALE_INSTRUCTIONS to Size(Dim.Fill(32), about(22, 2)),
        UiTags.SCALE_REFERENCE_IMAGE to Size(Dim.Fill(32), fixed(167)),
        UiTags.SCALE_LEGEND to Size(Dim.Fill(32), about(70)),
        UiTags.SCALE_LOCATION to field,
        UiTags.SCALE_STEER_FIELD to field,
        UiTags.SCALE_DRIVE_FIELD to field,
        UiTags.SCALE_TRAILER_FIELD to field,
        UiTags.SCALE_GROSS_FIELD to field,
        UiTags.SCALE_CHECK_BUTTON to primaryButton,
    )

    // --- Fixtures -----------------------------------------------------------------------------------------

    private val filledTruck = TruckTag(
        description = "Ford F-450", name = "Goose", gvwrLb = 14_000.0, frontGawrLb = 6_000.0, rearGawrLb = 9_750.0,
        gcwrLb = 28_000.0,
    )
    private val filledTrailer = TrailerTag(
        description = "Brinkley RV", name = "Addie", gvwrLb = 11_990.0, gawrPerAxleLb = 7_000.0, axleCount = 2, uvwLb = 8_400.0,
    )
    private val filledScale = ScaleTicket(
        locationName = "Truck stop, Exit 42", steerAxleLb = 4_900.0, driveAxleLb = 7_600.0, trailerAxleLb = 9_600.0,
        grossWeightLb = 22_100.0,
    )

    private fun noticeFor(module: EntryModule): ScanNotice =
        applyScan(module, JsonObject(emptyMap()), TruckTag(), TrailerTag(), ScaleTicket()).notice!!

    private fun truck(truck: TruckTag = TruckTag(), scanState: ScanUiState = ScanUiState.Idle, notice: ScanNotice? = null): @Composable () -> Unit = {
        TruckTagEntryScreen(
            truck = truck,
            onTruckChange = {},
            onContinue = {},
            scanState = scanState,
            creditBalance = 12,
            scanNotice = notice,
        )
    }

    private fun trailer(trailer: TrailerTag = TrailerTag(), notice: ScanNotice? = null): @Composable () -> Unit = {
        TrailerTagEntryScreen(trailer = trailer, onTrailerChange = {}, onContinue = {}, scanNotice = notice)
    }

    private fun scale(scale: ScaleTicket = ScaleTicket(), notice: ScanNotice? = null): @Composable () -> Unit = {
        ScaleTicketEntryScreen(scale = scale, onScaleChange = {}, onContinue = {}, scanNotice = notice)
    }
}
