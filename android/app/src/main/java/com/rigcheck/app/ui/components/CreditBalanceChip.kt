package com.rigcheck.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

// null balance = not loaded yet. Shown near every Scan Photo entry point,
// per ANDROID_DESIGN_BRIEF.md ("contextual, not a nav destination"). An
// optional onClick turns it into a "get more scans" affordance to the
// Paywall - the only other entry point besides tapping Scan Photo at 0
// credits.
@Composable
fun CreditBalanceChip(balance: Int?, modifier: Modifier = Modifier, onClick: (() -> Unit)? = null) {
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = MaterialTheme.colorScheme.secondaryContainer,
        modifier = if (onClick != null) modifier.clickable(onClick = onClick) else modifier,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
        ) {
            Icon(
                Icons.Filled.CameraAlt,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.onSecondaryContainer,
            )
            Text(
                if (balance == null) "…" else "$balance scan${if (balance == 1) "" else "s"}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSecondaryContainer,
            )
        }
    }
}
