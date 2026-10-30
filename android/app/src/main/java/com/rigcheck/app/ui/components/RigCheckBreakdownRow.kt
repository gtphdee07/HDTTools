package com.rigcheck.app.ui.components

import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.outlined.Cancel
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.format.formatLb
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Motion
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.SurfaceSunken

/** What a row shows for its tone: the icon (in the row and in the badge), the badge words and kind, the bar colour and the percentage colour. */
data class RigCheckRowLook(
    val icon: ImageVector,
    val badgeText: String,
    val badgeKind: RigCheckBadgeKind,
    val progress: RigCheckProgressTone,
    val percent: Color,
)

// Pass, fail and not checked each differ in icon and in words, so a failing row is never drawn in colour alone.
fun rigCheckRowLook(tone: Tone): RigCheckRowLook = when (tone) {
    Tone.SUCCESS -> RigCheckRowLook(
        Icons.Outlined.CheckCircle, "Within limit", RigCheckBadgeKind.WithinLimit, RigCheckProgressTone.Pass, Ink,
    )
    Tone.WARNING -> RigCheckRowLook(
        Icons.Outlined.Cancel, "Over limit", RigCheckBadgeKind.OverLimit, RigCheckProgressTone.Fail, DangerText,
    )
    Tone.INSUFFICIENT -> RigCheckRowLook(
        Icons.Outlined.Info, "Not checked", RigCheckBadgeKind.NotChecked, RigCheckProgressTone.NotChecked, Ink,
    )
}

// resize-rules.md, "Font scale 2.0": the badge goes on a line of its own under the label. From 1.6, as the top bar's chip does.
private const val BADGE_BELOW_FROM_FONT_SCALE = 1.6f

// The row's side padding is the design's 16 dp; the vertical 16 and the 8 between the parts make a row of the map's ~104 dp.
private val RowSidePadding = 16.dp
private val RowVerticalPadding = 16.dp

// What the label line keeps free at its right for the chevron, whose 48 dp box reaches into the row's padding.
private val ChevronRoom = 42.dp
private val ChevronEdgeGap = 4.dp

// components.md, "Breakdown row": the status icon (26 dp), the label (Outfit 700 17), the status badge and, only when
// the row has a note, a chevron (a 48 dp target); under them a 10 dp progress bar, then "A lb of B lb" at the left
// and the percentage at the right. A fill over 100% stops at the end of the bar. Expanded, the note shows in a
// block under the row, with a 200 ms expand. The rows sit flat in the breakdown card, which draws what is between them.
//
// The chevron's 48 dp target is taller than the label line (26 dp), so it is laid over the row, centred on that line,
// rather than in the line: the frames' rows are as tall with a chevron as without one. Being a child of the whole
// row, it is inside the bounds its touches are checked against. The rest of the row is tappable too (a touch
// shortcut for the same toggle, with no second control for a screen reader: the chevron is the control).
@Composable
fun RigCheckBreakdownRow(
    item: BreakdownItem,
    modifier: Modifier = Modifier,
    startExpanded: Boolean = false,
) {
    var expanded by remember { mutableStateOf(startExpanded) }
    var labelLineHeightPx by remember { mutableIntStateOf(0) }
    val look = rigCheckRowLook(item.tone)
    val hasNote = item.note != null
    val badgeBelow = LocalDensity.current.fontScale >= BADGE_BELOW_FROM_FONT_SCALE
    val toggle = { expanded = !expanded }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .testTag(UiTags.RESULTS_ROW)
            .then(if (hasNote) Modifier.pointerInput(Unit) { detectTapGestures { toggle() } } else Modifier),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .padding(horizontal = RowSidePadding, vertical = RowVerticalPadding)
                .animateContentSize(tween(Motion.MediumMs, easing = CubicBezierEasing(0.2f, 0f, 0f, 1f))),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier
                    .padding(end = if (hasNote) ChevronRoom else 0.dp)
                    .onSizeChanged { labelLineHeightPx = it.height },
            ) {
                Icon(
                    look.icon,
                    contentDescription = null,
                    tint = rigCheckProgressFill(look.progress),
                    modifier = Modifier.size(Sizes.RowStatusIcon).testTag(UiTags.RESULTS_ROW_ICON),
                )
                val label: @Composable (Modifier) -> Unit = { placement ->
                    Text(
                        item.label,
                        style = RigCheckStyles.titleSm.copy(fontSize = 17.sp),
                        color = Ink,
                        modifier = placement.testTag(UiTags.RESULTS_ROW_LABEL),
                    )
                }
                val badge: @Composable (Modifier) -> Unit = { placement ->
                    RigCheckBadge(look.badgeText, look.badgeKind, icon = look.icon, modifier = placement.testTag(UiTags.RESULTS_ROW_BADGE))
                }
                if (badgeBelow) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.weight(1f)) {
                        label(Modifier)
                        badge(Modifier)
                    }
                } else {
                    label(Modifier.weight(1f))
                    badge(Modifier)
                }
            }
            RigCheckProgressBar(
                fraction = item.pct / 100f,
                tone = look.progress,
                modifier = Modifier.testTag(UiTags.RESULTS_ROW_BAR),
            )
            Row(modifier = Modifier.fillMaxWidth()) {
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
                // The map's `results.row_note` is the sunken block, not the words in it.
                Surface(
                    shape = RoundedCornerShape(Radii.Input),
                    color = SurfaceSunken,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.RESULTS_ROW_NOTE),
                ) {
                    Text(item.note, style = RigCheckStyles.bodySm, color = Ink, modifier = Modifier.padding(12.dp))
                }
            }
        }
        if (hasNote) {
            RigCheckIconButton(
                icon = if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                contentDescription = if (expanded) "Hide note" else "Show note",
                onClick = toggle,
                glyphTint = InkMuted,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(end = ChevronEdgeGap)
                    .offset { IntOffset(0, RowVerticalPadding.roundToPx() + (labelLineHeightPx - Sizes.IconButton.roundToPx()) / 2) }
                    .testTag(UiTags.RESULTS_ROW_CHEVRON),
            )
        }
    }
}
