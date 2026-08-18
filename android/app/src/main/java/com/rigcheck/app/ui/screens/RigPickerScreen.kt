package com.rigcheck.app.ui.screens

import android.text.format.DateUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.ui.theme.AvatarPalette
import com.rigcheck.app.ui.theme.DuskMauve
import com.rigcheck.app.ui.theme.SunsetOrange
import com.rigcheck.app.ui.theme.SunsetRose
import java.time.Instant

@Composable
fun RigPickerScreen(
    recentRigs: List<RecentRig>,
    onSelectRecentRig: (RecentRig) -> Unit,
    onStartNewRig: (String) -> Unit,
) {
    var newRigNickname by remember { mutableStateOf("") }

    Column(modifier = Modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        0f to SunsetRose,
                        0.55f to DuskMauve,
                        1f to SunsetOrange,
                    ),
                )
                .padding(20.dp),
        ) {
            Column {
                Text("RigCheck", style = MaterialTheme.typography.headlineMedium, color = Color.White)
                Text(
                    "Wandering Trails, Wagging Tails",
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.White,
                )
            }
        }

        Column(modifier = Modifier.padding(16.dp)) {
            Text("Pick a rig to weigh in", style = MaterialTheme.typography.bodyLarge)
        }

        LazyColumn(
            modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            itemsIndexed(recentRigs) { index, rig ->
                RecentRigCard(rig = rig, index = index, onClick = { onSelectRecentRig(rig) })
            }
        }

        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Or start a new rig", style = MaterialTheme.typography.bodyLarge)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextField(
                    value = newRigNickname,
                    onValueChange = { newRigNickname = it },
                    placeholder = { Text("Rig nickname (e.g. Big Blue)") },
                    modifier = Modifier.weight(1f),
                )
                Button(
                    onClick = { onStartNewRig(newRigNickname.trim()) },
                    enabled = newRigNickname.isNotBlank(),
                ) { Text("Create") }
            }
        }
    }
}

@Composable
private fun RecentRigCard(rig: RecentRig, index: Int, onClick: () -> Unit) {
    val avatarColor = AvatarPalette[index % AvatarPalette.size]
    val subtitle = listOfNotNull(rig.truck.description, rig.trailer.description)
        .filter { it.isNotBlank() }
        .joinToString(" · ")
    val relativeTime = remember(rig.lastUsedAt) {
        runCatching {
            DateUtils.getRelativeTimeSpanString(
                Instant.parse(rig.lastUsedAt).toEpochMilli(),
                System.currentTimeMillis(),
                DateUtils.MINUTE_IN_MILLIS,
            ).toString()
        }.getOrDefault("")
    }

    Surface(
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier.size(44.dp).background(avatarColor, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    rig.nickname.take(1).uppercase(),
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                )
            }
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text(rig.nickname, style = MaterialTheme.typography.titleMedium)
                if (subtitle.isNotBlank()) {
                    Text(subtitle, style = MaterialTheme.typography.bodySmall)
                }
                if (relativeTime.isNotBlank()) {
                    Text("Last checked $relativeTime", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}
