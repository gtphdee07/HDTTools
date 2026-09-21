package com.rigcheck.app.ui.screens

import android.text.format.DateUtils
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.ui.components.CreditBalanceChip
import com.rigcheck.app.ui.theme.AvatarPalette
import java.time.Instant

@Composable
fun RigPickerScreen(
    recentRigs: List<RecentRig>,
    creditBalance: Int?,
    onSelectRecentRig: (RecentRig) -> Unit,
    onStartNewRig: (String) -> Unit,
    onOpenPaywall: () -> Unit,
) {
    var newRigNickname by remember { mutableStateOf("") }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.background)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "RigCheck",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.ExtraBold,
                modifier = Modifier.weight(1f),
            )
            CreditBalanceChip(balance = creditBalance, onClick = onOpenPaywall)
        }
        HorizontalDivider()

        Column(modifier = Modifier.padding(20.dp, 16.dp, 20.dp, 8.dp)) {
            Text("Which rig?", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
            Text(
                "Pick one you have checked before, or start a new one.",
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.padding(top = 4.dp),
            )
        }

        LazyColumn(
            modifier = Modifier.weight(1f).padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 8.dp),
        ) {
            itemsIndexed(recentRigs) { index, rig ->
                RecentRigCard(rig = rig, index = index, onClick = { onSelectRecentRig(rig) })
            }
        }

        Column(
            modifier = Modifier.padding(20.dp, 8.dp, 20.dp, 20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Or start a new rig", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextField(
                    value = newRigNickname,
                    onValueChange = { newRigNickname = it },
                    placeholder = { Text("Rig nickname") },
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
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
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
