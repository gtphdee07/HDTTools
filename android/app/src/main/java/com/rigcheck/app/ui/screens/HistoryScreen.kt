package com.rigcheck.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.historyDateText
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.Pine
import com.rigcheck.app.ui.theme.Purple
import com.rigcheck.app.ui.verdictBadgeFor

// The account's past checks, newest first (web/src/screens/History.tsx). `limitNotice` is given to a Free
// account whose History is full, with a way to Pro.
@Composable
fun HistoryScreen(
    entries: List<HistoryEntry>,
    limitNotice: String? = null,
    onUpgrade: () -> Unit = {},
) {
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 16.dp)) {
        Text(
            "Check History",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.ExtraBold,
            modifier = Modifier.testTag(UiTags.HISTORY_TITLE),
        )
        Text(
            "Every check you have run and where you stood.",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 4.dp, bottom = 16.dp).testTag(UiTags.HISTORY_SUBTITLE),
        )

        if (limitNotice != null) {
            Surface(
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp).testTag(UiTags.HISTORY_LIMIT_NOTICE),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(limitNotice, style = MaterialTheme.typography.bodyMedium)
                    TextButton(onClick = onUpgrade, modifier = Modifier.testTag(UiTags.HISTORY_UPGRADE)) {
                        Text("Upgrade to Pro")
                    }
                }
            }
        }

        if (entries.isEmpty()) {
            Text(
                "No checks yet. Finish a check and it will be listed here.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.testTag(UiTags.HISTORY_EMPTY),
            )
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.weight(1f)) {
                items(entries, key = { it.id }) { entry -> HistoryEntryCard(entry) }
            }
        }
    }
}

@Composable
private fun HistoryEntryCard(entry: HistoryEntry) {
    val badge = verdictBadgeFor(entry.verdict)
    val toneColor = when (badge.tone) {
        Tone.SUCCESS -> Pine
        Tone.WARNING -> DangerRed
        Tone.INSUFFICIENT -> Purple
    }
    Surface(
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth().testTag(UiTags.HISTORY_ENTRY),
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    entry.rigNickname,
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.testTag(UiTags.HISTORY_ENTRY_RIG),
                )
                Text(
                    historyDateText(entry.checkedAt),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.testTag(UiTags.HISTORY_ENTRY_DATE),
                )
            }
            Text(
                badge.label,
                style = MaterialTheme.typography.labelLarge,
                color = toneColor,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.testTag(UiTags.HISTORY_ENTRY_VERDICT),
            )
        }
    }
}
