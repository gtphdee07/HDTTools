package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Orange

// The notice above an entry screen's fields after a Scan that was delivered but
// did not read everything (#120). Shows nothing when there is no text, so a
// screen can pass it whatever ScanNotice.textFor returns.
@Composable
fun ScanNoticeCard(text: String?, modifier: Modifier = Modifier) {
    if (text == null) return
    Text(
        text,
        style = MaterialTheme.typography.bodyMedium,
        modifier = modifier
            .fillMaxWidth()
            .background(Orange.copy(alpha = 0.12f), RoundedCornerShape(12.dp))
            .padding(16.dp)
            .testTag("scan_notice"),
    )
}
