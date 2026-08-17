package com.rigcheck.app.domain

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlin.math.min
import kotlin.math.roundToInt

// Kotlin port of src/hdttools/api/breakdown.py (the single source of truth,
// itself already a port of web/src/calc.ts) — keep the three in sync.
// Pin/tongue weight is commonly ~15-25% of trailer weight, so a trailer's
// axle reading alone is assumed to be ~80% of its actual total weight when
// no stand-alone truck weight was given to compute an exact figure.
const val DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8

private fun lb(value: Double?): Double = value ?: 0.0

private data class Row(val label: String, val actual: Double, val limit: Double, val note: String?)

fun computeBreakdown(truck: TruckTag, trailer: TrailerTag, scale: ScaleTicket): List<BreakdownItem> {
    val steer = lb(scale.steerAxleLb)
    val drive = lb(scale.driveAxleLb)
    val trailerAxle = lb(scale.trailerAxleLb)
    val gross = lb(scale.grossWeightLb)

    val truckGvwr = lb(truck.gvwrLb)
    val frontGawr = lb(truck.frontGawrLb)
    val rearGawr = lb(truck.rearGawrLb)

    val trailerGvwr = lb(trailer.gvwrLb)
    val gawrPerAxle = lb(trailer.gawrPerAxleLb)

    // Truthiness parity with the Python original: an explicit 0 is treated
    // the same as "not provided" for both axleCount and standaloneWeightLb,
    // not just null — a plain `?:` port would diverge here.
    val axleCountRaw = trailer.axleCount
    val axleCountProvided = axleCountRaw != null && axleCountRaw != 0
    val axleCount = if (axleCountProvided) axleCountRaw!! else 2
    val axleCountNote = if (axleCountProvided) {
        "Trailer axle rating: $axleCount axle(s) at the tag's per-axle rating."
    } else {
        "Assumes a 2-axle trailer at the tag's per-axle rating."
    }

    val standaloneWeight = truck.standaloneWeightLb
    val standaloneProvided = standaloneWeight != null && standaloneWeight != 0.0
    val trailerTotalActual: Double
    val trailerTotalNote: String
    if (standaloneProvided) {
        val tongueWeight = ((steer + drive) - standaloneWeight!!).coerceAtLeast(0.0)
        trailerTotalActual = trailerAxle + tongueWeight
        trailerTotalNote = "Includes an estimated ${formatWholeNumber(tongueWeight)} lb tongue weight " +
            "(steer + drive minus your truck's stand-alone weight)."
    } else {
        trailerTotalActual = trailerAxle / DEFAULT_AXLE_TO_TOTAL_RATIO
        trailerTotalNote = "Estimated total weight — assumes the axle reading is " +
            "80% of actual trailer weight; enter your truck's stand-alone weight for an exact figure."
    }

    val rows = listOf(
        Row("Front Axle (Steer)", steer, frontGawr, null),
        Row("Rear Axle (Drive)", drive, rearGawr, null),
        Row(
            "Tow Vehicle Total (GVWR)", steer + drive, truckGvwr,
            "Steer + drive axle readings vs. your truck tag's GVWR.",
        ),
        Row("Trailer Axle(s)", trailerAxle, gawrPerAxle * axleCount, axleCountNote),
        Row("Trailer Total (GVWR)", trailerTotalActual, trailerGvwr, trailerTotalNote),
        Row("Combined Rig Weight", gross, truckGvwr + trailerGvwr, null),
    )

    return rows.map { row ->
        val passed = row.actual <= row.limit
        val pct = if (row.limit > 0) min(100, ((row.actual / row.limit) * 100).roundToInt()) else 0
        BreakdownItem(
            label = row.label,
            tone = if (passed) Tone.SUCCESS else Tone.WARNING,
            actual = row.actual,
            limit = row.limit,
            margin = row.limit - row.actual,
            pct = pct,
            note = row.note,
        )
    }
}
