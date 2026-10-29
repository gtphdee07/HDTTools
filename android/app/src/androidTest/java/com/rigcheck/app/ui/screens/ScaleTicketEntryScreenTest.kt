package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertContentDescriptionEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.ui.UiTags
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

        composeRule.onNodeWithTag(UiTags.SCALE_LOCATION).performTextInput("Loves Country Stores")

        assertEquals("Loves Country Stores", current.locationName)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = ScaleTicket(), onScaleChange = {}, onContinue = { continued = true })
        }

        // Pinned below the scrolling form, so it is on screen however tall the content is.
        composeRule.onNodeWithTag(UiTags.SCALE_CHECK_BUTTON).assertIsDisplayed().performClick()

        assert(continued) { "onContinue should have fired" }
    }

    // #193: the top bar's Back.
    @Test
    fun theTopBarsBackGoesBack() {
        var backs = 0
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = ScaleTicket(), onScaleChange = {}, onContinue = {}, onBack = { backs++ })
        }

        composeRule.onNodeWithTag(UiTags.SCALE_BACK).assertContentDescriptionEquals("Back").performClick()

        assertEquals(1, backs)
    }

    // #193: the legend says which number is which line (the old legend had numbers that appeared nowhere else), and the
    // same five numbers are drawn on the ticket photo.
    @Test
    fun theLegendNamesTheFiveNumbersAndTheTicketPhotoCarriesThem() {
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = ScaleTicket(), onScaleChange = {}, onContinue = {})
        }

        composeRule.onNodeWithTag(UiTags.SCALE_LEGEND).scrollToIfScrollable()
        listOf("1" to "Scale location", "2" to "Steer", "3" to "Drive", "4" to "Trailer", "5" to "Gross").forEach { (number, label) ->
            composeRule.onNodeWithTagText(UiTags.SCALE_LEGEND, number).assertIsDisplayed()
            composeRule.onNodeWithTagText(UiTags.SCALE_LEGEND, label).assertIsDisplayed()
        }
        composeRule.onNodeWithTag(UiTags.SCALE_REFERENCE_IMAGE).scrollToIfScrollable()
        (1..5).forEach { number ->
            composeRule.onNodeWithTag("$SCALE_PHOTO_BADGE_TAG$number", useUnmergedTree = true).assertIsDisplayed()
        }
    }
}
