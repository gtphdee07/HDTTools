package com.rigcheck.app.domain

// The pin weight slider works in whole percentage points (15-25); computeBreakdown
// works in the 0-1 fraction. pinWeightFraction is the one place that divides by 100
// (test-vectors/pin_weight_pct_contract.json, checked by PinWeightTest).
const val DEFAULT_PIN_WEIGHT_UI_PERCENT = 20

fun pinWeightFraction(uiPercent: Int): Double = uiPercent / 100.0
