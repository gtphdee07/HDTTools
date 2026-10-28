package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Surface
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Rig card" and "Icon button on a card": the card body starts a check, the bin beside it asks to
// delete, and the two never overlap.
@RunWith(AndroidJUnit4::class)
class RigCheckRigCardTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun show(
        onClick: () -> Unit = {},
        onDelete: (() -> Unit)? = {},
        deleteEnabled: Boolean = true,
        index: Int = 0,
        lastChecked: String? = "Last checked Oct 24",
    ) = composeRule.setRigCheckContent {
        RigCheckRigCard(
            nickname = "Blue Goose",
            subtitle = "F-150 and a 24 ft trailer",
            lastChecked = lastChecked,
            index = index,
            onClick = onClick,
            onDelete = onDelete,
            deleteEnabled = deleteEnabled,
            bodyModifier = Modifier.testTag("body"),
            deleteModifier = Modifier.testTag("bin"),
        )
    }

    @Test
    fun cardWithABinShowsItsTextAndTheTwoTargetsDoNotOverlap() {
        var checks = 0
        var deletes = 0
        show(onClick = { checks++ }, onDelete = { deletes++ })
        composeRule.onNodeWithText("Blue Goose").assertIsDisplayed()
        composeRule.onNodeWithText("F-150 and a 24 ft trailer").assertIsDisplayed()
        composeRule.onNodeWithText("Last checked Oct 24").assertIsDisplayed()
        composeRule.onNodeWithTag("body").assertHeightIsAtLeast(84.dp).performClick()
        assertEquals("tapping the body starts a check and does not delete", 1 to 0, checks to deletes)
        composeRule.onNodeWithContentDescription("Delete Blue Goose").performClick()
        assertEquals("tapping the bin deletes and does not start a check", 1 to 1, checks to deletes)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 2)
    }

    @Test
    fun signedOutCardHasNoBin() {
        show(onDelete = null)
        composeRule.onNodeWithTag("bin").assertDoesNotExist()
        composeRule.onNodeWithTag("body").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun theBinIsDisabledWhileADeleteRuns() {
        var deletes = 0
        show(onDelete = { deletes++ }, deleteEnabled = false)
        composeRule.onNodeWithContentDescription("Delete Blue Goose").assertIsNotEnabled().performClick()
        assertEquals(0, deletes)
        composeRule.onNodeWithTag("body").assertIsDisplayed()
    }

    @Test
    fun cardWithoutALastCheckedLineStillShows() {
        show(lastChecked = null)
        composeRule.onNodeWithText("Blue Goose").assertIsDisplayed()
        composeRule.onNodeWithText("Last checked Oct 24").assertDoesNotExist()
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 2)
    }

    @Test
    fun everyAvatarTintKeepsItsInitialReadableAndTheTintsCycle() {
        for (index in 0..5) {
            val colors = rigCardAvatarColors(index)
            assertAa("avatar $index initial", colors.initial, colors.fill, largeText = true)
            assertEquals("tints repeat every three cards", rigCardAvatarColors(index % 3), colors)
        }
        assertAa("nickname", Ink, Surface)
        assertAa("subtitle", InkMuted, Surface)
        show(index = 4)
        composeRule.onNodeWithText("B").assertIsDisplayed()
    }
}
