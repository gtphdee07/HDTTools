package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.getBoundsInRoot
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.ui.UiTags
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DisclaimerScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun rendersFinalizedCopyAndAcknowledgeFiresCallback() {
        var acknowledged = false
        composeRule.setContent { DisclaimerScreen(onAcknowledge = { acknowledged = true }) }

        composeRule.onNodeWithTagText(UiTags.DISCLAIMER_TITLE, "Experimental Tool —\nNot for Safety Decisions").assertIsDisplayed()

        composeRule.onNodeWithTag(UiTags.DISCLAIMER_ACCEPT_BUTTON).performClick()

        assert(acknowledged) { "onAcknowledge should have fired" }
    }

    // The wording is legally reviewed (docs/android-redesign/design-return/ui-redesign-map.json, disclaimer.body_*):
    // the re-skin changes how it is laid out, never a character of it. These are the inventory's strings.
    @Test
    fun theWordingIsTheReviewedWordingCharacterForCharacter() {
        composeRule.setContent { DisclaimerScreen(onAcknowledge = {}) }

        val expected = mapOf(
            UiTags.DISCLAIMER_TITLE to "Experimental Tool —\nNot for Safety Decisions",
            UiTags.DISCLAIMER_BODY_1 to "RigCheck is an experimental project built to learn app development, not a certified or " +
                "professional weight-safety tool. You type in numbers straight off your own tag and ticket photos, and the " +
                "math that follows is simplified — any step of that chain can be wrong.",
            UiTags.DISCLAIMER_BODY_2 to "Do not use this tool to decide whether your rig is safe to tow. Always verify actual " +
                "weights and ratings using a certified scale and your vehicle's official documentation, and consult a " +
                "qualified professional if you're unsure. You use this tool, and any decisions you make based on it, " +
                "entirely at your own risk and responsibility.",
            UiTags.DISCLAIMER_ACCEPT_BUTTON to "I Understand, Continue",
        )
        // `onNodeWithTagText` matches the whole text, so a changed character leaves nothing to find.
        expected.forEach { (tag, text) ->
            composeRule.onNodeWithTagText(tag, text).scrollToIfScrollable().assertIsDisplayed()
        }
    }

    // The page scrolls and the button does not: on a screen too short for the words, the button is still there with the
    // words scrolled away (the layout test holds this on a 360 x 640 phone at font scale 2.0).
    @Test
    fun theButtonStaysPinnedWhileThePageScrolls() {
        composeRule.setContent { Box(Modifier.height(300.dp)) { DisclaimerScreen(onAcknowledge = {}) } }

        val before = composeRule.onNodeWithTag(UiTags.DISCLAIMER_ACCEPT_BUTTON).getBoundsInRoot()
        composeRule.onNodeWithTag(UiTags.DISCLAIMER_BODY_2, useUnmergedTree = true).performScrollTo()
        val after = composeRule.onNodeWithTag(UiTags.DISCLAIMER_ACCEPT_BUTTON).getBoundsInRoot()

        composeRule.onNodeWithTag(UiTags.DISCLAIMER_ACCEPT_BUTTON).assertIsDisplayed()
        assertEquals("the button moved when the page scrolled", before.top, after.top)
    }
}
