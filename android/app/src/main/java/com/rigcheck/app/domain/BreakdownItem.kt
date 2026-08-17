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
)
