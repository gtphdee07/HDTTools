package com.rigcheck.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Icon
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.OnTealWash
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.Surface
import com.rigcheck.app.ui.theme.Teal

/** The fill behind and the colour of the glyph of an icon button; [wash] is laid over the teal bar. */
data class RigCheckIconButtonColors(val container: Color, val icon: Color, val behind: Color)

/** Over the teal bar: a 72% white wash with an ink glyph. Elsewhere: no fill and a muted glyph. */
fun rigCheckIconButtonColors(onTeal: Boolean): RigCheckIconButtonColors =
    if (onTeal) {
        RigCheckIconButtonColors(container = OnTealWash, icon = Ink, behind = Teal)
    } else {
        RigCheckIconButtonColors(container = Color.Transparent, icon = InkMuted, behind = Surface)
    }

// components.md, "Icon button (48)": a 48 x 48 circle, 24 dp glyph, pressed ripple, disabled at 38%, a focus ring.
// Every one needs a content description.
@Composable
fun RigCheckIconButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    onTeal: Boolean = false,
    glyphTint: Color? = null,
) {
    val colors = rigCheckIconButtonColors(onTeal)
    val source = remember { MutableInteractionSource() }
    val focused by source.collectIsFocusedAsState()
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(Sizes.IconButton)
            .alpha(if (enabled) 1f else Opacity.Disabled)
            .focusRing(focused, cornerRadius = Sizes.IconButton / 2)
            .clip(CircleShape)
            .drawBehind { drawRect(colors.container) }
            .semantics { this.contentDescription = contentDescription }
            .clickable(enabled = enabled, role = Role.Button, interactionSource = source, indication = ripple(), onClick = onClick),
    ) {
        Icon(icon, contentDescription = null, tint = glyphTint ?: colors.icon, modifier = Modifier.size(24.dp))
    }
}
