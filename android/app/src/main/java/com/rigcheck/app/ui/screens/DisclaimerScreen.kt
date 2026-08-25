package com.rigcheck.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.DangerRed

// Exact wording finalized 2026-08-17 (ANDROID_DESIGN_BRIEF.md) - Android-
// specific, deliberately not identical to web/Streamlit's disclaimer,
// since the "OCR-read photos" phrasing there doesn't fit Android's
// manual-entry-first default.
private const val BODY_1 = "RigCheck is an experimental project built to learn app development, " +
    "not a certified or professional weight-safety tool. You type in numbers straight off your " +
    "own tag and ticket photos, and the math that follows is simplified — any step of that chain " +
    "can be wrong."
private const val BODY_2 = "Do not use this tool to decide whether your rig is safe to tow. " +
    "Always verify actual weights and ratings using a certified scale and your vehicle's official " +
    "documentation, and consult a qualified professional if you're unsure. You use this tool, and " +
    "any decisions you make based on it, entirely at your own risk and responsibility."

@Composable
fun DisclaimerScreen(onAcknowledge: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .padding(top = 48.dp, bottom = 24.dp)
                .size(72.dp)
                .background(DangerRed.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Filled.Warning,
                contentDescription = null,
                tint = DangerRed,
                modifier = Modifier.size(36.dp),
            )
        }
        Text(
            "Experimental Tool —\nNot for Safety Decisions",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center,
        )
        Text(
            BODY_1,
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 24.dp),
        )
        Text(
            BODY_2,
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp),
        )
        Button(
            onClick = onAcknowledge,
            modifier = Modifier.fillMaxWidth().padding(top = 32.dp),
        ) {
            Text("I Understand, Continue")
        }
    }
}
