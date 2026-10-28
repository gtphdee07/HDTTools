package com.rigcheck.app.ui.components

import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Info
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.format.formatLb
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Motion
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.SurfaceSunken
import com.rigcheck.app.ui.theme.TintRed
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** What a row shows for its tone: the icon, the badge words and kind, the bar colour and the percentage colour. */
data class RigCheckRowLook(
    val icon: ImageVector,
    val badgeText: String,
    val badgeKind: RigCheckBadgeKind,
    val progress: RigCheckProgressTone,
    val percent: Color,
    val noteFill: Color,
)

// Pass, fail and not checked each differ in icon and in words, so a failing row is never drawn in colour alone.
fun rigCheckRowLook(tone: Tone): RigCheckRowLook = when (tone) {
    Tone.SUCCESS -> RigCheckRowLook(
        Icons.Filled.CheckCircle, "Within limit", RigCheckBadgeKind.WithinLimit, RigCheckProgressTone.Pass, Ink, SurfaceSunken,
    )
    Tone.WARNING -> RigCheckRowLook(
        Icons.Filled.Cancel, "Over limit", RigCheckBadgeKind.OverLimit, RigCheckProgressTone.Fail, DangerText, TintRed,
    )
    Tone.INSUFFICIENT -> RigCheckRowLook(
        Icons.Filled.Info, "Not checked", RigCheckBadgeKind.NotChecked, RigCheckProgressTone.NotChecked, Ink, SurfaceSunken,
    )
}

// components.md, "Breakdown row": the status icon (26 dp), the label (Outfit 700 17), the status badge and, only when
// the row has a note, a chevron (a 48 dp target); under them a 10 dp progress bar, then "A lb of B lb" at the left
// and the percentage at the right. A fill over 100% stops at the end of the bar. Expanded, the note shows in a
// block under the row, with a 200 ms expand.
@Composable
fun RigCheckBreakdownRow(
    item: BreakdownItem,
    modifier: Modifier = Modifier,
    startExpanded: Boolean = false,
) {
    var expanded by remember { mutableStateOf(startExpanded) }
    val look = rigCheckRowLook(item.tone)
    val hasNote = item.note != null
    Surface(
        shape = RoundedCornerShape(Radii.Card),
        color = SurfaceWhite,
        border = BorderStroke(1.dp, if (item.tone == Tone.WARNING) look.percent else Border),
        modifier = modifier.fillMaxWidth().testTag(UiTags.RESULTS_ROW),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .padding(start = 14.dp, top = 12.dp, end = if (hasNote) 6.dp else 14.dp, bottom = 12.dp)
                .animateContentSize(tween(Motion.MediumMs, easing = CubicBezierEasing(0.2f, 0f, 0f, 1f))),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(
                    look.icon,
                    contentDescription = null,
                    tint = rigCheckProgressFill(look.progress),
                    modifier = Modifier.size(Sizes.RowStatusIcon).testTag(UiTags.RESULTS_ROW_ICON),
                )
                Text(
                    item.label,
                    style = RigCheckStyles.titleSm.copy(fontSize = 17.sp),
                    color = Ink,
                    modifier = Modifier.weight(1f).testTag(UiTags.RESULTS_ROW_LABEL),
                )
                // The badge and the chevron are `results.row_badge` and `results.row_chevron` in the redesign map; their
                // tags join UiTags and the inventory when the Results re-skin (#194) puts this row on the screen.
                RigCheckBadge(look.badgeText, look.badgeKind)
                if (hasNote) {
                    RigCheckIconButton(
                        icon = if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                        contentDescription = if (expanded) "Hide note" else "Show note",
                        onClick = { expanded = !expanded },
                        glyphTint = InkMuted,
                    )
                }
            }
            RigCheckProgressBar(
                fraction = item.pct / 100f,
                tone = look.progress,
                modifier = Modifier.testTag(UiTags.RESULTS_ROW_BAR),
            )
            Row(modifier = Modifier.fillMaxWidth().padding(end = if (hasNote) 8.dp else 0.dp)) {
                Text(
                    "${formatLb(item.actual)} of ${formatLb(item.limit)}",
                    style = RigCheckStyles.bodySm,
                    color = InkMuted,
                    modifier = Modifier.weight(1f).testTag(UiTags.RESULTS_ROW_VALUES),
                )
                Text(
                    "${item.pct}%",
                    style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Bold),
                    color = look.percent,
                    modifier = Modifier.testTag(UiTags.RESULTS_ROW_PCT),
                )
            }
            if (expanded && item.note != null) {
                Surface(
                    shape = RoundedCornerShape(Radii.Input),
                    color = look.noteFill,
                    modifier = Modifier.fillMaxWidth().padding(end = 8.dp),
                ) {
                    Text(
                        item.note,
                        style = RigCheckStyles.bodySm,
                        color = Ink,
                        modifier = Modifier.padding(12.dp).testTag(UiTags.RESULTS_ROW_NOTE),
                    )
                }
            }
        }
    }
}
