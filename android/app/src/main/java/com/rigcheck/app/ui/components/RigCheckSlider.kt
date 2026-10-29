package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsDraggedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Slider
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

private val PRESSED_THUMB = 32.dp

// components.md, "Slider": a 4 dp track (`border`) with a `teal-deep` fill up to the thumb, a 28 dp thumb with a 3 dp
// `teal-deep` ring and a white centre (32 dp while it is pressed), and a 48 dp touch height. Material 3's slider
// supplies the dragging and the semantics; the track and the thumb are drawn here, and the element is the 48 dp row
// the map measures (the slider itself lays out at its thumb's height). That row carries the slider's semantics, so a tag
// on it finds the control and a screen reader names it.
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RigCheckSlider(
    value: Float,
    onValueChange: (Float) -> Unit,
    valueRange: ClosedFloatingPointRange<Float>,
    steps: Int,
    contentDescription: String,
    modifier: Modifier = Modifier,
) {
    val source = remember { MutableInteractionSource() }
    val dragged by source.collectIsDraggedAsState()
    val pressed by source.collectIsPressedAsState()
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier.fillMaxWidth().height(Sizes.TouchTargetMin).semantics(mergeDescendants = true) {
            this.contentDescription = contentDescription
        },
    ) {
        Slider(
            value = value,
            onValueChange = onValueChange,
            valueRange = valueRange,
            steps = steps,
            interactionSource = source,
            thumb = {
                Box(
                    modifier = Modifier
                        .size(if (dragged || pressed) PRESSED_THUMB else Sizes.SliderThumb)
                        .background(SurfaceWhite, CircleShape)
                        .border(3.dp, TealDeep, CircleShape),
                )
            },
            track = { state ->
                val fraction = (state.value - valueRange.start) / (valueRange.endInclusive - valueRange.start)
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .drawBehind {
                            // The thumb's centre runs from half a thumb in from each end; the fill stops there.
                            val half = Sizes.SliderThumb.toPx() / 2
                            val end = half + fraction * (size.width - 2 * half)
                            val round = CornerRadius(size.height / 2)
                            drawRoundRect(Border, cornerRadius = round)
                            drawRoundRect(TealDeep, size = Size(end, size.height), cornerRadius = round)
                        },
                )
            },
        )
    }
}
