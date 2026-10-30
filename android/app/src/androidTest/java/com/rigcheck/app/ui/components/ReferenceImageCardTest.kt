package com.rigcheck.app.ui.components

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onChildren
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.R
import com.rigcheck.app.testsupport.assertShowsCrop
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.ReferenceSpots
import com.rigcheck.app.ui.TruckField
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// The pinned reference card (#193, #199): the photo cropped to the focused field with that line outlined, the badge
// naming the field, and the hint. The card has no callback outputs, so what it shows is read from its semantics (the
// crop it is centred on, its description) and, for the outline, from the pixels it draws. The press-and-hold zoom the
// card had before #199 is gone, so the gesture tests assert that holding does nothing.
@RunWith(AndroidJUnit4::class)
class ReferenceImageCardTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val imageTag = "reference_image_card"
    private val badgeTag = "reference_badge"
    private val hint = "Tap a field to see its spot on the tag"
    private val frontGawr = ReferenceSpots.truck.spotFor(TruckField.FrontGawr)!!

    private fun setCard(focused: () -> TruckField?, compact: () -> Boolean = { false }) {
        composeRule.setRigCheckContent {
            PinnedReferenceCard(
                imageRes = R.drawable.ref_truck_tag,
                imageDescription = "Truck compliance label",
                hint = hint,
                label = ReferenceSpots.truck,
                focused = focused(),
                compact = compact(),
                imageModifier = Modifier.testTag(imageTag),
                badgeModifier = Modifier.testTag(badgeTag),
            )
        }
    }

    // True if some pixel of the node is the design's orange (the photo has none), i.e. the focused line is outlined.
    private fun hasTheOrangeOutline(tag: String): Boolean {
        val pixels = composeRule.onNodeWithTag(tag).captureToImage().toPixelMap()
        for (x in 0 until pixels.width) {
            for (y in 0 until pixels.height) {
                val c = pixels[x, y]
                if (c.red > 0.93f && c.green in 0.40f..0.55f && c.blue < 0.2f) return true
            }
        }
        return false
    }

    @Test
    fun withNoFieldFocusedItShowsTheFirstLinesAndTheHintWithNoBadgeOrOutline() {
        setCard(focused = { null })

        composeRule.onNodeWithTag(imageTag).assertShowsCrop(ReferenceSpots.truck.defaultCrop).onChildren().assertCountEquals(0)
        composeRule.onNodeWithText(hint).assertIsDisplayed()
        composeRule.onNodeWithTag(badgeTag).assertDoesNotExist()
        assertFalse("nothing is outlined with no field focused", hasTheOrangeOutline(imageTag))
    }

    @Test
    fun aFocusedFieldShowsItsCropItsBadgeAndTheOutlinedLineAndTheBadgeIsReadOutWhenItAppears() {
        var focused by mutableStateOf<TruckField?>(TruckField.FrontGawr)
        setCard(focused = { focused })

        composeRule.onNodeWithTag(imageTag).assertShowsCrop(frontGawr.crop)
        composeRule.onNodeWithText("Front GAWR").assertIsDisplayed()
        composeRule.onNodeWithTag(badgeTag, useUnmergedTree = true)
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite))
        composeRule.onNodeWithText(hint).assertIsDisplayed()
        assertTrue("the focused line is outlined in orange", hasTheOrangeOutline(imageTag))

        // The field loses focus: back to the default view, the badge and the outline gone.
        focused = null
        composeRule.waitForIdle()
        composeRule.onNodeWithTag(imageTag).assertShowsCrop(ReferenceSpots.truck.defaultCrop)
        composeRule.onNodeWithTag(badgeTag).assertDoesNotExist()
        assertFalse("the outline goes with the focus", hasTheOrangeOutline(imageTag))
    }

    // A field with no line on the label is the default view, not the last field's crop.
    @Test
    fun aFieldWithNoLineOnTheLabelShowsTheDefaultView() {
        setCard(focused = { TruckField.Gcwr })

        composeRule.onNodeWithTag(imageTag).assertShowsCrop(ReferenceSpots.truck.defaultCrop)
        composeRule.onNodeWithTag(badgeTag).assertDoesNotExist()
    }

    @Test
    fun holdingAndDraggingOnTheCardDoesNothing() {
        setCard(focused = { TruckField.FrontGawr })
        val image = composeRule.onNodeWithTag(imageTag)

        image.performTouchInput {
            down(center)
            advanceEventTime(700)
            moveTo(center + Offset(10f, 10f))
        }
        composeRule.waitForIdle()
        // Before #199 two images were composed here, the photo and the zoomed copy of it.
        image.assertShowsCrop(frontGawr.crop).onChildren().assertCountEquals(0)

        image.performTouchInput { up() }
        composeRule.waitForIdle()
        image.assertShowsCrop(frontGawr.crop).onChildren().assertCountEquals(0)
        composeRule.onNodeWithText("Front GAWR").assertIsDisplayed()
    }

    // On a short screen or at a large font the card keeps the caption and shows one label line: the focused line.
    @Test
    fun theCardsPhotoIs116DpHighOr44DpWhenCompactAndTheStripIsCenteredOnTheFocusedLine() {
        var compact by mutableStateOf(false)
        setCard(focused = { TruckField.FrontGawr }, compact = { compact })

        composeRule.onNodeWithText(hint).assertIsDisplayed()
        composeRule.onNodeWithTag(imageTag).assertHeightIsEqualTo(116.dp).assertShowsCrop(frontGawr.crop)

        compact = true
        composeRule.waitForIdle()
        composeRule.onNodeWithTag(imageTag).assertHeightIsEqualTo(44.dp).assertShowsCrop(frontGawr.line)
        assertTrue("the line is still outlined on the strip", hasTheOrangeOutline(imageTag))
    }
}
