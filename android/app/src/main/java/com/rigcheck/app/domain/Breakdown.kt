package com.rigcheck.app.domain

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlin.math.abs
import kotlin.math.min
import kotlin.math.roundToInt

// Kotlin port of src/hdttools/api/breakdown.py (the single source of truth,
// itself already a port of web/src/calc.ts) — keep the three in sync, and
// keep test-vectors/breakdown_cases.json's SUPPORTED_CAPABILITIES in
// BreakdownGoldenVectorTest.kt updated as this port gains capabilities.
// Pin/tongue weight is commonly ~15-25% of trailer weight - used as a
// fraction of a REAL trailer-axle scale reading when one exists, or as a
// fraction of the trailer's RATED GVWR when no scale reading exists at all.
const val DEFAULT_PIN_WEIGHT_PCT = 0.20

private fun lb(value: Double?): Double = value ?: 0.0

// insufficient: this row's own "do we actually have enough data to check
// this" flag, checked from the specific source fields it depends on - not
// inferred from whether actual/limit happen to be 0, which a real 0 lb
// reading and a never-entered field are otherwise indistinguishable from.
private data class Row(
    val label: String,
    val actual: Double,
    val limit: Double,
    val note: String?,
    val insufficient: Boolean,
)

// Android-only enhancement, deliberately not ported back to breakdown.py/
// calc.ts: these two rows are sums of other rows, so their notes spell out
// the arithmetic with real numbers (matching the 2026-08-17 mockup) rather
// than the Python/web originals' fixed generic sentence. Suppressed
// entirely (null) when the row is insufficient - showing "0 + 0 = 0 lb"
// arithmetic would misrepresent "no data" as "a real zero reading."
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

fun computeBreakdown(
    truck: TruckTag,
    trailer: TrailerTag,
    scale: ScaleTicket,
    pinWeightPct: Double = DEFAULT_PIN_WEIGHT_PCT,
): List<BreakdownItem> {
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

    val standaloneWeight = lb(truck.standaloneWeightLb)
    // haveHitched/haveStandalone are deliberately independent checks - a
    // standalone-only reading (no hitched steer+drive reading) used to be
    // silently treated the same as a real hitched+standalone pair, which
    // gave the wrong trailer total (fixed 2026-08-21). haveStandalone is
    // truthy, not just non-null - a truck can't really weigh 0 lb, so an
    // explicit 0 means "not entered," matching axleCountProvided's own
    // truthy check above (truthiness parity with the Python original).
    val haveHitched = scale.steerAxleLb != null && scale.driveAxleLb != null
    val haveStandalone = truck.standaloneWeightLb != null && truck.standaloneWeightLb != 0.0

    val trailerTotalActual: Double
    val trailerTotalNote: String
    if (haveHitched && haveStandalone) {
        val tongueWeight = ((steer + drive) - standaloneWeight).coerceAtLeast(0.0)
        trailerTotalActual = trailerAxle + tongueWeight
        trailerTotalNote = "Includes an estimated ${formatWholeNumber(tongueWeight)} lb tongue weight " +
            "(steer + drive minus your truck's stand-alone weight)."
    } else if (scale.trailerAxleLb != null) {
        trailerTotalActual = trailerAxle / (1 - pinWeightPct)
        trailerTotalNote = "Estimated total weight — assumes the axle reading is " +
            "${formatWholeNumber((1 - pinWeightPct) * 100)}% of actual trailer weight; " +
            "enter your truck's stand-alone weight for an exact figure."
    } else {
        // No scale reading at all - nothing to divide, so estimate off the
        // trailer's rated GVWR instead. This is what makes a pre-purchase
        // "can I tow this" check possible before a real scale ticket
        // exists (currently only for the trailer side - the matching
        // truck-side predictive estimate is Round 2, not built yet).
        trailerTotalActual = trailerGvwr
        trailerTotalNote = "Estimated total weight — no scale reading yet, so this assumes " +
            "the trailer is loaded to its rated GVWR; weigh it for a real figure."
    }

    // Truck total: a real hitched reading always wins. Without one, this
    // row stays insufficient - the standalone-only predictive estimate
    // (mirroring the trailer side's GVWR-fallback logic above) is Round 2,
    // not built yet; test-vectors/breakdown_cases.json's
    // predictive_truck_estimate case is expected to fail against this
    // Kotlin port until then.
    val truckTotalActual: Double?
    if (haveHitched) {
        truckTotalActual = steer + drive
    } else {
        truckTotalActual = null
    }

    val towVehicleInsufficient = truckTotalActual == null || truck.gvwrLb == null
    val trailerTotalInsufficient = trailer.gvwrLb == null
    val combinedInsufficient = scale.grossWeightLb == null || truck.gvwrLb == null || trailer.gvwrLb == null

    val rows = listOf(
        Row(
            "Front Axle (Steer)", steer, frontGawr, null,
            scale.steerAxleLb == null || truck.frontGawrLb == null,
        ),
        Row(
            "Rear Axle (Drive)", drive, rearGawr, null,
            scale.driveAxleLb == null || truck.rearGawrLb == null,
        ),
        Row(
            "Tow Vehicle Total (GVWR)",
            truckTotalActual ?: 0.0,
            truckGvwr,
            if (towVehicleInsufficient) null else towVehicleTotalNote(steer, drive, truckGvwr),
            towVehicleInsufficient,
        ),
        Row(
            "Trailer Axle(s)", trailerAxle, gawrPerAxle * axleCount, axleCountNote,
            scale.trailerAxleLb == null || trailer.gawrPerAxleLb == null,
        ),
        Row("Trailer Total (GVWR)", trailerTotalActual, trailerGvwr, trailerTotalNote, trailerTotalInsufficient),
        Row(
            "Combined Rig Weight",
            gross,
            truckGvwr + trailerGvwr,
            if (combinedInsufficient) null else combinedRigWeightNote(truckGvwr, trailerGvwr, gross),
            combinedInsufficient,
        ),
    )

    return rows.map { row ->
        if (row.insufficient) {
            BreakdownItem(
                label = row.label,
                tone = Tone.INSUFFICIENT,
                actual = row.actual,
                limit = row.limit,
                margin = row.limit - row.actual,
                pct = 0,
                note = row.note,
            )
        } else {
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
}
