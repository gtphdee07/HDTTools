package com.rigcheck.app.ui.components

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.ui.format.formatLb
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.DuskMauve
import com.rigcheck.app.ui.theme.TrailGreen

private fun toneColorFor(tone: Tone) = when (tone) {
    Tone.SUCCESS -> TrailGreen
    Tone.WARNING -> DangerRed
    Tone.INSUFFICIENT -> DuskMauve
}

@Composable
fun BreakdownRow(item: BreakdownItem, modifier: Modifier = Modifier) {
    var expanded by remember { mutableStateOf(false) }
    val toneColor = toneColorFor(item.tone)

    Surface(
        shape = RoundedCornerShape(14.dp),
        border = if (item.tone == Tone.WARNING) BorderStroke(1.dp, DangerRed) else null,
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize()
            .clickable(enabled = item.note != null) { expanded = !expanded },
    ) {
        Column(modifier = Modifier.padding(14.dp, 12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = when (item.tone) {
                        Tone.SUCCESS -> Icons.Filled.CheckCircle
                        Tone.WARNING -> Icons.Filled.Cancel
                        Tone.INSUFFICIENT -> Icons.Filled.Info
                    },
                    contentDescription = null,
                    tint = toneColor,
                    modifier = Modifier.size(28.dp),
                )
                Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                    Text(item.label, style = MaterialTheme.typography.titleSmall)
                    Text(
                        "${formatLb(item.actual)} of ${formatLb(item.limit)}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text(
                    "${item.pct}%",
                    style = MaterialTheme.typography.titleMedium,
                    color = toneColor,
                )
            }
            LinearProgressIndicator(
                progress = { (item.pct.coerceIn(0, 100)) / 100f },
                color = toneColor,
                // Explicit, tone-matching track color - Material3's default
                // track color is theme-derived, not based on the `color`
                // param, so it stayed a fixed green regardless of tone.
                // Invisible for a normal passing/failing row (mostly
                // covered by the filled portion) but every insufficient
                // row is 0% (all track, no fill), which made this bug
                // impossible to miss on a real device.
                trackColor = toneColor.copy(alpha = 0.2f),
                modifier = Modifier
                    .padding(top = 8.dp)
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
            )
            if (expanded && item.note != null) {
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                Text(item.note, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
