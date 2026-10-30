package com.rigcheck.app.ui

import kotlin.math.max
import kotlin.math.min

// The pinned reference card on the Truck and Trailer screens (components.md, "Reference card (pinned crop) and
// reference image"; interaction-notes.md): when a field takes focus the card shows three lines of the label centred on
// that field's printed line, with the line outlined, and a badge naming the field. This file holds the data that needs
// (a crop rectangle per field, as fractions of the photo) and the arithmetic that turns one into what the card draws;
// the Compose side is ReferenceImageCard.

/** A rectangle of a photo as fractions of it: 0 is the left or top edge, 1 the right or bottom edge. */
data class PhotoRect(val left: Float, val top: Float, val right: Float, val bottom: Float) {
    val width: Float get() = right - left
    val height: Float get() = bottom - top

    val isInsidePhoto: Boolean
        get() = left >= 0f && top >= 0f && right <= 1f && bottom <= 1f && width > 0f && height > 0f

    fun contains(other: PhotoRect): Boolean =
        other.left >= left - EDGE_SLACK && other.top >= top - EDGE_SLACK &&
            other.right <= right + EDGE_SLACK && other.bottom <= bottom + EDGE_SLACK

    private companion object {
        // Float arithmetic on the way to and from the window leaves a rounding error of this size.
        const val EDGE_SLACK = 1e-4f
    }
}

/** What the card shows for a focused field: the crop (three lines of the label), the line outlined in it, and the badge's name. */
data class ReferenceSpot(val badge: String, val crop: PhotoRect, val line: PhotoRect)

// Every field of the form, so a test can run over the whole table and name the one a rectangle is missing for. Most of
// them have no line on the label.
enum class TruckField { Description, Name, Gvwr, FrontGawr, RearGawr, Gcwr, StandaloneWeight }

enum class TrailerField { Description, Name, Gvwr, GawrPerAxle, AxleCount, Uvw }

/**
 * One label photo's rectangles. `defaultCrop` is the first three lines of the label (what the card shows with no field
 * focused, or a field with no line on the label) and `defaultLine` the first line, for the one-line strip a short screen
 * or a large font gives the card. `spots` has an entry for each field that has a printed line.
 */
class ReferenceLabel<F : Enum<F>>(
    val defaultCrop: PhotoRect,
    val defaultLine: PhotoRect,
    private val spots: Map<F, ReferenceSpot>,
) {
    /** The spot of the focused field, or null for no field or a field with no line on the label (the default view). */
    fun spotFor(field: F?): ReferenceSpot? = field?.let { spots[it] }
}

object ReferenceSpots {
    // Both photos (res/drawable/ref_truck_tag.jpg and ref_trailer_tag.jpg) are 1600 x 721 px, and the rectangles below
    // were read off them in pixels: left, top, right, bottom. The VIN block of the truck label is not in any of them.
    private const val PHOTO_WIDTH = 1600f
    private const val PHOTO_HEIGHT = 721f

    private fun rect(left: Int, top: Int, right: Int, bottom: Int) =
        PhotoRect(left / PHOTO_WIDTH, top / PHOTO_HEIGHT, right / PHOTO_WIDTH, bottom / PHOTO_HEIGHT)

    // The truck label's top rows: "MFD. BY ..." and the DATE and GVWR on the first, FRONT GAWR on the left and REAR GAWR
    // on the right of the second, the tires of each on the third.
    val truck = ReferenceLabel(
        defaultCrop = rect(312, 104, 712, 198),
        defaultLine = rect(312, 108, 712, 140),
        spots = mapOf(
            TruckField.Gvwr to ReferenceSpot("GVWR", crop = rect(715, 100, 1230, 195), line = rect(900, 108, 1218, 140)),
            TruckField.FrontGawr to ReferenceSpot("Front GAWR", crop = rect(312, 105, 712, 200), line = rect(322, 140, 700, 170)),
            TruckField.RearGawr to ReferenceSpot("Rear GAWR", crop = rect(782, 107, 1192, 200), line = rect(792, 141, 1180, 170)),
        ),
    )

    // The trailer label's rows from the top: MANUFACTURED BY, GVWR, GAWR (EACH AXLE), UVW, TIRE.
    val trailer = ReferenceLabel(
        defaultCrop = rect(140, 214, 640, 308),
        defaultLine = rect(145, 218, 640, 248),
        spots = mapOf(
            TrailerField.Gvwr to ReferenceSpot("GVWR", crop = rect(140, 218, 640, 312), line = rect(145, 250, 505, 280)),
            TrailerField.GawrPerAxle to ReferenceSpot("GAWR per axle", crop = rect(140, 250, 800, 345), line = rect(145, 282, 800, 312)),
            TrailerField.Uvw to ReferenceSpot("UVW", crop = rect(140, 282, 640, 376), line = rect(150, 314, 410, 344)),
        ),
    )
}

/** What a screen reader is told the card shows: the photo, and the line outlined in it once a field with one has focus. */
fun referenceDescription(photo: String, spot: ReferenceSpot?): String =
    if (spot == null) photo else "$photo, ${spot.badge} line outlined"

/**
 * The part of the photo the card draws, and where the outlined line falls in the card's box.
 * `visible` is in fractions of the photo and `lineInBox` in fractions of the box (null: nothing to outline).
 */
data class SpotWindow(val visible: PhotoRect, val lineInBox: PhotoRect?)

/**
 * The window of a photo that shows `target` (a spot's crop, or its line on a one-line strip) in a box of the given
 * shape: the smallest window of the box's shape that holds the target, centred on it, slid back inside the photo where
 * the target is near an edge. `boxAspect` is the box's width over its height, `photoAspect` the photo's.
 *
 * It works in units where the photo is 1 high and `photoAspect` wide, so a window of the box's shape stays that shape.
 */
fun spotWindow(target: PhotoRect, line: PhotoRect?, boxAspect: Float, photoAspect: Float): SpotWindow {
    val targetWidth = target.width * photoAspect
    val targetHeight = target.height
    var width = max(targetWidth, targetHeight * boxAspect)
    var height = width / boxAspect
    // A target that needs more than the photo has (not the case for the stored rectangles): shrink to the photo.
    val shrink = min(1f, min(photoAspect / width, 1f / height))
    width *= shrink
    height *= shrink

    val left = ((target.left + target.right) / 2 * photoAspect - width / 2).coerceIn(0f, photoAspect - width)
    val top = ((target.top + target.bottom) / 2 - height / 2).coerceIn(0f, 1f - height)
    val visible = PhotoRect(left / photoAspect, top, (left + width) / photoAspect, top + height)
    val lineInBox = line?.let {
        PhotoRect(
            (it.left * photoAspect - left) / width,
            (it.top - top) / height,
            (it.right * photoAspect - left) / width,
            (it.bottom - top) / height,
        )
    }
    return SpotWindow(visible, lineInBox)
}
