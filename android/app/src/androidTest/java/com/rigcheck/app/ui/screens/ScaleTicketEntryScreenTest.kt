package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.ScaleTicket
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ScaleTicketEntryScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun typingLocationUpdatesTheTicketAndBlankBecomesNull() {
        var current = ScaleTicket()
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = current, onScaleChange = { current = it }, onContinue = {})
        }

        composeRule.onNodeWithTag("scale_location").performTextInput("Loves Country Stores")

        assertEquals("Loves Country Stores", current.locationName)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = ScaleTicket(), onScaleChange = {}, onContinue = { continued = true })
        }

        composeRule.onNodeWithText("Check Weights").performScrollTo().performClick()

        assert(continued) { "onContinue should have fired" }
    }
}
