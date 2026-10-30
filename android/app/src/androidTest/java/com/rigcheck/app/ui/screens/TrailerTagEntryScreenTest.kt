package com.rigcheck.app.ui.screens

import androidx.compose.ui.focus.FocusManager
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.test.assertContentDescriptionEquals
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onChildren
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performTouchInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.testsupport.assertShowsCrop
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.ui.ReferenceSpots
import com.rigcheck.app.ui.TrailerField
import com.rigcheck.app.ui.UiTags
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

        composeRule.onNodeWithTag(UiTags.TRAILER_DESCRIPTION).performTextInput("Brinkley RV")

        assertEquals("Brinkley RV", current.description)
    }

    @Test
    fun continueButtonInvokesOnContinue() {
        var continued = false
        composeRule.setContent {
            TrailerTagEntryScreen(trailer = TrailerTag(), onTrailerChange = {}, onContinue = { continued = true })
        }

        // Pinned below the scrolling form, so it is on screen however tall the content is.
        composeRule.onNodeWithTag(UiTags.TRAILER_NEXT_BUTTON).assertIsDisplayed().performClick()

        assert(continued) { "onContinue should have fired" }
    }

    // #193: the top bar's Back, and the pinned reference card that replaced the hover hint.
    @Test
    fun theTopBarsBackGoesBack() {
        var backs = 0
        composeRule.setContent {
            TrailerTagEntryScreen(trailer = TrailerTag(), onTrailerChange = {}, onContinue = {}, onBack = { backs++ })
        }

        composeRule.onNodeWithTag(UiTags.TRAILER_BACK).assertContentDescriptionEquals("Back").performClick()

        assertEquals(1, backs)
    }

    // #199: the pinned card follows the focused field (as on the Truck screen): its crop moves to that field's
    // rectangle and a badge names the field; a field with no line on the label, or no field at all, is the default view.
    @Test
    fun focusingEachFieldMovesThePinnedCardsCropAndBadgeAndLeavingTheFieldsReturnsToTheDefaultView() {
        lateinit var focusManager: FocusManager
        composeRule.setContent {
            focusManager = LocalFocusManager.current
            TrailerTagEntryScreen(trailer = TrailerTag(), onTrailerChange = {}, onContinue = {})
        }
        val image = composeRule.onNodeWithTag(UiTags.TRAILER_REFERENCE_IMAGE)
        val label = ReferenceSpots.trailer
        val hint = "Tap a field to see its spot on the tag"

        fun showsTheDefaultView() {
            image.assertShowsCrop(label.defaultCrop).assertContentDescriptionEquals("Trailer compliance label")
            composeRule.onNodeWithTag(UiTags.TRAILER_REFERENCE_FOCUS_BADGE).assertDoesNotExist()
            composeRule.onNodeWithTagText(UiTags.TRAILER_REFERENCE_HINT, hint).assertExists()
        }
        showsTheDefaultView()

        listOf(
            Triple(UiTags.TRAILER_UVW_FIELD, TrailerField.Uvw, "UVW"),
            Triple(UiTags.TRAILER_GVWR_FIELD, TrailerField.Gvwr, "GVWR"),
            Triple(UiTags.TRAILER_GAWR_FIELD, TrailerField.GawrPerAxle, "GAWR per axle"),
            Triple(UiTags.TRAILER_UVW_FIELD, TrailerField.Uvw, "UVW"),
        ).forEach { (tag, field, badge) ->
            composeRule.onNodeWithTag(tag).scrollToIfScrollable().performClick()
            // (Not `assertIsDisplayed`: the test activity pans for the keyboard, which moves the pinned card off the window.)
            composeRule.onNodeWithTagText(UiTags.TRAILER_REFERENCE_FOCUS_BADGE, badge).assertExists()
            image.assertShowsCrop(label.spotFor(field)!!.crop)
                .assertContentDescriptionEquals("Trailer compliance label, $badge line outlined")
            composeRule.onNodeWithTagText(UiTags.TRAILER_REFERENCE_HINT, hint).assertExists()
        }

        // A field with no line on the label (the description, the name, the axle count).
        listOf(UiTags.TRAILER_DESCRIPTION, UiTags.TRAILER_NAME_FIELD, UiTags.TRAILER_AXLE_COUNT_FIELD).forEach { tag ->
            composeRule.onNodeWithTag(tag).scrollToIfScrollable().performClick()
            showsTheDefaultView()
            composeRule.onNodeWithTag(UiTags.TRAILER_GAWR_FIELD).scrollToIfScrollable().performClick()
            composeRule.onNodeWithTagText(UiTags.TRAILER_REFERENCE_FOCUS_BADGE, "GAWR per axle").assertExists()
        }

        composeRule.runOnIdle { focusManager.clearFocus() }
        showsTheDefaultView()
    }

    // The decision of #199 (owner, 2026-10-29): the press-and-hold zoom the pinned photo had is gone.
    @Test
    fun holdingOnThePinnedReferenceImageDoesNothing() {
        composeRule.setContent {
            TrailerTagEntryScreen(trailer = TrailerTag(), onTrailerChange = {}, onContinue = {})
        }
        // The GVWR is the field nearest the top, so the keyboard does not pan the card off the test window.
        composeRule.onNodeWithTag(UiTags.TRAILER_GVWR_FIELD).scrollToIfScrollable().performClick()
        val image = composeRule.onNodeWithTag(UiTags.TRAILER_REFERENCE_IMAGE)
        val crop = ReferenceSpots.trailer.spotFor(TrailerField.Gvwr)!!.crop
        image.assertShowsCrop(crop)

        image.performTouchInput {
            down(center)
            advanceEventTime(700)
            moveTo(center + Offset(10f, 10f))
        }
        composeRule.waitForIdle()
        image.assertShowsCrop(crop).onChildren().assertCountEquals(0)

        image.performTouchInput { up() }
        composeRule.waitForIdle()
        image.assertShowsCrop(crop).onChildren().assertCountEquals(0)
        composeRule.onNodeWithTagText(UiTags.TRAILER_REFERENCE_FOCUS_BADGE, "GVWR").assertExists()
    }
}
