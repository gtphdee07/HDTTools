package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.testsupport.onRigDeleteButton
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.testsupport.onRigCard
import com.rigcheck.app.testsupport.onNodeWithTagText

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

        composeRule.onRigCard("Goose + Addie").assertIsDisplayed()
        composeRule.onRigCard("Goose + Addie").performClick()

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

        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).assertIsNotEnabled()
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

        composeRule.onNodeWithTag(UiTags.PICKER_NEW_RIG_INPUT).performTextInput("Big Blue")
        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).performClick()

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

        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "3 scans").performClick()

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

        composeRule.onRigCard("Goose + Addie").assertIsDisplayed()
        composeRule.onRigDeleteButton("Goose + Addie").assertDoesNotExist()
    }

    @Test
    fun deleteAsksFirstAndCancelKeepsTheRigWithoutStartingACheck() {
        val deleted = mutableListOf<RecentRig>()
        val selected = mutableListOf<RecentRig>()
        showPicker(selected, onDeleteRig = { deleted += it; true })

        composeRule.onRigDeleteButton("Goose + Addie").performClick()
        composeRule.onNodeWithTagText(UiTags.DELETE_RIG_TITLE, "Delete \"Goose + Addie\"?").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CANCEL).performClick()

        composeRule.onNodeWithTag(UiTags.DELETE_RIG_DIALOG).assertDoesNotExist()
        composeRule.onRigCard("Goose + Addie").assertIsDisplayed()
        assert(deleted.isEmpty()) { "cancelling must not delete: $deleted" }
        assert(selected.isEmpty()) { "the delete control must not start a check: $selected" }
    }

    @Test
    fun confirmingDeletesThatRigAndClosesTheQuestion() {
        val deleted = mutableListOf<RecentRig>()
        showPicker(onDeleteRig = { deleted += it; true })

        composeRule.onRigDeleteButton("Goose + Addie").performClick()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CONFIRM).performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) { deleted.isNotEmpty() }
        assert(deleted == listOf(recentRig)) { "expected $recentRig to be deleted, got $deleted" }
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_DIALOG).assertDoesNotExist()
    }

    @Test
    fun aFailedDeleteSaysSoKeepsTheRigAndCanBeTriedAgain() {
        var attempts = 0
        showPicker(onDeleteRig = { ++attempts > 1 })

        composeRule.onRigDeleteButton("Goose + Addie").performClick()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CONFIRM).performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithTag(UiTags.DELETE_RIG_ERROR).fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_ERROR).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_DIALOG).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CONFIRM).assertIsEnabled()

        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CONFIRM).performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithTag(UiTags.DELETE_RIG_DIALOG).fetchSemanticsNodes().isEmpty()
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
        composeRule.onRigDeleteButton("Goose + Addie").performClick()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_DIALOG).assertIsDisplayed()

        composeRule.runOnIdle { handler = null } // signed out
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_DIALOG).assertDoesNotExist()
        composeRule.runOnIdle { handler = { true } } // signed in again

        composeRule.onNodeWithTag(UiTags.DELETE_RIG_DIALOG).assertDoesNotExist()
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

        composeRule.onNodeWithTag(UiTags.PICKER_FEEDBACK_LINK).assertIsDisplayed()
    }

    // --- Who is signed in (#192; the owner's phone feedback, items 3 and 4) ----------------------------

    private fun showAccount(
        signedOut: Boolean = false,
        accountLabel: String? = null,
        onSignIn: () -> Unit = {},
        onSignOut: () -> Unit = {},
    ) = composeRule.setContent {
        RigPickerScreen(
            recentRigs = listOf(recentRig),
            creditBalance = 3,
            onSelectRecentRig = {},
            onStartNewRig = {},
            onOpenPaywall = {},
            signedOut = signedOut,
            accountLabel = accountLabel,
            onSignIn = onSignIn,
            onSignOut = onSignOut,
        )
    }

    @Test
    fun aSignedInHeaderSaysWhoIsSignedInAndOpensTheSheetWithSignOutInTwoTaps() {
        val signedOutCalls = mutableListOf<String>()
        showAccount(accountLabel = "dana.rivera@example.com", onSignOut = { signedOutCalls += "out" })

        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_STATUS, "Signed in as").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_STATUS, "dana.rivera@example.com").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_AVATAR, "D").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_MENU).assertDoesNotExist()

        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).performClick() // tap one: the sheet
        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PICKER_SIGN_OUT_BUTTON) > 0 }
        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_MENU_EMAIL, "dana.rivera@example.com").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.PICKER_SIGN_OUT_BUTTON, "Sign out").performClick() // tap two: out

        assertEquals(listOf("out"), signedOutCalls)
        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PICKER_ACCOUNT_MENU) == 0 }
    }

    @Test
    fun cancelInTheAccountSheetClosesItAndSignsNobodyOut() {
        val signedOutCalls = mutableListOf<String>()
        showAccount(accountLabel = "dana.rivera@example.com", onSignOut = { signedOutCalls += "out" })

        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).performClick()
        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PICKER_ACCOUNT_MENU_CANCEL) > 0 }
        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_MENU_CANCEL, "Cancel").performClick()

        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PICKER_ACCOUNT_MENU) == 0 }
        assertEquals(emptyList<String>(), signedOutCalls)
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).assertIsDisplayed()
    }

    @Test
    fun aSignedOutHeaderSaysSoAndOffersSignInWithoutOpeningASheet() {
        var signIns = 0
        showAccount(signedOut = true, onSignIn = { signIns++ })

        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_STATUS, "Not signed in").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_STATUS, "Sign in").assertIsDisplayed()

        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).performClick()

        assertEquals(1, signIns)
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_MENU).assertDoesNotExist()
        // Signed out there is nothing to sign out of: no Sign out anywhere on the screen.
        composeRule.onNodeWithTag(UiTags.PICKER_SIGN_OUT_BUTTON).assertDoesNotExist()
    }

    @Test
    fun anAccountStillBeingLookedUpHasNoAccountRowYet() {
        showAccount(signedOut = false, accountLabel = null)

        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).assertIsDisplayed()
    }

    @Test
    fun signingOutWhileTheSheetIsOpenClosesIt() {
        var label by mutableStateOf<String?>("dana.rivera@example.com")
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = listOf(recentRig),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
                signedOut = label == null,
                accountLabel = label,
            )
        }
        composeRule.onNodeWithTag(UiTags.PICKER_ACCOUNT_STATUS).performClick()
        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PICKER_ACCOUNT_MENU) > 0 }

        composeRule.runOnIdle { label = null } // signed out some other way (a refused Scan's "Sign in again")

        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PICKER_ACCOUNT_MENU) == 0 }
        composeRule.onNodeWithTagText(UiTags.PICKER_ACCOUNT_STATUS, "Not signed in").assertIsDisplayed()
    }

    // --- No saved Rigs, and the new-Rig panel -------------------------------------------------------

    @Test
    fun noSavedRigsShowTheEmptyStateInsteadOfCards() {
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = emptyList(),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.PICKER_EMPTY_STATE, "No saved rigs yet").assertIsDisplayed()
        composeRule.onNodeWithTagText(
            UiTags.PICKER_EMPTY_STATE,
            "Finish a check and your rig shows up here. Manual entry is free.",
        ).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PICKER_RIG_CARD).assertDoesNotExist()
    }

    @Test
    fun aSavedRigHidesTheEmptyState() {
        showPicker(onDeleteRig = null)

        composeRule.onNodeWithTag(UiTags.PICKER_EMPTY_STATE).assertDoesNotExist()
    }

    @Test
    fun historyButtonOpensTheHistory() {
        var opened = 0
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = emptyList(),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
                onOpenHistory = { opened++ },
            )
        }

        composeRule.onNodeWithTagText(UiTags.OPEN_HISTORY, "History").performClick()

        assertEquals(1, opened)
    }

    @Test
    fun aNicknameOfOnlySpacesDoesNotEnableCreateAndOneWithTextIsTrimmed() {
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

        composeRule.onNodeWithTag(UiTags.PICKER_NEW_RIG_INPUT).performTextInput("   ")
        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).assertIsNotEnabled()
        composeRule.onNodeWithTag(UiTags.PICKER_NEW_RIG_INPUT).performTextInput("  Big Blue ")
        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).assertIsEnabled().performClick()

        assertEquals("Big Blue", startedWith)
    }

    private fun assertEqualsRig(expected: RecentRig, actual: RecentRig?) {
        assert(actual == expected) { "expected $expected but got $actual" }
    }
}
