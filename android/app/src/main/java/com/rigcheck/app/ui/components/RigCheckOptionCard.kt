package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.Purple
import com.rigcheck.app.ui.theme.PurpleDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Teal
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintPurple
import com.rigcheck.app.ui.theme.TintTeal
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** Scan Photo (purple) and Enter Manually (teal): the same size, so Manual is a first-class path. */
enum class RigCheckOptionKind { Scan, Manual }

data class RigCheckOptionColors(
    val container: Color,
    val border: Color,
    val iconCircle: Color,
    val icon: Color,
    val title: Color,
    val description: Color,
)

fun rigCheckOptionColors(kind: RigCheckOptionKind): RigCheckOptionColors = when (kind) {
    RigCheckOptionKind.Scan -> RigCheckOptionColors(TintPurple, PurpleDeep, Purple, SurfaceWhite, Ink, InkMuted)
    RigCheckOptionKind.Manual -> RigCheckOptionColors(TintTeal, TealDeep, Teal, Ink, Ink, InkMuted)
}

// components.md, "Option card": at least 148 dp high, 24 dp radius, 1.5 dp border, the tint fill, shadow sm, a 64 dp
// circle with the icon at the left, the title (20/24 Outfit 700) with an optional badge beside it, then the
// description in `body-md` ink-muted. A balance of 0 changes nothing visually: the Scan card still opens the Paywall.
@Composable
fun RigCheckOptionCard(
    kind: RigCheckOptionKind,
    title: String,
    description: String,
    icon: ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    badge: (@Composable () -> Unit)? = null,
) {
    val colors = rigCheckOptionColors(kind)
    val source = remember { MutableInteractionSource() }
    val focused by source.collectIsFocusedAsState()
    val shape = RoundedCornerShape(Radii.Panel)
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = shape,
        color = colors.container,
        border = BorderStroke(1.5.dp, colors.border),
        shadowElevation = Elevations.Sm,
        interactionSource = source,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 148.dp)
            .alpha(if (enabled) 1f else Opacity.Disabled)
            .focusRing(focused, cornerRadius = Radii.Panel),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier.padding(20.dp),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(64.dp).background(colors.iconCircle, CircleShape),
            ) {
                Icon(icon, contentDescription = null, tint = colors.icon, modifier = Modifier.size(32.dp))
            }
            Column(verticalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        title,
                        style = RigCheckStyles.titleLg.copy(fontSize = 20.sp, lineHeight = 24.sp),
                        color = colors.title,
                        modifier = Modifier.weight(1f, fill = false),
                    )
                    if (badge != null) badge()
                }
                Text(description, style = RigCheckStyles.bodyMd, color = colors.description, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}
