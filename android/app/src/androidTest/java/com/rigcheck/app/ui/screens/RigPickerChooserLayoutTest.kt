package com.rigcheck.app.ui.screens

import android.content.ActivityNotFoundException
import android.content.ContextWrapper
import android.content.Intent
import android.os.Bundle
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.layoutcapture.CaptureScope
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
import com.rigcheck.app.testsupport.shown
import com.rigcheck.app.testsupport.sizes
import com.rigcheck.app.testsupport.square
import com.rigcheck.app.testsupport.touchTargets
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.navigation.EntryModule
import java.time.Instant
import kotlin.math.abs
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #192: the Rig picker, the Chooser (all three documents) and the photo-source dialog, checked against the designer's
// map (docs/android-redesign/design-return/ui-redesign-map.json, with the follow-up map for the Rig card's bin and the
// Send feedback link). For every element of those screens, in the states below:
//   - it is displayed (found by its UiTags tag and at least partly on show);
//   - the reading order is the map's `new_order`, compared by the elements' top positions (see ORDER below);
//   - its measured width and height are the map's `new_width` and `new_height`. TOLERANCE: 1.5 dp where the map gives
//     a fixed size, 4 dp on a height the map gives with a "~" and on a width that is a text's, up to 10 dp for the
//     widest text. The frames were drawn in a browser with its own font metrics, so a text's width differs a little
//     from the bundled font's; a layout that is wrong (a wrong padding, the wrong component) is many dp out;
//   - "fill" is the full width of the column it is in (the screen less its margins), "wrap" has no width to check;
//   - every clickable element is at least 48 x 48 dp.
// And on a 360 x 640 dp phone, at font scale 2.0, and with the keyboard open on the Rig picker, the screen's primary
// action can be scrolled to and is then wholly on show, with nothing wider than the screen.
//
// It changes the display's size, density and font scale for the run and puts them back (as LayoutCaptureTest does),
// and no state sends a Scan or calls the network.
@RunWith(AndroidJUnit4::class)
class RigPickerChooserLayoutTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())

    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-192-screenshots")

    private fun putOnTheDisplay(frame: Frame) {
        runner.frameName = frame.name
        display.apply(frame)
    }

    @After
    fun putTheDisplayBack() {
        display.reset()
    }

    @Test
    fun theDesignFrame412x892MatchesTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()

        problems += inState("rig_picker: in", pickerContent(rigs = oneRig, balance = 12)) { p ->
            val b = p.bounds()
            shown(b, pickerElements) + sizes(b, p.widthDp, pickerSizes - UiTags.PICKER_EMPTY_STATE) + rigCardSpansTheColumn(b, p.widthDp) +
                order(b, pickerOrder, pickerStacks) + touchTargets(p)
        }
        problems += inState("rig_picker: signed_out_empty", pickerContent(rigs = emptyList(), balance = null, signedOut = true)) { p ->
            val b = p.bounds()
            shown(b, pickerEmptyElements) + absent(b, listOf(UiTags.PICKER_RIG_CARD, UiTags.PICKER_RIG_DELETE)) +
                sizes(b, p.widthDp, pickerSizes.filterKeys { it in pickerEmptyElements }) +
                order(b, pickerEmptyOrder) + touchTargets(p)
        }
        problems += inState(
            "rig_picker: account_menu", pickerContent(rigs = oneRig, balance = 12),
            setUp = {
                tap(UiTags.PICKER_ACCOUNT_STATUS)
                rule.waitUntil(timeoutMillis = 5_000) { rule.onAllNodesWithTag(UiTags.PICKER_ACCOUNT_MENU).fetchSemanticsNodes().isNotEmpty() }
            },
        ) { p ->
            val b = p.bounds()
            shown(b, menuElements) + sizes(b, p.widthDp, menuSizes) + order(b, menuOrder) + touchTargets(p)
        }
        problems += inState(
            "rig_picker: new_rig_typing", pickerContent(rigs = oneRig, balance = 12),
            setUp = {
                type(UiTags.PICKER_NEW_RIG_INPUT, "Weekend rig")
                awaitKeyboardShown()
            },
        ) { p ->
            // rig_picker__new_rig_typing: the bar stays, the panel scrolls into view above the keyboard, Create is on.
            shown(p.bounds(), listOf(UiTags.PICKER_LOGO, UiTags.PICKER_ACCOUNT_STATUS)) +
                reach(p, UiTags.PICKER_NEW_RIG_LABEL, UiTags.PICKER_NEW_RIG_INPUT, UiTags.PICKER_CREATE_BUTTON)
        }
        problems += inState(
            "rig_picker: feedback_no_mail", withNoMailApp(pickerContent(rigs = oneRig, balance = 12)),
            setUp = { tap(UiTags.PICKER_FEEDBACK_LINK) },
        ) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.PICKER_FEEDBACK_LINK, UiTags.SEND_FEEDBACK_NO_MAIL_APP)) +
                order(b, listOf(listOf(UiTags.PICKER_FEEDBACK_LINK), listOf(UiTags.SEND_FEEDBACK_NO_MAIL_APP))) +
                sizes(b, p.widthDp, mapOf(UiTags.SEND_FEEDBACK_NO_MAIL_APP to Size(Dim.Any, about(36, 8))))
        }
        for (module in EntryModule.entries) {
            problems += inState("chooser: ${module.name.lowercase()}", chooserContent(module = module, balance = 12)) { p ->
                val b = p.bounds()
                shown(b, chooserElements) + absent(b, listOf(UiTags.CHOOSER_LOADING_OVERLAY)) +
                    sizes(b, p.widthDp, chooserSizes) + order(b, chooserOrder) + touchTargets(p)
            }
        }
        problems += inState("chooser: balance_loading", chooserContent(balance = null)) { p ->
            val b = p.bounds()
            shown(b, chooserElements) + touchTargets(p)
        }
        problems += inState("chooser: scan_in_flight", chooserContent(scanState = ScanUiState.Loading)) { p ->
            val b = p.bounds()
            val overlay = b[UiTags.CHOOSER_LOADING_OVERLAY]
            val covers = if (overlay == null) {
                listOf("the overlay is not on the screen")
            } else {
                // Over the whole screen, the top bar (Back, the chip) included.
                listOfNotNull(
                    b[UiTags.CHOOSER_BACK]?.takeIf { overlay.y > it.y + 0.5 }?.let { "the overlay starts below Back" },
                    b[UiTags.CHOOSER_SCAN_CARD]?.takeIf { overlay.y + overlay.height < it.y + it.height - 0.5 }
                        ?.let { "the overlay ends above the Scan card's bottom" },
                    overlay.takeIf { abs(it.width - p.widthDp) > 1.5 }?.let { "the overlay is ${it.width} dp wide, not ${p.widthDp}" },
                )
            }
            shown(b, listOf(UiTags.CHOOSER_LOADING_OVERLAY, UiTags.CHOOSER_LOADING_TEXT)) + covers +
                sizes(b, p.widthDp, mapOf(UiTags.CHOOSER_LOADING_TEXT to Size(about(92, 6), about(24, 2))))
        }
        problems += inState(
            "photo_source_dialog: default", chooserContent(),
            setUp = { tap(UiTags.CHOOSER_SCAN_CARD) },
        ) { p ->
            val b = p.bounds()
            shown(b, dialogElements) + sizes(b, p.widthDp, dialogSizes) + order(b, dialogOrder.map { listOf(it) }) +
                touchTargets(p)
        }

        assertTrue("the design frame differs from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    @Test
    fun aSmallPhone360x640ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640))

    @Test
    fun aSmallPhone360x640AtFontScale2ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640, fontScale = 2f))

    // The primary action of each screen: the Rig picker's Create (and its cards), the Chooser's two ways, the dialog's
    // two buttons. A scroll puts it wholly on show, nothing is wider than the screen, and the 48 dp rule holds.
    private fun reachEverything(frame: Frame) {
        putOnTheDisplay(frame)
        val problems = mutableListOf<String>()

        problems += inState("rig_picker: in", pickerContent(rigs = sixRigs, balance = 12)) { p ->
            reach(p, UiTags.PICKER_CREATE_BUTTON, UiTags.PICKER_RIG_CARD, UiTags.PICKER_FEEDBACK_LINK, UiTags.OPEN_HISTORY) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState("rig_picker: signed_out_empty", pickerContent(rigs = emptyList(), balance = null, signedOut = true)) { p ->
            reach(p, UiTags.PICKER_CREATE_BUTTON, UiTags.PICKER_EMPTY_STATE, UiTags.PICKER_ACCOUNT_STATUS) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState(
            "rig_picker: new_rig_typing (keyboard open)", pickerContent(rigs = oneRig, balance = 12),
            setUp = {
                tap(UiTags.PICKER_NEW_RIG_INPUT)
                awaitKeyboardShown()
            },
        ) { p ->
            reach(p, UiTags.PICKER_NEW_RIG_INPUT, UiTags.PICKER_CREATE_BUTTON) + noneWiderThanTheScreen(p)
        }
        problems += inState(
            "rig_picker: account_menu", pickerContent(rigs = oneRig, balance = 12),
            setUp = {
                tap(UiTags.PICKER_ACCOUNT_STATUS)
                rule.waitUntil(timeoutMillis = 5_000) { rule.onAllNodesWithTag(UiTags.PICKER_ACCOUNT_MENU).fetchSemanticsNodes().isNotEmpty() }
            },
        ) { p ->
            reach(p, UiTags.PICKER_SIGN_OUT_BUTTON, UiTags.PICKER_ACCOUNT_MENU_CANCEL) + noneWiderThanTheScreen(p)
        }
        for (module in EntryModule.entries) {
            problems += inState("chooser: ${module.name.lowercase()}", chooserContent(module = module, balance = 12)) { p ->
                reach(p, UiTags.CHOOSER_SCAN_CARD, UiTags.CHOOSER_MANUAL_CARD, UiTags.CHOOSER_FOOTER_NOTE, UiTags.CHOOSER_BACK) +
                    noneWiderThanTheScreen(p) + touchTargets(p)
            }
        }
        problems += inState(
            "photo_source_dialog: default", chooserContent(),
            setUp = { tap(UiTags.CHOOSER_SCAN_CARD) },
        ) { p ->
            reach(p, UiTags.PHOTO_DIALOG_CAMERA, UiTags.PHOTO_DIALOG_GALLERY) + noneWiderThanTheScreen(p) + touchTargets(p)
        }

        assertTrue("${frame.name}:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Putting a state on the screen (testsupport/LayoutChecks.kt) -----------------------------------

    private fun inState(
        name: String,
        content: @Composable () -> Unit,
        setUp: CaptureScope.() -> Unit = {},
        check: (Probe) -> List<String>,
    ): List<String> = runner.inState(name, content, setUp, check)

    // The Rig card is tagged on its body (the part that starts a check); the bin beside it is the rest of the card.
    // Together, with the bin's 4 dp margin, they fill the column.
    private fun rigCardSpansTheColumn(b: Map<String, TaggedBounds>, screenWidth: Double): List<String> {
        val card = b[UiTags.PICKER_RIG_CARD] ?: return emptyList()
        val bin = b[UiTags.PICKER_RIG_DELETE] ?: return listOf("the Rig card has no delete bin")
        val spans = bin.x + bin.width + 4
        return listOfNotNull(
            // card.x is where the body's content starts, inside the body's 16 dp of start padding.
            "the Rig card starts at ${card.x - 16} dp, not the 16 dp margin".takeIf { abs(card.x - 16 - 16) > 1.5 },
            "the Rig card and its bin end at $spans dp, not ${screenWidth - 16}".takeIf { abs(spans - (screenWidth - 16)) > 1.5 },
            "the Rig card is ${card.height} dp high, the map says ~86".takeIf { abs(card.height - 86) > 4 },
        )
    }


    // --- What the map says ------------------------------------------------------------------------------

    // rig_picker__in: the elements in the frame, in its numbering.
    private val pickerElements = listOf(
        UiTags.PICKER_LOGO, UiTags.PICKER_APP_TITLE, UiTags.PICKER_TAGLINE, UiTags.PICKER_CREDIT_CHIP,
        UiTags.PICKER_ACCOUNT_STATUS, UiTags.PICKER_ACCOUNT_AVATAR, UiTags.PICKER_HEADING, UiTags.PICKER_SUBHEADING,
        UiTags.OPEN_HISTORY, UiTags.PICKER_RIG_CARD, UiTags.PICKER_RIG_AVATAR, UiTags.PICKER_RIG_NICKNAME,
        UiTags.PICKER_RIG_SUBTITLE, UiTags.PICKER_RIG_LAST_CHECKED, UiTags.PICKER_RIG_DELETE,
        UiTags.PICKER_NEW_RIG_LABEL, UiTags.PICKER_NEW_RIG_INPUT, UiTags.PICKER_CREATE_BUTTON,
        UiTags.PICKER_FEEDBACK_LINK,
    )

    // rig_picker__signed_out_empty: the empty state in place of the cards.
    private val pickerEmptyElements = pickerElements.filter {
        it !in setOf(
            UiTags.PICKER_RIG_CARD, UiTags.PICKER_RIG_AVATAR, UiTags.PICKER_RIG_NICKNAME, UiTags.PICKER_RIG_SUBTITLE,
            UiTags.PICKER_RIG_LAST_CHECKED, UiTags.PICKER_RIG_DELETE,
        )
    } + UiTags.PICKER_EMPTY_STATE

    private val pickerSizes: Map<String, Size> = mapOf(
        UiTags.PICKER_LOGO to square(56),
        UiTags.PICKER_APP_TITLE to Size(Dim.Any, about(30)),
        UiTags.PICKER_TAGLINE to Size(about(175, 8), about(16, 2)),
        UiTags.PICKER_CREDIT_CHIP to Size(about(125, 6), fixed(48)),
        UiTags.PICKER_ACCOUNT_STATUS to Size(Dim.Fill(32), fixed(48)),
        UiTags.PICKER_ACCOUNT_AVATAR to square(32),
        UiTags.PICKER_HEADING to Size(Dim.Any, about(34)),
        UiTags.PICKER_SUBHEADING to Size(Dim.Any, about(44)),
        UiTags.OPEN_HISTORY to Size(Dim.Any, fixed(48)),
        UiTags.PICKER_RIG_AVATAR to square(52),
        UiTags.PICKER_RIG_NICKNAME to Size(Dim.Any, about(22)),
        UiTags.PICKER_RIG_SUBTITLE to Size(Dim.Any, about(18)),
        UiTags.PICKER_RIG_LAST_CHECKED to Size(Dim.Any, about(16)),
        UiTags.PICKER_RIG_DELETE to square(48),
        UiTags.PICKER_NEW_RIG_LABEL to Size(Dim.Fill(64), about(22)),
        UiTags.PICKER_NEW_RIG_INPUT to Size(Dim.Fill(64), fixed(56)),
        UiTags.PICKER_CREATE_BUTTON to Size(Dim.Fill(64), fixed(56)),
        UiTags.PICKER_FEEDBACK_LINK to Size(Dim.Any, fixed(48)),
        UiTags.PICKER_EMPTY_STATE to Size(Dim.Fill(32), about(108, 8)),
    )

    // Bands of rig_picker__in (see ORDER): the header row, the account row, the heading block, the card, then one each.
    private val pickerOrder: List<List<String>> = listOf(
        listOf(UiTags.PICKER_LOGO, UiTags.PICKER_APP_TITLE, UiTags.PICKER_TAGLINE, UiTags.PICKER_CREDIT_CHIP),
        listOf(UiTags.PICKER_ACCOUNT_STATUS, UiTags.PICKER_ACCOUNT_AVATAR),
        listOf(UiTags.PICKER_HEADING, UiTags.PICKER_SUBHEADING, UiTags.OPEN_HISTORY),
        listOf(
            UiTags.PICKER_RIG_CARD, UiTags.PICKER_RIG_AVATAR, UiTags.PICKER_RIG_NICKNAME, UiTags.PICKER_RIG_SUBTITLE,
            UiTags.PICKER_RIG_LAST_CHECKED, UiTags.PICKER_RIG_DELETE,
        ),
        listOf(UiTags.PICKER_NEW_RIG_LABEL),
        listOf(UiTags.PICKER_NEW_RIG_INPUT),
        listOf(UiTags.PICKER_CREATE_BUTTON),
        listOf(UiTags.PICKER_FEEDBACK_LINK),
    )

    private val pickerStacks: List<List<String>> = listOf(
        listOf(UiTags.PICKER_HEADING, UiTags.PICKER_SUBHEADING),
        listOf(UiTags.PICKER_RIG_NICKNAME, UiTags.PICKER_RIG_SUBTITLE, UiTags.PICKER_RIG_LAST_CHECKED),
        listOf(UiTags.PICKER_APP_TITLE, UiTags.PICKER_TAGLINE),
    )

    private val pickerEmptyOrder: List<List<String>> = pickerOrder.take(3) + listOf(listOf(UiTags.PICKER_EMPTY_STATE)) + pickerOrder.drop(4)

    private val menuElements = listOf(
        UiTags.PICKER_ACCOUNT_MENU, UiTags.PICKER_ACCOUNT_MENU_EMAIL, UiTags.PICKER_SIGN_OUT_BUTTON,
        UiTags.PICKER_ACCOUNT_MENU_CANCEL,
    )

    private val menuSizes: Map<String, Size> = mapOf(
        UiTags.PICKER_ACCOUNT_MENU to Size(Dim.Fill(0), about(288, 2)),
        UiTags.PICKER_ACCOUNT_MENU_EMAIL to Size(about(197, 10), about(22, 2)),
        UiTags.PICKER_SIGN_OUT_BUTTON to Size(Dim.Fill(32), fixed(56)),
        UiTags.PICKER_ACCOUNT_MENU_CANCEL to Size(Dim.Fill(32), fixed(56)),
    )

    private val menuOrder: List<List<String>> = listOf(
        listOf(UiTags.PICKER_ACCOUNT_MENU), listOf(UiTags.PICKER_ACCOUNT_MENU_EMAIL),
        listOf(UiTags.PICKER_SIGN_OUT_BUTTON), listOf(UiTags.PICKER_ACCOUNT_MENU_CANCEL),
    )

    // chooser__truck (the same frame for the other two documents).
    private val chooserElements = listOf(
        UiTags.CHOOSER_BACK, UiTags.CHOOSER_TITLE, UiTags.CHOOSER_CREDIT_CHIP, UiTags.CHOOSER_STEP_BAR,
        UiTags.CHOOSER_PROMPT, UiTags.CHOOSER_SCAN_CARD, UiTags.CHOOSER_SCAN_BADGE, UiTags.CHOOSER_MANUAL_CARD,
        UiTags.CHOOSER_MANUAL_BADGE, UiTags.CHOOSER_FOOTER_NOTE,
    )

    private val chooserSizes: Map<String, Size> = mapOf(
        UiTags.CHOOSER_BACK to square(48),
        UiTags.CHOOSER_TITLE to Size(Dim.Any, about(30)),
        UiTags.CHOOSER_CREDIT_CHIP to Size(about(125, 6), fixed(48)),
        // 2.5 dp: three line heights of text, which the font's own metrics move by a pixel or two.
        UiTags.CHOOSER_STEP_BAR to Size(Dim.Fill(32), Dim.Exact(76.0, 2.5)),
        UiTags.CHOOSER_PROMPT to Size(Dim.Fill(32), about(56)),
        UiTags.CHOOSER_SCAN_CARD to Size(Dim.Fill(32), about(148)),
        UiTags.CHOOSER_SCAN_BADGE to Size(about(66, 4), fixed(22)),
        UiTags.CHOOSER_MANUAL_CARD to Size(Dim.Fill(32), about(148)),
        UiTags.CHOOSER_MANUAL_BADGE to Size(about(48, 4), fixed(22)),
        UiTags.CHOOSER_FOOTER_NOTE to Size(Dim.Any, about(40)),
    )

    private val chooserOrder: List<List<String>> = listOf(
        listOf(UiTags.CHOOSER_BACK, UiTags.CHOOSER_TITLE, UiTags.CHOOSER_CREDIT_CHIP),
        listOf(UiTags.CHOOSER_STEP_BAR),
        listOf(UiTags.CHOOSER_PROMPT),
        listOf(UiTags.CHOOSER_SCAN_CARD, UiTags.CHOOSER_SCAN_BADGE),
        listOf(UiTags.CHOOSER_MANUAL_CARD, UiTags.CHOOSER_MANUAL_BADGE),
        listOf(UiTags.CHOOSER_FOOTER_NOTE),
    )

    private val dialogElements = listOf(
        UiTags.PHOTO_DIALOG_TITLE, UiTags.PHOTO_DIALOG_BODY, UiTags.PHOTO_DIALOG_CAMERA, UiTags.PHOTO_DIALOG_GALLERY,
    )

    private val dialogSizes: Map<String, Size> = mapOf(
        UiTags.PHOTO_DIALOG_TITLE to Size(Dim.Any, about(28, 2)),
        UiTags.PHOTO_DIALOG_BODY to Size(Dim.Any, about(48, 4)),
        UiTags.PHOTO_DIALOG_CAMERA to Size(Dim.Any, fixed(52)),
        UiTags.PHOTO_DIALOG_GALLERY to Size(Dim.Any, fixed(52)),
    )

    // photo_source_dialog__default: Take Photo (3) above Choose from Gallery (4).
    private val dialogOrder: List<String> = dialogElements

    // --- Fixtures -----------------------------------------------------------------------------------------

    private fun rig(nickname: String, secondsAgo: Long = 3_600) = RecentRig(
        nickname = nickname,
        truck = TruckTag(description = "Ford F-450"),
        trailer = TrailerTag(description = "Brinkley RV"),
        lastUsedAt = Instant.now().minusSeconds(secondsAgo).toString(),
    )

    private val oneRig = listOf(rig("Goose and Addie"))
    private val sixRigs = (1..6).map { rig("Rig number $it", secondsAgo = it * 86_400L) }

    private fun pickerContent(
        rigs: List<RecentRig>,
        balance: Int?,
        signedOut: Boolean = false,
    ): @Composable () -> Unit = {
        RigPickerScreen(
            recentRigs = rigs,
            creditBalance = balance,
            onSelectRecentRig = {},
            onStartNewRig = {},
            onOpenPaywall = {},
            onOpenHistory = {},
            signedOut = signedOut,
            accountLabel = if (signedOut) null else "dana.rivera@example.com",
            onDeleteRig = if (signedOut) null else ({ true }),
        )
    }

    private fun chooserContent(
        module: EntryModule = EntryModule.TRUCK,
        balance: Int? = 5,
        scanState: ScanUiState = ScanUiState.Idle,
    ): @Composable () -> Unit = {
        ChooserScreen(
            module = module,
            creditBalance = balance,
            scanState = scanState,
            onChooseManual = {},
            onPhotoScanned = {},
            onNeedCredits = {},
            onOpenPaywall = {},
            onDismissScanError = {},
            onScanErrorNextStep = {},
        )
    }

    // The screen on a phone with no email app: "Send feedback" starts its mail intent with the screen's Context, which
    // here throws ActivityNotFoundException.
    private fun withNoMailApp(content: @Composable () -> Unit): @Composable () -> Unit = {
        val real = LocalContext.current
        val noMailApp = remember(real) {
            object : ContextWrapper(real) {
                override fun startActivity(intent: Intent) = throw ActivityNotFoundException("no mail app")
                override fun startActivity(intent: Intent, options: Bundle?) = throw ActivityNotFoundException("no mail app")
            }
        }
        CompositionLocalProvider(LocalContext provides noMailApp) { content() }
    }

}
