package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.SemanticsPropertyKey
import androidx.compose.ui.semantics.SemanticsPropertyReceiver
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.PhotoRect
import com.rigcheck.app.ui.ReferenceLabel
import com.rigcheck.app.ui.referenceDescription
import com.rigcheck.app.ui.spotWindow
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Orange
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintOrange
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite
import kotlin.math.roundToInt

private val cardShape = RoundedCornerShape(14.dp)

// From this font scale the reference card is the one-line strip (EntryScreenFrame) and its hint steps aside for the badge.
internal const val LARGE_FONT_SCALE = 1.6f

// The line outlined in the crop: 2.5 dp in orange on tint-orange (components.md). The tint is see-through so the printed
// words show through it.
private val lineOutline = 2.5.dp
private val lineCorner = 6.dp
private const val LINE_TINT_ALPHA = 0.35f

/**
 * What the card is showing, for a test and for assistive tech: the rectangle of the photo it centres on (the focused
 * field's crop, or its line on the one-line strip; the label's first lines when no field with a spot has focus).
 */
val ReferenceCropKey = SemanticsPropertyKey<PhotoRect>("ReferenceCrop")
private var SemanticsPropertyReceiver.referenceCrop by ReferenceCropKey

// The photo's part around the focused field, drawn so that `target` fills the box (`spotWindow`), with `line` outlined.
// There is no gesture on it: the press-and-hold zoom it had until #199 is gone (interaction-notes.md, "no gesture is
// needed anywhere").
@Composable
fun ReferenceImageCard(
    imageRes: Int,
    contentDescription: String,
    target: PhotoRect,
    line: PhotoRect?,
    height: Dp,
    modifier: Modifier = Modifier,
) {
    val photo: ImageBitmap = ImageBitmap.imageResource(imageRes)
    val photoAspect = photo.width.toFloat() / photo.height

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .background(SurfaceSunken)
            .clip(cardShape)
            .semantics {
                this.contentDescription = contentDescription
                referenceCrop = target
            },
    ) {
        val window = spotWindow(target, line, size.width / size.height, photoAspect)
        drawImage(
            image = photo,
            srcOffset = IntOffset((window.visible.left * photo.width).roundToInt(), (window.visible.top * photo.height).roundToInt()),
            srcSize = IntSize((window.visible.width * photo.width).roundToInt(), (window.visible.height * photo.height).roundToInt()),
            dstSize = IntSize(size.width.roundToInt(), size.height.roundToInt()),
            filterQuality = FilterQuality.High,
        )
        window.lineInBox?.let { box ->
            val stroke = lineOutline.toPx()
            // Inset by half the stroke so the outline of a line as wide as the box is not cut at its edge.
            val topLeft = Offset(box.left * size.width + stroke / 2, box.top * size.height + stroke / 2)
            val outlined = Size(box.width * size.width - stroke, box.height * size.height - stroke)
            val corner = CornerRadius(lineCorner.toPx())
            drawRoundRect(TintOrange.copy(alpha = LINE_TINT_ALPHA), topLeft, outlined, corner)
            drawRoundRect(Orange, topLeft, outlined, corner, style = Stroke(stroke))
        }
    }
}

// Reports a field's focus to the card: `onFocused(field)` when it takes focus, and `onFocused(null)` when it loses it
// unless another field has already taken over (the order in which the two events arrive is not promised).
fun <F> Modifier.reportsFocusAs(field: F, current: () -> F?, onFocused: (F?) -> Unit): Modifier = onFocusChanged { state ->
    if (state.isFocused) onFocused(field) else if (current() == field) onFocused(null)
}

// components.md, "Reference card (pinned crop) and reference image": under the top bar on the Truck and Trailer
// screens, a white card (24 dp radius, shadow md, 12 dp padding) that does not scroll away: a caption row (a search
// icon, the hint, and a badge naming the focused field) over a crop of the label showing three lines, the focused
// field's line outlined. With no field focused, or one with no line on the label, it shows the label's first lines and
// no badge. `compact` (a short screen or a large font) keeps the caption to two lines and the crop to one label line.
@Composable
fun <F : Enum<F>> PinnedReferenceCard(
    imageRes: Int,
    imageDescription: String,
    hint: String,
    label: ReferenceLabel<F>,
    focused: F?,
    modifier: Modifier = Modifier,
    compact: Boolean = false,
    hintModifier: Modifier = Modifier,
    imageModifier: Modifier = Modifier,
    badgeModifier: Modifier = Modifier,
) {
    val spot = label.spotFor(focused)
    // What the photo is centred on: the focused line alone on the one-line strip, else three lines around it.
    val target = if (compact) spot?.line ?: label.defaultLine else spot?.crop ?: label.defaultCrop
    // At a large font the badge leaves the hint room for a few letters ("Tap a fi..."). The hint's point is to get the
    // user to tap a field; once one is focused the badge says which field the card shows, so the hint steps aside (#197).
    val showHint = !(spot != null && LocalDensity.current.fontScale >= LARGE_FONT_SCALE)
    Surface(
        color = SurfaceWhite,
        shape = RoundedCornerShape(Radii.Panel),
        shadowElevation = Elevations.Md,
        border = BorderStroke(1.dp, Border),
        modifier = modifier.fillMaxWidth(),
    ) {
        // 12 dp of padding inside the 1 dp border: the card is 170 dp high, as drawn.
        Column(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(13.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(horizontal = 4.dp),
            ) {
                Icon(Icons.Filled.Search, contentDescription = null, tint = TealDeep, modifier = Modifier.size(22.dp))
                if (showHint) {
                    Text(
                        hint,
                        style = RigCheckStyles.bodySm,
                        color = InkMuted,
                        maxLines = if (compact) 2 else Int.MAX_VALUE,
                        overflow = TextOverflow.Ellipsis,
                        modifier = hintModifier.weight(1f),
                    )
                } else {
                    Spacer(Modifier.weight(1f))
                }
                if (spot != null) {
                    // Read out when it appears, so a screen reader user hears which field the card now shows.
                    RigCheckBadge(
                        text = spot.badge,
                        kind = RigCheckBadgeKind.Plan,
                        modifier = badgeModifier.semantics { liveRegion = LiveRegionMode.Polite },
                    )
                }
            }
            ReferenceImageCard(
                imageRes = imageRes,
                contentDescription = referenceDescription(imageDescription, spot),
                target = target,
                line = spot?.line,
                height = if (compact) 44.dp else 116.dp,
                modifier = imageModifier,
            )
        }
    }
}
