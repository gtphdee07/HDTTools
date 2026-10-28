package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.OrangeDeep
import com.rigcheck.app.ui.theme.PurpleDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintOrange
import com.rigcheck.app.ui.theme.TintPurple
import com.rigcheck.app.ui.theme.TintTeal
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** The avatar's tint and the colour of its initial. They cycle teal, purple, orange by the card's index. */
data class RigCardAvatarColors(val fill: Color, val initial: Color)

fun rigCardAvatarColors(index: Int): RigCardAvatarColors = when (index.mod(3)) {
    0 -> RigCardAvatarColors(TintTeal, TealDeep)
    1 -> RigCardAvatarColors(TintPurple, PurpleDeep)
    else -> RigCardAvatarColors(TintOrange, OrangeDeep)
}

// components.md, "Rig card": at least 84 dp high, 14 dp radius, a 1 dp border, shadow sm. The card has no padding of
// its own. The body (left of a 1 dp divider) is the only part that starts a check; the delete bin on the right is a
// sibling with its own 48 dp hit area, so the two ripples and taps never overlap. The bin is left out when
// `onDelete` is null (signed out: the Rigs kept on the phone cannot be deleted) and disabled while a delete runs.
@Composable
fun RigCheckRigCard(
    nickname: String,
    subtitle: String,
    lastChecked: String?,
    index: Int,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    onDelete: (() -> Unit)? = null,
    deleteEnabled: Boolean = true,
    bodyModifier: Modifier = Modifier,
    deleteModifier: Modifier = Modifier,
) {
    val source = remember { MutableInteractionSource() }
    val focused by source.collectIsFocusedAsState()
    val avatar = rigCardAvatarColors(index)
    Surface(
        shape = RoundedCornerShape(Radii.Card),
        color = SurfaceWhite,
        border = BorderStroke(1.dp, Border),
        shadowElevation = Elevations.Sm,
        modifier = modifier.fillMaxWidth().heightIn(min = 84.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = bodyModifier
                    .weight(1f)
                    .heightIn(min = 84.dp)
                    .focusRing(focused, cornerRadius = Radii.Card)
                    .clickable(interactionSource = source, indication = ripple(), role = Role.Button, onClick = onClick)
                    .padding(start = 16.dp, top = 8.dp, end = 12.dp, bottom = 8.dp),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier.size(52.dp).background(avatar.fill, CircleShape),
                ) {
                    Text(
                        nickname.trim().take(1).uppercase(),
                        style = RigCheckStyles.heading.copy(fontSize = 22.sp, lineHeight = 26.sp),
                        color = avatar.initial,
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        nickname,
                        style = RigCheckStyles.title,
                        color = Ink,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(subtitle, style = RigCheckStyles.bodySm, color = InkMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (lastChecked != null) {
                        Text(lastChecked, style = RigCheckStyles.micro.copy(fontWeight = FontWeight.Medium), color = InkMuted)
                    }
                }
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = InkMuted)
            }
            if (onDelete != null) {
                Box(modifier = Modifier.width(1.dp).height(40.dp).background(Border))
                RigCheckIconButton(
                    icon = Icons.Filled.Delete,
                    contentDescription = "Delete $nickname",
                    onClick = onDelete,
                    enabled = deleteEnabled,
                    modifier = deleteModifier.padding(end = 4.dp),
                )
            }
        }
    }
}
