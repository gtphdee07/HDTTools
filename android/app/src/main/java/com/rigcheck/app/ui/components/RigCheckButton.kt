package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.DisabledContent
import com.rigcheck.app.ui.theme.DisabledFill
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Orange
import com.rigcheck.app.ui.theme.OrangeDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintRed
import com.rigcheck.app.ui.theme.TintTeal
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

enum class RigCheckButtonKind { Primary, Secondary, Ghost, Destructive }

/** Regular 56 dp, compact 48 dp (hugs its label), and 52 dp inside a dialog. */
enum class RigCheckButtonSize(val height: Dp) {
    Regular(Sizes.Button),
    Compact(Sizes.ButtonCompact),
    Dialog(Sizes.ButtonInDialog),
}

enum class RigCheckButtonState { Default, Pressed, Disabled }

/** A button's fill, its text colour and its border, for one kind in one state (components.md, "Button"). */
data class RigCheckButtonColors(val container: Color, val content: Color, val border: Color?)

fun rigCheckButtonColors(kind: RigCheckButtonKind, state: RigCheckButtonState): RigCheckButtonColors {
    if (state == RigCheckButtonState.Disabled) return RigCheckButtonColors(DisabledFill, DisabledContent, null)
    val pressed = state == RigCheckButtonState.Pressed
    return when (kind) {
        RigCheckButtonKind.Primary ->
            if (pressed) RigCheckButtonColors(OrangeDeep, SurfaceWhite, null) else RigCheckButtonColors(Orange, Ink, null)
        RigCheckButtonKind.Secondary ->
            RigCheckButtonColors(if (pressed) TintTeal else SurfaceWhite, TealDeep, TealDeep)
        RigCheckButtonKind.Ghost ->
            RigCheckButtonColors(if (pressed) TintTeal else Color.Transparent, TealDeep, null)
        RigCheckButtonKind.Destructive ->
            RigCheckButtonColors(if (pressed) TintRed else SurfaceWhite, if (pressed) DangerText else DangerRed, DangerRed)
    }
}

// components.md, "Button, primary / secondary / ghost / destructive": a pill, 20 dp side padding, the `button` text
// style (`button-compact` when compact), an optional 22 dp icon with an 8 dp gap. Full width unless compact. One
// primary per screen. Pressed swaps the fill; focus draws the purple-deep ring.
@Composable
fun RigCheckButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    kind: RigCheckButtonKind = RigCheckButtonKind.Primary,
    size: RigCheckButtonSize = RigCheckButtonSize.Regular,
    enabled: Boolean = true,
    icon: ImageVector? = null,
) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val focused by source.collectIsFocusedAsState()
    val state = when {
        !enabled -> RigCheckButtonState.Disabled
        pressed -> RigCheckButtonState.Pressed
        else -> RigCheckButtonState.Default
    }
    val colors = rigCheckButtonColors(kind, state)
    val shape = RoundedCornerShape(Radii.Pill)
    val width = if (size == RigCheckButtonSize.Compact) Modifier else Modifier.fillMaxWidth()
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = shape,
        color = colors.container,
        contentColor = colors.content,
        border = colors.border?.let { BorderStroke(1.5.dp, it) },
        shadowElevation = if (kind == RigCheckButtonKind.Primary && enabled) Elevations.Sm else 0.dp,
        interactionSource = source,
        modifier = modifier.then(width).heightIn(min = size.height).focusRing(focused, cornerRadius = size.height / 2),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
            modifier = Modifier.heightIn(min = size.height).padding(horizontal = 20.dp),
        ) {
            if (icon != null) Icon(icon, contentDescription = null, modifier = Modifier.size(22.dp), tint = colors.content)
            val style = if (size == RigCheckButtonSize.Compact) RigCheckStyles.buttonCompact else RigCheckStyles.button
            Text(text, style = style, color = colors.content)
        }
    }
}
