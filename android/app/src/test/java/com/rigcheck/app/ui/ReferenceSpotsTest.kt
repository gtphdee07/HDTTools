package com.rigcheck.app.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// #199: the stored crop rectangles of the Truck and Trailer reference photos, and the window the pinned card draws from one.
class ReferenceSpotsTest {

    // The fields with a printed line on the label (the label has no line for a description, a name, the GCWR the owner's
    // manual gives, the stand-alone weight or the axle count), and the badge the design names each with.
    private val truckOnTheLabel = mapOf(
        TruckField.Gvwr to "GVWR",
        TruckField.FrontGawr to "Front GAWR",
        TruckField.RearGawr to "Rear GAWR",
    )
    private val trailerOnTheLabel = mapOf(
        TrailerField.Gvwr to "GVWR",
        TrailerField.GawrPerAxle to "GAWR per axle",
        TrailerField.Uvw to "UVW",
    )

    private fun <F : Enum<F>> checkEveryField(label: ReferenceLabel<F>, fields: List<F>, onTheLabel: Map<F, String>) {
        for (field in fields) {
            val spot = label.spotFor(field)
            val badge = onTheLabel[field]
            if (badge == null) {
                assertNull("$field has no line on the label, so no spot", spot)
                continue
            }
            assertNotNull("$field has a printed line on the label, so it needs a stored rectangle", spot)
            spot!!
            assertEquals("the badge of $field", badge, spot.badge)
            assertTrue("the crop of $field lies outside the photo: ${spot.crop}", spot.crop.isInsidePhoto)
            assertTrue("the line of $field lies outside the photo: ${spot.line}", spot.line.isInsidePhoto)
            assertTrue("the line of $field is not inside its crop: ${spot.line} in ${spot.crop}", spot.crop.contains(spot.line))
        }
    }

    @Test
    fun everyTruckFieldWithALineOnTheLabelHasARectangleInsideThePhotoAndTheOthersHaveNone() {
        checkEveryField(ReferenceSpots.truck, TruckField.entries, truckOnTheLabel)
    }

    @Test
    fun everyTrailerFieldWithALineOnTheLabelHasARectangleInsideThePhotoAndTheOthersHaveNone() {
        checkEveryField(ReferenceSpots.trailer, TrailerField.entries, trailerOnTheLabel)
    }

    @Test
    fun noFieldAtAllIsTheDefaultViewWithNoOutlinedLine() {
        assertNull(ReferenceSpots.truck.spotFor(null))
        assertNull(ReferenceSpots.trailer.spotFor(null))
    }

    @Test
    fun theDefaultViewIsTheFirstLinesOfTheLabelInsideThePhoto() {
        for ((name, label) in listOf("truck" to ReferenceSpots.truck, "trailer" to ReferenceSpots.trailer)) {
            assertTrue("the $name label's default crop is outside the photo", label.defaultCrop.isInsidePhoto)
            assertTrue("the $name label's first line is outside the photo", label.defaultLine.isInsidePhoto)
            assertTrue("the $name label's first line is not in its default crop", label.defaultCrop.contains(label.defaultLine))
            assertTrue("the $name label's default crop starts in the top third of the photo", label.defaultCrop.top < 0.33f)
        }
    }

    // A swapped pair of rectangles is still inside the photo, so the places on the label are checked: on the truck label
    // the GVWR is the top right, the front axle's line is on the left and the rear axle's on the right, under it; on the
    // trailer label the lines run GVWR, GAWR, UVW from the top.
    @Test
    fun theTruckRectanglesSitWhereTheLinesArePrintedOnTheLabel() {
        val gvwr = ReferenceSpots.truck.spotFor(TruckField.Gvwr)!!.line
        val front = ReferenceSpots.truck.spotFor(TruckField.FrontGawr)!!.line
        val rear = ReferenceSpots.truck.spotFor(TruckField.RearGawr)!!.line

        assertTrue("GVWR is on the right half", gvwr.left > 0.5f)
        assertTrue("Front GAWR is on the left half", front.right < 0.5f)
        assertTrue("Rear GAWR is on the right half", rear.left > 0.45f)
        assertTrue("GVWR is above both GAWR lines", gvwr.bottom <= front.top + 0.01f && gvwr.bottom <= rear.top + 0.01f)
        assertTrue("Front and Rear GAWR are on the same row", kotlin.math.abs(front.top - rear.top) < 0.02f)
    }

