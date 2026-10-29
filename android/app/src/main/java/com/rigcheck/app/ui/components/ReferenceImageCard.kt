package com.rigcheck.app.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Orange
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

// Tap-and-hold zoom, replacing the mockup's hover-to-zoom pattern (no
// direct mobile equivalent - see ANDROID_DESIGN_BRIEF.md). Press and drag
// anywhere on the reference photo to zoom into that exact spot; release to
// return to normal. Border color (#f0942f) matches the mockup's own
// highlight-ring color exactly (confirmed from the .dc.html source).
//
// With a `height` the photo sits whole in a box of that height (the pinned card's 116 dp); without one it is as wide
// as the column and as tall as the photo.
private const val ZOOM_FACTOR = 2.5f
private val cardShape = RoundedCornerShape(14.dp)

@Composable
fun ReferenceImageCard(
    imageRes: Int,
    contentDescription: String,
    modifier: Modifier = Modifier,
    height: Dp? = null,
    // A strip of the top of the photo, as wide as the box, instead of the whole photo.
    strip: Boolean = false,
) {
    var pressPosition by remember { mutableStateOf<Offset?>(null) }
    var containerSize by remember { mutableStateOf(IntSize.Zero) }
    val fitted = height != null
    val scale = when {
        strip -> ContentScale.Crop
        fitted -> ContentScale.Fit
        else -> ContentScale.FillWidth
    }
    val sizing = if (fitted) Modifier.fillMaxSize() else Modifier.fillMaxWidth()
    val alignment = if (strip) Alignment.TopCenter else Alignment.Center

    Box(
        modifier = modifier
            .fillMaxWidth()
            .then(if (height != null) Modifier.height(height).background(SurfaceSunken) else Modifier)
            .clip(cardShape)
            .onSizeChanged { containerSize = it }
            .pointerInput(Unit) {
                detectDragGesturesAfterLongPress(
                    onDragStart = { offset -> pressPosition = offset },
                    onDrag = { change, _ -> pressPosition = change.position },
                    onDragEnd = { pressPosition = null },
                    onDragCancel = { pressPosition = null },
                )
            },
    ) {
        Image(
            painter = painterResource(imageRes),
            contentDescription = contentDescription,
            contentScale = scale,
            alignment = alignment,
            modifier = sizing,
        )

        val pos = pressPosition
        if (pos != null && containerSize.width > 0 && containerSize.height > 0) {
            val fracX = (pos.x / containerSize.width).coerceIn(0f, 1f)
            val fracY = (pos.y / containerSize.height).coerceIn(0f, 1f)
            Image(
                painter = painterResource(imageRes),
                contentDescription = null,
                contentScale = scale,
                alignment = alignment,
                modifier = Modifier
                    .matchParentSize()
                    .graphicsLayer {
                        scaleX = ZOOM_FACTOR
                        scaleY = ZOOM_FACTOR
                        transformOrigin = TransformOrigin(fracX, fracY)
                    }
                    .border(3.dp, Orange, cardShape),
            )
        }
    }
}

// components.md, "Reference card (pinned crop) and reference image": under the top bar on the Truck and Trailer
// screens, a white card (24 dp radius, shadow md, 12 dp padding) that does not scroll away: a caption row (a search
// icon and the hint) over the photo. The design's focused-field crop and its field badge need a stored crop rectangle
// per field (#199); until then the card shows the whole label with no highlight, and the press-and-hold zoom that was
// there before is what lets a user read a spot on it. `compact` (a short screen or a large font) keeps the caption
// to two lines and shows a strip of the label instead of all of it.
@Composable
fun PinnedReferenceCard(
    imageRes: Int,
    imageDescription: String,
    hint: String,
    modifier: Modifier = Modifier,
    compact: Boolean = false,
    hintModifier: Modifier = Modifier,
    imageModifier: Modifier = Modifier,
) {
    Surface(
        color = SurfaceWhite,
        shape = RoundedCornerShape(Radii.Panel),
        shadowElevation = Elevations.Md,
        border = androidx.compose.foundation.BorderStroke(1.dp, Border),
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
                Text(
                    hint,
                    style = RigCheckStyles.bodySm,
                    color = InkMuted,
                    maxLines = if (compact) 2 else Int.MAX_VALUE,
                    overflow = TextOverflow.Ellipsis,
                    modifier = hintModifier.weight(1f),
                )
            }
            ReferenceImageCard(
                imageRes = imageRes,
                contentDescription = imageDescription,
                height = if (compact) 44.dp else 116.dp,
                strip = compact,
                modifier = imageModifier,
            )
        }
    }
}
