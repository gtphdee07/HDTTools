package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.PurpleDeep

// components.md: "Focus (keyboard or switch access): 2 dp purple-deep outline with a 2 dp offset, on every
// surface." Drawn outside the control's bounds so it never changes the control's size.
fun Modifier.focusRing(focused: Boolean, cornerRadius: Dp): Modifier =
    if (!focused) {
        this
    } else {
        drawBehind {
            val outset = 3.dp.toPx() // 2 dp offset plus half the 2 dp stroke
            drawRoundRect(
                color = PurpleDeep,
                topLeft = Offset(-outset, -outset),
                size = Size(size.width + 2 * outset, size.height + 2 * outset),
                cornerRadius = CornerRadius(cornerRadius.toPx() + outset),
                style = Stroke(width = 2.dp.toPx()),
            )
        }
    }
