package com.rigcheck.app.domain

// actual/limit/margin are raw, unrounded values on purpose — rounding and
// comma-grouping happen at display time (see ui/format/NumberFormatting.kt),
// not here. margin is signed (limit - actual): positive means passing with
// that much room to spare, negative means over by that amount.
data class BreakdownItem(
    val label: String,
    val tone: Tone,
    val actual: Double,
    val limit: Double,
    val margin: Double,
    val pct: Int,
    val note: String?,
    // Mirrors breakdown.py's "estimated" field (added 2026-08-21, Round 2):
    // true when `actual` comes from pin-weight-pct/GVWR-fallback math
    // rather than a real scale reading. Drives the UI's estimated-figures
    // disclaimer - never true on an insufficient row.
    val estimated: Boolean = false,
)
