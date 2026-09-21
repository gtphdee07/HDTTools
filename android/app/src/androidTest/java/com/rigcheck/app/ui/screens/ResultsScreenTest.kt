package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
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

    private fun item(label: String, tone: Tone, pct: Int, note: String? = null, estimated: Boolean = false) =
        BreakdownItem(
            label = label, tone = tone, actual = 1.0, limit = 1.0, margin = 0.0, pct = pct, note = note,
            estimated = estimated,
        )

    @Test
    fun allPassingRendersSafeToTowVerdict() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

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
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithText("Not Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithText("Combined Rig Weight").assertIsDisplayed()
        composeRule.onNodeWithText("108%").assertIsDisplayed()
    }

    @Test
    fun allInsufficientRendersNotEnoughInformationVerdict() {
        val breakdown = listOf(item("Front Axle (Steer)", Tone.INSUFFICIENT, 0))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithText("Not Enough Information").assertIsDisplayed()
        composeRule.onNodeWithText("Front Axle (Steer)").assertIsDisplayed()
    }

    @Test
    fun mixedInsufficientAndPassingRendersPartiallyCheckedVerdict() {
        val breakdown = listOf(
            item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85),
            item("Trailer Total (GVWR)", Tone.INSUFFICIENT, 0),
        )
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithText("Partially Checked").assertIsDisplayed()
    }

    @Test
    fun estimatedFiguresNoticeShowsWhenAnyRowIsEstimated() {
        val breakdown = listOf(
            item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85, estimated = true),
        )
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithText("⚠️ Estimated Figures — Confirm Before You Buy").assertIsDisplayed()
    }

    @Test
    fun estimatedFiguresNoticeHiddenWhenNoRowIsEstimated() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithText("⚠️ Estimated Figures — Confirm Before You Buy").assertDoesNotExist()
    }

    @Test
    fun rigNicknameIsDisplayed() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithText("Goose + Addie").assertIsDisplayed()
    }

    @Test
    fun startAnotherCheckButtonInvokesOnStartAnother() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        var started = false
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = { started = true },
            )
        }

        composeRule.onNodeWithText("Start another check").performClick()

        assert(started) { "onStartAnother should have fired when the button was tapped" }
    }
}
