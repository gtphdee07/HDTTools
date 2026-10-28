package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.theme.BorderStrong
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.DisabledContent
import com.rigcheck.app.ui.theme.DisabledFill
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintTeal
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

enum class RigCheckFieldState { Default, Focused, Error, Disabled }

/** The box of a field: its fill, the border colour and width, and the colour of the value and of the hint text. */
data class RigCheckFieldColors(
    val container: Color,
    val border: Color,
    val borderWidth: Dp,
    val value: Color,
    val hint: Color,
    val focusRing: Boolean,
)

fun rigCheckFieldColors(state: RigCheckFieldState): RigCheckFieldColors = when (state) {
    RigCheckFieldState.Default -> RigCheckFieldColors(SurfaceWhite, BorderStrong, 1.5.dp, Ink, InkMuted, false)
    RigCheckFieldState.Focused -> RigCheckFieldColors(SurfaceWhite, TealDeep, 2.dp, Ink, InkMuted, true)
    RigCheckFieldState.Error -> RigCheckFieldColors(SurfaceWhite, DangerRed, 2.dp, Ink, InkMuted, false)
    RigCheckFieldState.Disabled -> RigCheckFieldColors(DisabledFill, BorderStrong, 1.5.dp, DisabledContent, DisabledContent, false)
}

// components.md, "Text field (and number field with unit)": the label above, then a 56 dp box with a 1.5 dp
// border-strong outline, an 8 dp radius and 16 dp side padding; the value in `body` at 17 sp; a unit hint ("lb")
// right-aligned; an optional help line. Focused: 2 dp teal-deep border plus a 4 dp tint-teal ring. Error: a 2 dp
// danger border and a message line in danger-text; the message names the problem, so it is not colour alone.
// Disabled: the disabled fill at 70%. A number field is this with `numeric = true` and a `unit`.
@Composable
fun RigCheckTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    unit: String? = null,
    help: String? = null,
    error: String? = null,
    enabled: Boolean = true,
    numeric: Boolean = false,
    singleLine: Boolean = true,
    // For the tag and the other semantics of the input itself (focus, typing); `modifier` is for the whole field,
    // label and message included.
    inputModifier: Modifier = Modifier,
) {
    val source = remember { MutableInteractionSource() }
    val focused by source.collectIsFocusedAsState()
    val state = when {
        !enabled -> RigCheckFieldState.Disabled
        error != null -> RigCheckFieldState.Error
        focused -> RigCheckFieldState.Focused
        else -> RigCheckFieldState.Default
    }
    val colors = rigCheckFieldColors(state)
    val shape = RoundedCornerShape(Radii.Input)
    val valueStyle = RigCheckStyles.body.copy(fontSize = 17.sp, color = colors.value)

    Column(verticalArrangement = Arrangement.spacedBy(6.dp), modifier = modifier.fillMaxWidth()) {
        Text(label, style = RigCheckStyles.label, color = Ink)
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            enabled = enabled,
            singleLine = singleLine,
            textStyle = valueStyle,
            cursorBrush = SolidColor(TealDeep),
            keyboardOptions = KeyboardOptions(keyboardType = if (numeric) KeyboardType.Number else KeyboardType.Text),
            interactionSource = source,
            modifier = inputModifier
                .fillMaxWidth()
                .heightIn(min = Sizes.TextField)
                .drawBehind {
                    if (colors.focusRing) {
                        // The 4 dp tint-teal ring around the 2 dp border.
                        val ring = 4.dp.toPx()
                        drawRoundRect(
                            TintTeal,
                            topLeft = Offset(-ring, -ring),
                            size = Size(size.width + 2 * ring, size.height + 2 * ring),
                            cornerRadius = CornerRadius(Radii.Input.toPx() + ring),
                        )
                    }
                },
            decorationBox = { inner ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .heightIn(min = Sizes.TextField)
                        .background(colors.container.copy(alpha = if (enabled) 1f else Opacity.DisabledField), shape)
                        .border(BorderStroke(colors.borderWidth, colors.border), shape)
                        .padding(horizontal = 16.dp),
                ) {
                    Box(modifier = Modifier.weight(1f)) {
                        if (value.isEmpty() && placeholder != null) {
                            Text(placeholder, style = valueStyle, color = colors.hint)
                        }
                        inner()
                    }
                    if (unit != null) Text(unit, style = RigCheckStyles.bodyMd, color = colors.hint)
                }
            },
        )
        if (error != null) {
            Text(error, style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Medium), color = DangerText)
        } else if (help != null) {
            Text(help, style = RigCheckStyles.caption, color = InkMuted)
        }
    }
}
