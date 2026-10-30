package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.getBoundsInRoot
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.height
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Surface
import com.rigcheck.app.ui.theme.SurfaceSunken
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Breakdown row": pass, fail and not checked; a row with a note expands, one without has no chevron.
@RunWith(AndroidJUnit4::class)
class RigCheckBreakdownRowTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun item(tone: Tone, pct: Int, note: String? = "A note about this row") = BreakdownItem(
        label = "Rear axle",
        tone = tone,
        actual = 5200.0,
        limit = 6000.0,
        margin = 800.0,
        pct = pct,
        note = note,
    )

    private fun assertRowReadable(tone: Tone) {
        val look = rigCheckRowLook(tone)
        assertAa("label", Ink, Surface)
        assertAa("values line", InkMuted, Surface)
        assertAa("percentage", look.percent, Surface)
        val badge = rigCheckBadgeColors(look.badgeKind)
        assertAa("badge", badge.content, badge.container)
        // The bar and the icon are graphics: 3:1 against what is behind them.
        assertAa("bar fill on track", rigCheckProgressFill(look.progress), ProgressTrack, largeText = true)
        assertAa("status icon", rigCheckProgressFill(look.progress), Surface, largeText = true)
        assertAa("note", Ink, SurfaceSunken)
    }

    @Test
    fun passingRowSaysWithinLimitWithItsValuesAndPercentage() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.SUCCESS, 87)) }
        composeRule.onNodeWithText("Rear axle").assertIsDisplayed()
        composeRule.onNodeWithText("Within limit").assertIsDisplayed()
        composeRule.onNodeWithText("5,200 lb of 6,000 lb").assertIsDisplayed()
        composeRule.onNodeWithText("87%").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        assertRowReadable(Tone.SUCCESS)
    }

    @Test
    fun failingRowSaysOverLimitInWordsAndInDangerText() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.WARNING, 112)) }
        composeRule.onNodeWithText("Over limit").assertIsDisplayed()
        composeRule.onNodeWithText("112%").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        assertRowReadable(Tone.WARNING)
        assertEquals(DangerText, rigCheckRowLook(Tone.WARNING).percent)
    }

    @Test
    fun notCheckedRowSaysNotChecked() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.INSUFFICIENT, 0)) }
        composeRule.onNodeWithText("Not checked").assertIsDisplayed()
        composeRule.onNodeWithText("0%").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        assertRowReadable(Tone.INSUFFICIENT)
    }

    @Test
    fun theChevronOpensAndClosesTheNote() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.SUCCESS, 87)) }
        assertEquals(0, composeRule.nodesWithTag(UiTags.RESULTS_ROW_NOTE))
        composeRule.onNodeWithContentDescription("Show note").performClick()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_NOTE, "A note about this row").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Hide note").performClick()
        composeRule.waitUntil(2_000) { composeRule.nodesWithTag(UiTags.RESULTS_ROW_NOTE) == 0 }
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun aRowThatStartsExpandedShowsItsNote() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.WARNING, 112), startExpanded = true) }
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_NOTE, "A note about this row").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Hide note").assertIsDisplayed()
    }

    @Test
    fun aRowWithoutANoteHasNoChevron() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.SUCCESS, 87, note = null)) }
        composeRule.onNodeWithContentDescription("Show note").assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.RESULTS_ROW).assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    // The rest of the row opens the note too (what the old row did: a tap anywhere on it), so a thumb that misses the
    // chevron still gets the note. The chevron stays the one control a screen reader is given.
    @Test
    fun tappingTheRowItselfOpensAndClosesTheNote() {
        val note = "Steer (5,640) + drive (9,080) = 14,720 lb, which is 720 lb over this truck's 14,000 lb GVWR."
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.WARNING, 105, note = note)) }
        assertEquals(0, composeRule.nodesWithTag(UiTags.RESULTS_ROW_NOTE))

        composeRule.onNodeWithTag(UiTags.RESULTS_ROW).performClick()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_NOTE, note).assertIsDisplayed()

        composeRule.onNodeWithTag(UiTags.RESULTS_ROW).performClick()
        composeRule.waitUntil(2_000) { composeRule.nodesWithTag(UiTags.RESULTS_ROW_NOTE) == 0 }
    }

    @Test
    fun tappingARowWithoutANoteChangesNothing() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.SUCCESS, 80, note = null)) }

        composeRule.onNodeWithTag(UiTags.RESULTS_ROW).performClick()

        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Rear axle").assertIsDisplayed()
        assertEquals(0, composeRule.nodesWithTag(UiTags.RESULTS_ROW_NOTE))
    }

    // components.md: "A fill over 100% is clamped at the bar's end"; the percentage still says what it is.
    @Test
    fun aRowOverItsLimitStillShowsTheTruePercentage() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.WARNING, 140)) }
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_PCT, "140%").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_BADGE, "Over limit").assertIsDisplayed()
    }

    // The status badge and the chevron are the map's `results.row_badge` and `results.row_chevron`: tagged, and the
    // chevron is a 48 x 48 dp target (the map) that the row's height does not grow for.
    @Test
    fun theBadgeSaysTheStatusInWordsAndTheChevronIsA48dpTarget() {
        composeRule.setRigCheckContent { RigCheckBreakdownRow(item(Tone.SUCCESS, 87)) }
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_BADGE, "Within limit").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.RESULTS_ROW_CHEVRON, useUnmergedTree = true)
            .assertWidthIsEqualTo(48.dp).assertHeightIsEqualTo(48.dp)
        val rowHeight = composeRule.onNodeWithTag(UiTags.RESULTS_ROW).getBoundsInRoot().height
        assertEquals(
            "a chevron must not make the row taller than the 104 dp the design gives it",
            104f, rowHeight.value, 4f,
        )
    }
}
