package com.rigcheck.app.domain

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlin.math.abs
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

// Android-only enhancement, deliberately not ported back to breakdown.py/
// calc.ts: these two rows are sums of other rows, so their notes spell out
// the arithmetic with real numbers (matching the 2026-08-17 mockup) rather
// than the Python/web originals' fixed generic sentence. Deliberately does
// NOT try to identify "the" row causing a "Not Safe" verdict the way the
// mockup's single-failure example did — with multiple simultaneous
// failures that framing gets ambiguous, so tone/color alone carries pass/
// fail and each note only explains its own row's math.
private fun towVehicleTotalNote(steer: Double, drive: Double, limit: Double): String {
    val sum = steer + drive
    val margin = limit - sum
    val overUnder = if (margin >= 0) "under" else "over"
    return "Steer (${formatWholeNumber(steer)}) + drive (${formatWholeNumber(drive)}) = " +
        "${formatWholeNumber(sum)} lb, which is ${formatWholeNumber(abs(margin))} lb $overUnder " +
        "this truck's ${formatWholeNumber(limit)} lb GVWR."
}

private fun combinedRigWeightNote(truckGvwr: Double, trailerGvwr: Double, gross: Double): String {
    val limit = truckGvwr + trailerGvwr
    val margin = limit - gross
    val overUnder = if (margin >= 0) "to spare" else "over"
    return "Truck GVWR (${formatWholeNumber(truckGvwr)}) + trailer GVWR " +
        "(${formatWholeNumber(trailerGvwr)}) = ${formatWholeNumber(limit)} lb allowed combined " +
        "weight — your ${formatWholeNumber(gross)} lb gross reading is " +
        "${formatWholeNumber(abs(margin))} lb $overUnder."
}

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
            towVehicleTotalNote(steer, drive, truckGvwr),
        ),
        Row("Trailer Axle(s)", trailerAxle, gawrPerAxle * axleCount, axleCountNote),
        Row("Trailer Total (GVWR)", trailerTotalActual, trailerGvwr, trailerTotalNote),
        Row(
            "Combined Rig Weight", gross, truckGvwr + trailerGvwr,
            combinedRigWeightNote(truckGvwr, trailerGvwr, gross),
        ),
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
