package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
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

        composeRule.onNodeWithText("Experimental Tool —\nNot for Safety Decisions").assertIsDisplayed()

        composeRule.onNodeWithText("I Understand, Continue").performClick()

        assert(acknowledged) { "onAcknowledge should have fired" }
    }
}
