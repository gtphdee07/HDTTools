package com.rigcheck.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
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
import com.rigcheck.app.ui.theme.DuskMauve
import com.rigcheck.app.ui.theme.TrailGreen

@Composable
fun ResultsScreen(breakdown: List<BreakdownItem>, verdict: VerdictInfo) {
    val toneColor = when (verdict.tone) {
        Tone.SUCCESS -> TrailGreen
        Tone.WARNING -> DangerRed
        Tone.INSUFFICIENT -> DuskMauve
    }

    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        Text("Results", style = MaterialTheme.typography.headlineMedium)

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 16.dp)
                .background(toneColor.copy(alpha = 0.12f), RoundedCornerShape(14.dp))
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = when (verdict.tone) {
                    Tone.SUCCESS -> Icons.Filled.CheckCircle
                    Tone.WARNING -> Icons.Filled.Warning
                    Tone.INSUFFICIENT -> Icons.Filled.Info
                },
                contentDescription = null,
                tint = toneColor,
                modifier = Modifier.size(36.dp),
            )
            Column(modifier = Modifier.padding(start = 16.dp)) {
                Text(verdict.headline, style = MaterialTheme.typography.titleLarge, color = toneColor)
                Text(verdict.subline, style = MaterialTheme.typography.bodyMedium)
            }
        }

        if (breakdown.any { it.estimated }) {
            Column(modifier = Modifier.padding(bottom = 16.dp)) {
                EstimatedFiguresNotice()
            }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items(breakdown) { item -> BreakdownRow(item) }
        }
    }
}
