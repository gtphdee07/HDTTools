package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.testsupport.onHistoryEntry
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.ui.UiTags
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

        composeRule.onAllNodesWithTag(UiTags.HISTORY_ENTRY).assertCountEquals(3)
        composeRule.onHistoryEntry("Goose + Addie").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.HISTORY_ENTRY_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.HISTORY_ENTRY_VERDICT, "Over Limit").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.HISTORY_ENTRY_VERDICT, "Partially Checked").assertIsDisplayed()
    }

    @Test
    fun noChecksSaysSoAndShowsNoLimitNotice() {
        composeRule.setContent { HistoryScreen(entries = emptyList()) }

        composeRule.onNodeWithTag(UiTags.HISTORY_EMPTY).assertIsDisplayed()
        composeRule.onAllNodesWithTag(UiTags.HISTORY_LIMIT_NOTICE).assertCountEquals(0)
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

        composeRule.onNodeWithTag(UiTags.HISTORY_LIMIT_NOTICE).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.HISTORY_UPGRADE).performClick()
        assert(upgrade) { "Upgrade to Pro should have fired onUpgrade" }
    }
}
