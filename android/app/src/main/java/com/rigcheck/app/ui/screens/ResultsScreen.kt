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
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictInfo
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
) {
    val toneColor = when (verdict.tone) {
        Tone.SUCCESS -> Pine
        Tone.WARNING -> DangerRed
        Tone.INSUFFICIENT -> Purple
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.weight(1f).padding(20.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(rigNickname.ifBlank { "Rig" }, style = MaterialTheme.typography.titleLarge)
                    Text(LocalDate.now().format(DATE_FORMAT), style = MaterialTheme.typography.bodySmall)
                }
                Surface(
                    shape = RoundedCornerShape(999.dp),
                    border = BorderStroke(2.dp, toneColor),
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                    ) {
                        Icon(
                            imageVector = when (verdict.tone) {
                                Tone.SUCCESS -> Icons.Filled.CheckCircle
                                Tone.WARNING -> Icons.Filled.Warning
                                Tone.INSUFFICIENT -> Icons.Filled.Info
                            },
                            contentDescription = null,
                            tint = toneColor,
                            modifier = Modifier.padding(0.dp),
                        )
                        Text(verdict.headline, style = MaterialTheme.typography.labelLarge, color = toneColor)
                    }
                }
            }

            if (breakdown.any { it.estimated }) {
                Column(modifier = Modifier.padding(top = 16.dp)) {
                    EstimatedFiguresNotice()
                }
            }

            Surface(
                shape = RoundedCornerShape(20.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
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
                modifier = Modifier.padding(top = 16.dp),
            )
        }

        Button(
            onClick = onStartAnother,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp),
        ) { Text("Start another check") }
    }
}
