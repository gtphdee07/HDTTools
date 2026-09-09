package com.rigcheck.app.ui.experiments.cameraoverlay

import org.junit.Assert.assertEquals
import org.junit.Test
import kotlin.math.abs

// Minor/JVM test for the camera-overlay spike's guide-rectangle sizing
// math (item #18, ClaudePlans/2026-08-27-android-camera-overlay-spike.md).
// Extracted from CameraOverlaySpikeScreen's Canvas draw block into a pure
// function (computeGuideRect) specifically so this doesn't need
// Robolectric/an emulator - it's plain arithmetic, no Android framework
// dependency once separated from the Composable.

private const val TOLERANCE = 0.001f

class GuideRectMathTest {

    @Test
    fun wideCanvas_isWidthBound_heightShrinksToFitAspectRatio() {
        // 1000x1000 canvas, aspect ratio 2.22:1 (real tag proportions) ->
        // width-bound: height = maxWidth / aspectRatio is well within maxHeight.
        val rect = computeGuideRect(canvasWidth = 1000f, canvasHeight = 1000f, aspectRatio = 2.22f, fraction = 0.85f)

        val expectedWidth = 1000f * 0.85f
        val expectedHeight = expectedWidth / 2.22f
        assertEquals(expectedWidth, rect.width, TOLERANCE)
        assertEquals(expectedHeight, rect.height, TOLERANCE)
    }

    @Test
    fun wideFlatCanvas_isHeightBound_widthShrinksToFitAspectRatio() {
        // For a wide guide box (aspectRatio 2.22:1), height-bound sizing
        // only kicks in when the canvas itself is proportionally wider
        // than the guide (e.g. a landscape screen) - a tall/narrow canvas
        // is width-bound instead, since the wide guide needs very little
        // height once its width is fixed. 2000x500 (4:1, wider than 2.22:1)
        // forces the height-bound branch: width-bound would need
        // maxWidth/aspectRatio = 1700/2.22 = 765.8px of height, which
        // overflows the 500*0.85=425px actually available.
        val rect = computeGuideRect(canvasWidth = 2000f, canvasHeight = 500f, aspectRatio = 2.22f, fraction = 0.85f)

        val expectedHeight = 500f * 0.85f
        val expectedWidth = expectedHeight * 2.22f
        assertEquals(expectedWidth, rect.width, TOLERANCE)
        assertEquals(expectedHeight, rect.height, TOLERANCE)
        // Sanity: the width-bound candidate really would have overflowed.
        val widthBoundHeightCandidate = (2000f * 0.85f) / 2.22f
        assert(widthBoundHeightCandidate > 500f * 0.85f)
    }

    @Test
    fun guideRect_isAlwaysHorizontallyAndVerticallyCentered() {
        val rect = computeGuideRect(canvasWidth = 1080f, canvasHeight = 2280f, aspectRatio = 2.22f, fraction = 0.85f)

        val leftMargin = rect.left
        val rightMargin = 1080f - (rect.left + rect.width)
        val topMargin = rect.top
        val bottomMargin = 2280f - (rect.top + rect.height)
        assertEquals(leftMargin, rightMargin, TOLERANCE)
        assertEquals(topMargin, bottomMargin, TOLERANCE)
    }

    @Test
    fun guideRect_neverExceedsTheFractionOfCanvasInEitherDimension() {
        // Across a spread of realistic phone preview aspect ratios, the
        // guide box must never claim more than `fraction` of either
        // dimension - that's the whole point of GUIDE_FRACTION as a margin.
        val sizes = listOf(1080f to 2280f, 2280f to 1080f, 1440f to 1440f, 720f to 1600f)
        for ((w, h) in sizes) {
            val rect = computeGuideRect(canvasWidth = w, canvasHeight = h, aspectRatio = 2.22f, fraction = 0.85f)
            assert(rect.width <= w * 0.85f + TOLERANCE) { "width ${rect.width} exceeded fraction bound for ${w}x$h" }
            assert(rect.height <= h * 0.85f + TOLERANCE) { "height ${rect.height} exceeded fraction bound for ${w}x$h" }
        }
    }

    @Test
    fun guideRect_alwaysPreservesTheRequestedAspectRatio() {
        val sizes = listOf(1080f to 2280f, 2280f to 1080f, 1440f to 1440f)
        for ((w, h) in sizes) {
            val rect = computeGuideRect(canvasWidth = w, canvasHeight = h, aspectRatio = 2.22f, fraction = 0.85f)
            val actualAspectRatio = rect.width / rect.height
            assert(abs(actualAspectRatio - 2.22f) < 0.01f) {
                "aspect ratio $actualAspectRatio didn't match 2.22 for ${w}x$h"
            }
        }
    }
}
