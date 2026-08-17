package com.rigcheck.app.domain

import java.text.NumberFormat
import java.util.Locale
import kotlin.math.roundToLong

// Shared with ui/format's display helpers — domain needs this too, since
// note text (e.g. "Includes an estimated 1,660 lb tongue weight...") embeds
// a comma-grouped number as part of the business text itself, not just at
// final display time.
private val wholeNumberFormat: NumberFormat = NumberFormat.getIntegerInstance(Locale.US)

fun formatWholeNumber(value: Double): String = wholeNumberFormat.format(value.roundToLong())
