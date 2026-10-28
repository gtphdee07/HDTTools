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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.ui.GarageNotice
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.BreakdownRow
import com.rigcheck.app.ui.components.EstimatedFiguresNotice
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.Pine
import com.rigcheck.app.ui.theme.Purple
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private val DATE_FORMAT = DateTimeFormatter.ofPattern("MMM d, yyyy")

@Composable
fun ResultsScreen(
    rigNickname: String,
    breakdown: List<BreakdownItem>,
    verdict: VerdictInfo,
    onStartAnother: () -> Unit,
    garageNotice: GarageNotice? = null,
    historyNotice: String? = null,
    onGetPro: () -> Unit = {},
) {
    val toneColor = when (verdict.tone) {
        Tone.SUCCESS -> Pine
        Tone.WARNING -> DangerRed
        Tone.INSUFFICIENT -> Purple
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.weight(1f).padding(20.dp)) {
            Text(
                rigNickname.ifBlank { "Rig" },
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.testTag(UiTags.RESULTS_RIG_NAME),
            )
            Text(
                LocalDate.now().format(DATE_FORMAT),
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.testTag(UiTags.RESULTS_DATE),
            )

            // The subline is a full sentence, so the verdict pill takes the whole row
            // rather than sharing it with the nickname.
            Surface(
                shape = RoundedCornerShape(20.dp),
                border = BorderStroke(2.dp, toneColor),
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp).testTag(UiTags.RESULTS_VERDICT),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                ) {
                    Icon(
                        imageVector = when (verdict.tone) {
                            Tone.SUCCESS -> Icons.Filled.CheckCircle
                            Tone.WARNING -> Icons.Filled.Warning
                            Tone.INSUFFICIENT -> Icons.Filled.Info
                        },
                        contentDescription = null,
                        tint = toneColor,
                    )
                    Column {
                        Text(verdict.headline, style = MaterialTheme.typography.labelLarge, color = toneColor)
                        Text(
                            verdict.subline,
                            style = MaterialTheme.typography.bodyMedium,
                            color = toneColor.copy(alpha = 0.9f),
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                }
            }

            if (garageNotice != null) {
                GarageNoticeCard(garageNotice, onGetPro)
            }

            if (historyNotice != null) {
                HistoryNoticeCard(historyNotice)
            }

            if (breakdown.any { it.estimated }) {
                Column(modifier = Modifier.padding(top = 16.dp)) {
                    EstimatedFiguresNotice()
                }
            }

            Surface(
                shape = RoundedCornerShape(20.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp).testTag(UiTags.RESULTS_BREAKDOWN_CARD),
            ) {
                LazyColumn(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(breakdown) { item -> BreakdownRow(item) }
                }
            }

            Text(
                "Experimental tool, not a certified safety decision.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 16.dp).testTag(UiTags.RESULTS_FOOTER_NOTE),
            )
        }

        Button(
            onClick = onStartAnother,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp)
                .testTag(UiTags.RESULTS_START_ANOTHER_BUTTON),
        ) { Text("Start another check") }
    }
}

// The check went ahead; only its History entry did not reach the account.
@Composable
private fun HistoryNoticeCard(message: String) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth().padding(top = 16.dp).testTag(UiTags.HISTORY_NOTICE),
    ) {
        Text(message, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(16.dp))
    }
}

// The check went ahead; only its Rig did not reach the Garage. A Free account with a full Garage is offered Pro.
@Composable
private fun GarageNoticeCard(notice: GarageNotice, onGetPro: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth().padding(top = 16.dp).testTag(UiTags.GARAGE_NOTICE),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(notice.message, style = MaterialTheme.typography.bodyMedium)
            if (notice.offerPro) {
                TextButton(onClick = onGetPro, modifier = Modifier.testTag(UiTags.GARAGE_NOTICE_GET_PRO)) {
                    Text("Get Pro for a bigger Garage")
                }
            }
        }
    }
}
