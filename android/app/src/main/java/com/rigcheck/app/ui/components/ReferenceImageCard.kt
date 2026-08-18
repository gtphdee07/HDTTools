package com.rigcheck.app.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.SunsetOrange

// Tap-and-hold zoom, replacing the mockup's hover-to-zoom pattern (no
// direct mobile equivalent - see ANDROID_DESIGN_BRIEF.md). Press and drag
// anywhere on the reference photo to zoom into that exact spot; release to
// return to normal. Border color (#f0942f) matches the mockup's own
// highlight-ring color exactly (confirmed from the .dc.html source).
private const val ZOOM_FACTOR = 2.5f
private val cardShape = RoundedCornerShape(14.dp)

@Composable
fun ReferenceImageCard(
    imageRes: Int,
    contentDescription: String,
    modifier: Modifier = Modifier,
) {
    var pressPosition by remember { mutableStateOf<Offset?>(null) }
    var containerSize by remember { mutableStateOf(IntSize.Zero) }

    Box(
        modifier = modifier
            .fillMaxWidth()
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
            contentScale = ContentScale.FillWidth,
            modifier = Modifier.fillMaxWidth(),
        )

        val pos = pressPosition
        if (pos != null && containerSize.width > 0 && containerSize.height > 0) {
            val fracX = (pos.x / containerSize.width).coerceIn(0f, 1f)
            val fracY = (pos.y / containerSize.height).coerceIn(0f, 1f)
            Image(
                painter = painterResource(imageRes),
                contentDescription = null,
                contentScale = ContentScale.FillWidth,
                modifier = Modifier
                    .matchParentSize()
                    .graphicsLayer {
                        scaleX = ZOOM_FACTOR
                        scaleY = ZOOM_FACTOR
                        transformOrigin = TransformOrigin(fracX, fracY)
                    }
                    .border(3.dp, SunsetOrange, cardShape),
            )
        }
    }
}
