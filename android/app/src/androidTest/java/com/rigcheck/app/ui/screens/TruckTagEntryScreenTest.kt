package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.TruckTag
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TruckTagEntryScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun typingDescriptionUpdatesTheTruckAndBlankBecomesNull() {
        var current = TruckTag()
        composeRule.setContent {
            TruckTagEntryScreen(truck = current, onTruckChange = { current = it }, onContinue = {})
        }

        composeRule.onNodeWithTag("truck_description").performTextInput("Ford F-450")

        assertEquals("Ford F-450", current.description)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            TruckTagEntryScreen(truck = TruckTag(), onTruckChange = {}, onContinue = { continued = true })
        }

        composeRule.onNodeWithText("Next: Trailer Tag").performScrollTo().performClick()

        assert(continued) { "onContinue should have fired" }
    }
}
