package com.rigcheck.app.ui.components

import androidx.compose.material3.Text
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Teal
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Top app bar (header)": the title, an optional Back, the balance chip at the end, an optional second
// row (account status or step indicator), and a compact form while the keyboard is open.
@RunWith(AndroidJUnit4::class)
class RigCheckTopBarTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun titleBackAndBalanceChipAreAllShownAndTappable() {
        var backs = 0
        var chips = 0
        composeRule.setRigCheckContent {
            RigCheckTopBar(
                title = "Which rig?",
                onBack = { backs++ },
                end = { CreditBalanceChip(balance = 3, onClick = { chips++ }) },
            )
        }
        composeRule.onNodeWithText("Which rig?").assertIsDisplayed()
        composeRule.onNodeWithText("3 scans").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Back").performClick()
        composeRule.onNodeWithText("3 scans").performClick()
        assertEquals(1, backs)
        assertEquals(1, chips)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 2)
        assertAa("title on the teal bar", Ink, Teal)
    }

    @Test
    fun withASecondRowItIsShownUnderTheTitle() {
        composeRule.setRigCheckContent {
            RigCheckTopBar(title = "Truck tag", onBack = {}, below = { Text("Step 1 of 3") })
        }
        composeRule.onNodeWithText("Step 1 of 3").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun compactBarKeepsTheTitleAndBack() {
        composeRule.setRigCheckContent { RigCheckTopBar(title = "Truck tag", onBack = {}, compact = true) }
        composeRule.onNodeWithText("Truck tag").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Back").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun backIsDisabledWhileAPaidScanIsInFlight() {
        var backs = 0
        composeRule.setRigCheckContent { RigCheckTopBar(title = "Scan", onBack = { backs++ }, backEnabled = false) }
        composeRule.onNodeWithContentDescription("Back").assertIsNotEnabled().performClick()
        assertEquals(0, backs)
    }

    @Test
    fun withoutAnOnBackThereIsNoBackButton() {
        composeRule.setRigCheckContent { RigCheckTopBar(title = "RigCheck") }
        composeRule.onNodeWithText("RigCheck").assertIsDisplayed()
        composeRule.onAllNodesWithContentDescription("Back").assertCountEquals(0)
    }
}
