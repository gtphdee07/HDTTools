package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
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
                creditBalance = 3,
                onSelectRecentRig = { selected = it },
                onStartNewRig = {},
                onOpenPaywall = {},
            )
        }

        composeRule.onNodeWithText("Goose + Addie").assertIsDisplayed()
        composeRule.onNodeWithText("Goose + Addie").performClick()

        assertEqualsRig(recentRig, selected)
    }

    @Test
    fun createButtonDisabledUntilNicknameIsEntered() {
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = emptyList(),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
            )
        }

        composeRule.onNodeWithText("Create").assertIsNotEnabled()
    }

    @Test
    fun typingNicknameThenCreateInvokesOnStartNewRig() {
        var startedWith: String? = null
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = emptyList(),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = { startedWith = it },
                onOpenPaywall = {},
            )
        }

        composeRule.onNodeWithText("Rig nickname").performTextInput("Big Blue")
        composeRule.onNodeWithText("Create").performClick()

        assert(startedWith == "Big Blue") { "onStartNewRig should have fired with the typed nickname" }
    }

    @Test
    fun creditBalanceChipTapInvokesOnOpenPaywall() {
        var opened = false
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = emptyList(),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = { opened = true },
            )
        }

        composeRule.onNodeWithText("3 scans").performClick()

        assert(opened) { "onOpenPaywall should have fired when the credit chip was tapped" }
    }

    // --- Delete (#169) --------------------------------------------------------------------------------

    private fun showPicker(
        selected: MutableList<RecentRig> = mutableListOf(),
        onDeleteRig: (suspend (RecentRig) -> Boolean)?,
    ) = composeRule.setContent {
        RigPickerScreen(
            recentRigs = listOf(recentRig),
            creditBalance = 3,
            onSelectRecentRig = { selected += it },
            onStartNewRig = {},
            onOpenPaywall = {},
            onDeleteRig = onDeleteRig,
        )
    }

    @Test
    fun withoutADeleteHandlerNoRigHasADeleteControl() {
        showPicker(onDeleteRig = null)

        composeRule.onNodeWithText("Goose + Addie").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Delete Goose + Addie").assertDoesNotExist()
    }

    @Test
    fun deleteAsksFirstAndCancelKeepsTheRigWithoutStartingACheck() {
        val deleted = mutableListOf<RecentRig>()
        val selected = mutableListOf<RecentRig>()
        showPicker(selected, onDeleteRig = { deleted += it; true })

        composeRule.onNodeWithContentDescription("Delete Goose + Addie").performClick()
        composeRule.onNodeWithText("Delete \"Goose + Addie\"?").assertIsDisplayed()
        composeRule.onNodeWithTag("delete_rig_cancel").performClick()

        composeRule.onNodeWithTag("delete_rig_dialog").assertDoesNotExist()
        composeRule.onNodeWithText("Goose + Addie").assertIsDisplayed()
        assert(deleted.isEmpty()) { "cancelling must not delete: $deleted" }
        assert(selected.isEmpty()) { "the delete control must not start a check: $selected" }
    }

    @Test
    fun confirmingDeletesThatRigAndClosesTheQuestion() {
        val deleted = mutableListOf<RecentRig>()
        showPicker(onDeleteRig = { deleted += it; true })

        composeRule.onNodeWithContentDescription("Delete Goose + Addie").performClick()
        composeRule.onNodeWithTag("delete_rig_confirm").performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) { deleted.isNotEmpty() }
        assert(deleted == listOf(recentRig)) { "expected $recentRig to be deleted, got $deleted" }
        composeRule.onNodeWithTag("delete_rig_dialog").assertDoesNotExist()
    }

    @Test
    fun aFailedDeleteSaysSoKeepsTheRigAndCanBeTriedAgain() {
        var attempts = 0
        showPicker(onDeleteRig = { ++attempts > 1 })

        composeRule.onNodeWithContentDescription("Delete Goose + Addie").performClick()
        composeRule.onNodeWithTag("delete_rig_confirm").performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithTag("delete_rig_error").fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithTag("delete_rig_error").assertIsDisplayed()
        composeRule.onNodeWithTag("delete_rig_dialog").assertIsDisplayed()
        composeRule.onNodeWithTag("delete_rig_confirm").assertIsEnabled()

        composeRule.onNodeWithTag("delete_rig_confirm").performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithTag("delete_rig_dialog").fetchSemanticsNodes().isEmpty()
        }
        assert(attempts == 2) { "expected one retry, got $attempts attempts" }
    }

    @Test
    fun signingOutWhileAskedClosesTheQuestionAndItDoesNotComeBackAtTheNextSignIn() {
        var handler by mutableStateOf<(suspend (RecentRig) -> Boolean)?>({ true })
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = listOf(recentRig),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
                onDeleteRig = handler,
            )
        }
        composeRule.onNodeWithContentDescription("Delete Goose + Addie").performClick()
        composeRule.onNodeWithTag("delete_rig_dialog").assertIsDisplayed()

        composeRule.runOnIdle { handler = null } // signed out
        composeRule.onNodeWithTag("delete_rig_dialog").assertDoesNotExist()
        composeRule.runOnIdle { handler = { true } } // signed in again

        composeRule.onNodeWithTag("delete_rig_dialog").assertDoesNotExist()
    }

    // Where a beta tester finds it (#182); what the link sends is FeedbackLinkTest's job.
    @Test
    fun showsTheSendFeedbackControl() {
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = listOf(recentRig),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
            )
        }

        composeRule.onNodeWithText("Send feedback").assertIsDisplayed()
    }

    private fun assertEqualsRig(expected: RecentRig, actual: RecentRig?) {
        assert(actual == expected) { "expected $expected but got $actual" }
    }
}
