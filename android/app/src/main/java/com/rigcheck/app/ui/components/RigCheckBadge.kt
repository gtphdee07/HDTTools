package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.BorderStrong
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Pine
import com.rigcheck.app.ui.theme.Purple
import com.rigcheck.app.ui.theme.PurpleDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintGreen
import com.rigcheck.app.ui.theme.TintPurple
import com.rigcheck.app.ui.theme.TintRed
import com.rigcheck.app.ui.theme.TintTeal
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** The seven badge kinds of components.md, "Badge". */
enum class RigCheckBadgeKind { Credit, Free, WithinLimit, OverLimit, PartiallyChecked, NotChecked, Plan }

data class RigCheckBadgeColors(val container: Color, val content: Color, val border: Color?)

fun rigCheckBadgeColors(kind: RigCheckBadgeKind): RigCheckBadgeColors = when (kind) {
    RigCheckBadgeKind.Credit -> RigCheckBadgeColors(Purple, SurfaceWhite, null)
    RigCheckBadgeKind.Free -> RigCheckBadgeColors(Pine, SurfaceWhite, null)
    RigCheckBadgeKind.WithinLimit -> RigCheckBadgeColors(TintGreen, Pine, null)
    RigCheckBadgeKind.OverLimit -> RigCheckBadgeColors(TintRed, DangerText, null)
    RigCheckBadgeKind.PartiallyChecked -> RigCheckBadgeColors(TintPurple, PurpleDeep, null)
    RigCheckBadgeKind.NotChecked -> RigCheckBadgeColors(SurfaceSunken, InkMuted, BorderStrong)
    RigCheckBadgeKind.Plan -> RigCheckBadgeColors(TintTeal, TealDeep, null)
}

// A pill with the `badge` text, 2 x 10 dp padding and an optional 14 dp icon. Not interactive. The status is always
// said in words, never by colour alone (copy-changes.md: "Within limit" / "Over limit" / "Not checked").
@Composable
fun RigCheckBadge(
    text: String,
    kind: RigCheckBadgeKind,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
) {
    val colors = rigCheckBadgeColors(kind)
    Surface(
        shape = RoundedCornerShape(Radii.Pill),
        color = colors.container,
        contentColor = colors.content,
        border = colors.border?.let { BorderStroke(1.dp, it) },
        modifier = modifier,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp),
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 2.dp),
        ) {
            if (icon != null) Icon(icon, contentDescription = null, modifier = Modifier.size(14.dp), tint = colors.content)
            Text(text, style = RigCheckStyles.badge, color = colors.content)
        }
    }
}
