package com.rigcheck.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.RigCheckBadge
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckButtonKind
import com.rigcheck.app.ui.components.RigCheckButtonSize
import com.rigcheck.app.ui.components.RigCheckEmptyState
import com.rigcheck.app.ui.components.RigCheckLogo
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.components.rigCheckVerdictLook
import com.rigcheck.app.ui.historyBadgeKind
import com.rigcheck.app.ui.historyDateText
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite
import com.rigcheck.app.ui.verdictBadgeFor

// The account's past checks, newest first (web/src/screens/History.tsx), on the design's skeleton (resize-rules.md,
// "What scrolls and what is pinned"): the top bar (Back and the title) is pinned, and the subtitle, the notice and the
// entries scroll as one list. `limitNotice` is given to a Free account whose History is full, with a way to Pro.
// Nothing is pinned at the bottom: the screen has no action of its own.
@Composable
fun HistoryScreen(
    entries: List<HistoryEntry>,
    limitNotice: String? = null,
    onUpgrade: () -> Unit = {},
    onBack: () -> Unit = {},
) {
    Column(modifier = Modifier.fillMaxSize()) {
        RigCheckTopBar(
            title = "Check History",
            onBack = onBack,
            titleModifier = Modifier.testTag(UiTags.HISTORY_TITLE),
            backModifier = Modifier.testTag(UiTags.HISTORY_BACK),
        )
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(10.dp),
            contentPadding = PaddingValues(start = 16.dp, top = 20.dp, end = 16.dp, bottom = 24.dp),
            modifier = Modifier.weight(1f).fillMaxWidth(),
        ) {
            // The frames put 16 dp between the subtitle and what follows it and between the notice block and the entries;
            // the list's own gap is 10, the gap between two entries.
            item {
                Text(
                    "Every check you have run and where you stood.",
                    style = RigCheckStyles.body,
                    color = InkMuted,
                    modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp).testTag(UiTags.HISTORY_SUBTITLE),
                )
            }
            if (limitNotice != null) {
                item { LimitNoticeBlock(limitNotice, onUpgrade) }
            }
            if (entries.isEmpty()) {
                item {
                    RigCheckEmptyState(
                        title = null,
                        text = "No checks yet. Finish a check and it will be listed here.",
                        mark = { RigCheckLogo() },
                        textModifier = Modifier.testTag(UiTags.HISTORY_EMPTY),
                    )
                }
            } else {
                items(entries, key = { it.id }) { entry -> HistoryEntryCard(entry) }
            }
        }
    }
}

// What each plan keeps, then Upgrade to Pro in a ghost button under the notice (the frame history__limit_notice).
@Composable
private fun LimitNoticeBlock(limitNotice: String, onUpgrade: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.padding(bottom = 6.dp)) {
        RigCheckNoticeCard(
            text = limitNotice,
            tone = RigCheckNoticeTone.Info,
            modifier = Modifier.testTag(UiTags.HISTORY_LIMIT_NOTICE),
        )
        RigCheckButton(
            text = "Upgrade to Pro",
            onClick = onUpgrade,
            kind = RigCheckButtonKind.Ghost,
            size = RigCheckButtonSize.Compact,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.HISTORY_UPGRADE),
        )
    }
}

// components.md, "Card" as the Rig card draws it (14 dp radius, a 1 dp border, shadow sm), 16 dp inside: the Rig's name
// over the day at the left and the verdict as a pill badge at the right. The verdict is said in words and an icon, never
// by the badge's colour alone. Read-only: the entry has no tap action.
@Composable
private fun HistoryEntryCard(entry: HistoryEntry) {
    val kind = historyBadgeKind(entry.verdict)
    val name: @Composable () -> Unit = {
        Text(
            entry.rigNickname,
            style = RigCheckStyles.title,
            color = Ink,
            modifier = Modifier.testTag(UiTags.HISTORY_ENTRY_RIG),
        )
        Text(
            historyDateText(entry.checkedAt),
            style = RigCheckStyles.caption,
            color = InkMuted,
            modifier = Modifier.testTag(UiTags.HISTORY_ENTRY_DATE),
        )
    }
    val pill: @Composable () -> Unit = {
        RigCheckBadge(
            text = verdictBadgeFor(entry.verdict).label,
            kind = kind,
            icon = rigCheckVerdictLook(entry.verdict).icon,
            modifier = Modifier.testTag(UiTags.HISTORY_ENTRY_VERDICT),
        )
    }
    Surface(
        shape = RoundedCornerShape(Radii.Card),
        color = SurfaceWhite,
        border = BorderStroke(1.dp, Border),
        shadowElevation = Elevations.Sm,
        modifier = Modifier.fillMaxWidth().testTag(UiTags.HISTORY_ENTRY),
    ) {
        if (LocalDensity.current.fontScale >= BADGE_BELOW_FROM_FONT_SCALE) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(16.dp)) {
                Column { name() }
                pill()
            }
        } else {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.padding(16.dp),
            ) {
                Column(modifier = Modifier.weight(1f)) { name() }
                pill()
            }
        }
    }
}

// From this font scale the pill goes on a line of its own under the name and the day, as a Results row's badge does
// (RigCheckBreakdownRow): a long verdict ("Partially Checked") would otherwise leave the name a letter a line.
private const val BADGE_BELOW_FROM_FONT_SCALE = 1.6f
