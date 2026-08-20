package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.TrailerTag
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TrailerTagEntryScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun typingDescriptionUpdatesTheTrailerAndBlankBecomesNull() {
        var current = TrailerTag()
        composeRule.setContent {
            TrailerTagEntryScreen(trailer = current, onTrailerChange = { current = it }, onContinue = {})
        }

        composeRule.onNodeWithTag("trailer_description").performTextInput("Brinkley RV")

        assertEquals("Brinkley RV", current.description)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            TrailerTagEntryScreen(trailer = TrailerTag(), onTrailerChange = {}, onContinue = { continued = true })
        }

        composeRule.onNodeWithText("Next: Scale Ticket").performScrollTo().performClick()

        assert(continued) { "onContinue should have fired" }
    }
}
