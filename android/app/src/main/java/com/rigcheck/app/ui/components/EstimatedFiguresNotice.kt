package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.SunsetOrange

// Persistent (not dismissible) caution shown alongside any breakdown row
// derived from pin-weight-percentage math rather than a real scale
// reading - Android port of Web's PredictiveEstimateNotice.tsx, same
// legal copy. Deliberately separate from DisclaimerScreen (a one-time,
// acknowledge-and-forget screen): this context needs to travel with the
// estimate every time it's shown, not just once per session.
@Composable
fun EstimatedFiguresNotice() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(SunsetOrange.copy(alpha = 0.12f), RoundedCornerShape(12.dp))
            .padding(16.dp),
    ) {
        Text(
            "⚠️ Estimated Figures — Confirm Before You Buy",
            style = MaterialTheme.typography.titleSmall,
        )
        val bullets = listOf(
            "Trim, engine, axle ratio, cab/bed size, and factory options change a specific vehicle's " +
                "real payload — a GVWR/GAWR from a compliance label is a rating, not a guarantee for " +
                "every configuration.",
            "This estimate doesn't account for passengers, cargo in the cab or bed, or aftermarket " +
                "accessories — all of which reduce what's actually left for towing.",
            "Before buying, confirm the actual ratings on that specific vehicle's own certification " +
                "label, and the trailer's own data plate — not an average, a brochure figure, or this " +
                "estimate.",
            "Actual results may differ. You are solely responsible for safe towing and for complying " +
                "with all applicable federal and state regulations, including FMCSA and DOT requirements.",
        )
        Column(modifier = Modifier.padding(top = 8.dp)) {
            bullets.forEach { bullet ->
                Text(
                    "•  $bullet",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}
