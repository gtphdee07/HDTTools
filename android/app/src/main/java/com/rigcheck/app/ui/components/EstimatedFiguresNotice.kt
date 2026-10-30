package com.rigcheck.app.ui.components

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.RigCheckStyles

// Persistent (not dismissible) caution shown alongside any breakdown row
// derived from pin-weight-percentage math rather than a real scale
// reading - Android port of Web's PredictiveEstimateNotice.tsx, same
// legal copy. Deliberately separate from DisclaimerScreen (a one-time,
// acknowledge-and-forget screen): this context needs to travel with the
// estimate every time it's shown, not just once per session.
//
// Drawn as the design's warn Notice card (tint-orange). The title keeps its warning emoji because the text is
// frozen, so the card draws no icon of its own (ui-redesign-map.json, `results.estimated_notice`).
@Composable
fun EstimatedFiguresNotice(modifier: Modifier = Modifier) {
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
    RigCheckNoticeCard(
        tone = RigCheckNoticeTone.Warn,
        title = "⚠️ Estimated Figures — Confirm Before You Buy",
        icon = null,
        modifier = modifier.testTag(UiTags.RESULTS_ESTIMATED_NOTICE),
    ) {
        bullets.forEach { bullet -> Text("•  $bullet", style = RigCheckStyles.bodySm, color = Ink) }
    }
}
