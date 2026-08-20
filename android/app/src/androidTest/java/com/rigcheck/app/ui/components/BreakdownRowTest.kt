package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class BreakdownRowTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val noteText = "Steer (5,640) + drive (9,080) = 14,720 lb, which is 720 lb over this truck's 14,000 lb GVWR."

    @Test
    fun noteIsHiddenUntilTappedThenAppears() {
        val item = BreakdownItem(
            label = "Tow Vehicle Total (GVWR)", tone = Tone.WARNING,
            actual = 14720.0, limit = 14000.0, margin = -720.0, pct = 105, note = noteText,
        )
        composeRule.setContent { BreakdownRow(item) }

        // Not displayed until the row is tapped.
        composeRule.onNodeWithText(noteText).assertDoesNotExist()

        composeRule.onNodeWithText("Tow Vehicle Total (GVWR)").performClick()

        composeRule.onNodeWithText(noteText).assertIsDisplayed()
    }

    @Test
    fun rowWithoutANoteIsNotClickable() {
        val item = BreakdownItem(
            label = "Trailer Total (GVWR)", tone = Tone.SUCCESS,
            actual = 8000.0, limit = 10000.0, margin = 2000.0, pct = 80, note = null,
        )
        composeRule.setContent { BreakdownRow(item) }

        // clickable(enabled = item.note != null) means tapping a no-note
        // row is a no-op - confirms it doesn't crash and the row still
        // renders normally afterward.
        composeRule.onNodeWithText("Trailer Total (GVWR)").performClick()
        composeRule.onNodeWithText("Trailer Total (GVWR)").assertIsDisplayed()
    }
}
