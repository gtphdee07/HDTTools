package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.verdictFor
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ResultsScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun item(label: String, tone: Tone, pct: Int, note: String? = null) = BreakdownItem(
        label = label, tone = tone, actual = 1.0, limit = 1.0, margin = 0.0, pct = pct, note = note,
    )

    @Test
    fun allPassingRendersSafeToTowVerdict() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent { ResultsScreen(breakdown = breakdown, verdict = verdictFor(breakdown)) }

        composeRule.onNodeWithText("Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithText("Tow Vehicle Total (GVWR)").assertIsDisplayed()
        composeRule.onNodeWithText("85%").assertIsDisplayed()
    }

    @Test
    fun anyFailureRendersNotSafeToTowVerdict() {
        val breakdown = listOf(
            item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85),
            item("Combined Rig Weight", Tone.WARNING, 108),
        )
        composeRule.setContent { ResultsScreen(breakdown = breakdown, verdict = verdictFor(breakdown)) }

        composeRule.onNodeWithText("Not Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithText("Combined Rig Weight").assertIsDisplayed()
        composeRule.onNodeWithText("108%").assertIsDisplayed()
    }
}
