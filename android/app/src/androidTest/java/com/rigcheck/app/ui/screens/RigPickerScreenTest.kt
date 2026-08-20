package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RigPickerScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val recentRig = RecentRig(
        nickname = "Goose + Addie",
        truck = TruckTag(description = "F-450"),
        trailer = TrailerTag(description = "Brinkley G-4170"),
        lastUsedAt = "2026-08-19T12:00:00Z",
    )

    @Test
    fun recentRigCardTapInvokesOnSelectRecentRig() {
        var selected: RecentRig? = null
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = listOf(recentRig),
                onSelectRecentRig = { selected = it },
                onStartNewRig = {},
            )
        }

        composeRule.onNodeWithText("Goose + Addie").assertIsDisplayed()
        composeRule.onNodeWithText("Goose + Addie").performClick()

        assertEqualsRig(recentRig, selected)
    }

    @Test
    fun createButtonDisabledUntilNicknameIsEntered() {
        composeRule.setContent {
            RigPickerScreen(recentRigs = emptyList(), onSelectRecentRig = {}, onStartNewRig = {})
        }

        composeRule.onNodeWithText("Create").assertIsNotEnabled()
    }

    @Test
    fun typingNicknameThenCreateInvokesOnStartNewRig() {
        var startedWith: String? = null
        composeRule.setContent {
            RigPickerScreen(recentRigs = emptyList(), onSelectRecentRig = {}, onStartNewRig = { startedWith = it })
        }

        composeRule.onNodeWithText("Rig nickname (e.g. Big Blue)").performTextInput("Big Blue")
        composeRule.onNodeWithText("Create").performClick()

        assert(startedWith == "Big Blue") { "onStartNewRig should have fired with the typed nickname" }
    }

    private fun assertEqualsRig(expected: RecentRig, actual: RecentRig?) {
        assert(actual == expected) { "expected $expected but got $actual" }
    }
}
