package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.VerdictStatus
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// Fake parameters passed straight to the screen: what each past check shows, the empty list, and the notice a
// Free account with a full History gets. Where the entries come from is HistoryTest and HistoryNavigationTest.
@RunWith(AndroidJUnit4::class)
class HistoryScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun eachCheckShowsItsRigAndVerdictAndTheyAreNotLabelledAlike() {
        composeRule.setContent {
            HistoryScreen(
                entries = listOf(
                    HistoryEntry("1", "2026-10-22T12:00:00Z", "Goose + Addie", VerdictStatus.PASS),
                    HistoryEntry("2", "2026-10-21T12:00:00Z", "Big Blue", VerdictStatus.FAIL),
                    HistoryEntry("3", "2026-10-20T12:00:00Z", "Old Faithful", VerdictStatus.PARTIAL),
                ),
            )
        }

        composeRule.onAllNodesWithTag("history_entry").assertCountEquals(3)
        composeRule.onNodeWithText("Goose + Addie").assertIsDisplayed()
        composeRule.onNodeWithText("Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithText("Over Limit").assertIsDisplayed()
        composeRule.onNodeWithText("Partially Checked").assertIsDisplayed()
    }

    @Test
    fun noChecksSaysSoAndShowsNoLimitNotice() {
        composeRule.setContent { HistoryScreen(entries = emptyList()) }

        composeRule.onNodeWithTag("history_empty").assertIsDisplayed()
        composeRule.onAllNodesWithTag("history_limit_notice").assertCountEquals(0)
    }

    @Test
    fun theLimitNoticeOffersProAndUpgradeIsTappable() {
        var upgrade = false
        composeRule.setContent {
            HistoryScreen(
                entries = listOf(HistoryEntry("1", "2026-10-22T12:00:00Z", "Goose", VerdictStatus.PASS)),
                limitNotice = "The Free plan keeps your last 10 checks.",
                onUpgrade = { upgrade = true },
            )
        }

        composeRule.onNodeWithTag("history_limit_notice").assertIsDisplayed()
        composeRule.onNodeWithTag("history_upgrade").performClick()
        assert(upgrade) { "Upgrade to Pro should have fired onUpgrade" }
    }
}
