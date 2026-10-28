package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.SurfaceSunken
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Empty state": the title and the text, with or without the mark.
@RunWith(AndroidJUnit4::class)
class RigCheckEmptyStateTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun assertReadable() {
        assertAa("title on the sunken fill", Ink, SurfaceSunken)
        assertAa("text on the sunken fill", InkMuted, SurfaceSunken)
    }

    @Test
    fun emptyStateShowsItsTitleAndText() {
        composeRule.setRigCheckContent {
            RigCheckEmptyState("No saved rigs yet", "Finish a check and your rig shows up here. Manual entry is free.")
        }
        composeRule.onNodeWithText("No saved rigs yet").assertIsDisplayed()
        composeRule.onNodeWithText("Finish a check and your rig shows up here. Manual entry is free.").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
        assertReadable()
    }

    @Test
    fun emptyStateWithAMarkShowsItAboveTheText() {
        composeRule.setRigCheckContent {
            RigCheckEmptyState("No history yet", "Your finished checks will be listed here.", mark = {
                Box(Modifier.fillMaxSize().testTag("mark"))
            })
        }
        composeRule.onNodeWithTag("mark").assertIsDisplayed()
        composeRule.onNodeWithText("No history yet").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
        assertReadable()
    }
}