    @Test
    fun theTrailerRectanglesRunDownTheLabelInTheOrderOfTheLines() {
        val gvwr = ReferenceSpots.trailer.spotFor(TrailerField.Gvwr)!!.line
        val gawr = ReferenceSpots.trailer.spotFor(TrailerField.GawrPerAxle)!!.line
        val uvw = ReferenceSpots.trailer.spotFor(TrailerField.Uvw)!!.line

        assertTrue("GVWR is above GAWR", gvwr.bottom <= gawr.top + 0.01f)
        assertTrue("GAWR is above UVW", gawr.bottom <= uvw.top + 0.01f)
    }

    @Test
    fun aScreenReaderIsToldWhichLineIsOutlinedOnceAFieldWithOneHasFocus() {
        assertEquals("Truck compliance label", referenceDescription("Truck compliance label", null))
        val front = ReferenceSpots.truck.spotFor(TruckField.FrontGawr)
        assertEquals("Truck compliance label, Front GAWR line outlined", referenceDescription("Truck compliance label", front))
    }

    // --- The window the card draws -----------------------------------------------------------------------------

    private val photoAspect = 1600f / 721f

    // A 354 x 116 dp box and the 44 dp strip of a short screen.
    private val tallBox = 354f / 116f
    private val strip = 354f / 44f

    private fun every(): List<Pair<String, ReferenceSpot?>> =
        listOf("no field" to null) +
            TruckField.entries.mapNotNull { f -> ReferenceSpots.truck.spotFor(f)?.let { "truck $f" to it } } +
            TrailerField.entries.mapNotNull { f -> ReferenceSpots.trailer.spotFor(f)?.let { "trailer $f" to it } }

    @Test
    fun theWindowOfEveryViewIsInsideThePhotoHasTheBoxsShapeAndHoldsTheWholeCrop() {
        for ((name, spot) in every()) {
            val label = if (name.startsWith("trailer")) ReferenceSpots.trailer else ReferenceSpots.truck
            val crop = spot?.crop ?: label.defaultCrop
            val window = spotWindow(crop, spot?.line, tallBox, photoAspect)

            assertTrue("$name: the window ${window.visible} is outside the photo", window.visible.isInsidePhoto)
            val shape = (window.visible.width * photoAspect) / window.visible.height
            assertEquals("$name: the window is not the box's shape", tallBox, shape, 0.01f)
            assertTrue("$name: the window does not hold the crop $crop", window.visible.contains(crop))
        }
    }

    @Test
    fun theCompactWindowHoldsTheWholeOfTheFocusedLine() {
        for ((name, spot) in every()) {
            val label = if (name.startsWith("trailer")) ReferenceSpots.trailer else ReferenceSpots.truck
            val line = spot?.line ?: label.defaultLine
            val window = spotWindow(line, spot?.line, strip, photoAspect)

            assertTrue("$name: the strip ${window.visible} is outside the photo", window.visible.isInsidePhoto)
            assertTrue("$name: the strip does not hold the line $line", window.visible.contains(line))
        }
    }

    @Test
    fun theOutlinedLineLandsInsideTheBoxAndTheDefaultViewOutlinesNothing() {
        for ((name, spot) in every()) {
            val label = if (name.startsWith("trailer")) ReferenceSpots.trailer else ReferenceSpots.truck
            val window = spotWindow(spot?.crop ?: label.defaultCrop, spot?.line, tallBox, photoAspect)
            val outline = window.lineInBox
            if (spot == null) {
                assertNull("$name outlines no line", outline)
            } else {
                assertNotNull("$name outlines its line", outline)
                // The widest line fills the box's width exactly, so the right edge may come out a rounding error past 1.
                assertTrue(
                    "$name: the outlined line $outline is not wholly in the box",
                    outline!!.left >= -0.001f && outline.top >= -0.001f && outline.right <= 1.001f && outline.bottom <= 1.001f,
                )
            }
        }
    }

    @Test
    fun theWindowIsCenteredOnTheCropWhereThePhotoHasRoomAndSlidesInWhereItHasNot() {
        val centered = PhotoRect(0.4f, 0.4f, 0.6f, 0.5f)
        val inTheMiddle = spotWindow(centered, null, 3f, photoAspect)
        assertEquals(0.5f, (inTheMiddle.visible.left + inTheMiddle.visible.right) / 2, 0.001f)
        assertEquals(0.45f, (inTheMiddle.visible.top + inTheMiddle.visible.bottom) / 2, 0.001f)

        // A crop against the top left corner: the window cannot be centered on it, so it keeps the corner.
        val corner = PhotoRect(0f, 0f, 0.2f, 0.1f)
        val atTheCorner = spotWindow(corner, null, 3f, photoAspect)
        assertEquals(0f, atTheCorner.visible.left, 0.001f)
        assertEquals(0f, atTheCorner.visible.top, 0.001f)
        assertTrue("the corner crop is still held", atTheCorner.visible.contains(corner))
    }
}
