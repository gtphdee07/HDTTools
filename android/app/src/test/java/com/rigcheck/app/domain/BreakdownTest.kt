package com.rigcheck.app.domain

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.format.formatLb
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Same fixtures as tests/test_breakdown.py ("the shared spec") — keep in sync.
private val TRUCK = TruckTag(gvwrLb = 14000.0, frontGawrLb = 6000.0, rearGawrLb = 9500.0)
private val TRAILER = TrailerTag(gvwrLb = 12500.0, gawrPerAxleLb = 6000.0)
private val SCALE = ScaleTicket(
    steerAxleLb = 5620.0,
    driveAxleLb = 9040.0,
    trailerAxleLb = 11380.0,
    grossWeightLb = 26040.0,
)

private fun item(items: List<BreakdownItem>, label: String): BreakdownItem =
    items.first { it.label == label }

class BreakdownTest {

    @Test
    fun `trailer axle limit defaults to 2 axles when omitted`() {
        val items = computeBreakdown(TRUCK, TRAILER, SCALE)
        val row = item(items, "Trailer Axle(s)")
        assertEquals("12,000 lb", formatLb(row.limit))
        assertEquals("Assumes a 2-axle trailer at the tag's per-axle rating.", row.note)
    }

    @Test
    fun `trailer axle limit uses custom axle count`() {
        val trailer = TRAILER.copy(axleCount = 3)
        val items = computeBreakdown(TRUCK, trailer, SCALE)
        val row = item(items, "Trailer Axle(s)")
        assertEquals("18,000 lb", formatLb(row.limit))
        assertEquals("Trailer axle rating: 3 axle(s) at the tag's per-axle rating.", row.note)
    }

    @Test
    fun `trailer total estimates from axle reading when standalone weight omitted`() {
        val items = computeBreakdown(TRUCK, TRAILER, SCALE)
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("14,225 lb", formatLb(row.actual))
        assertTrue(row.note!!.startsWith("Estimated total weight"))
    }

    @Test
    fun `trailer total includes estimated tongue weight when provided`() {
        val truck = TRUCK.copy(standaloneWeightLb = 13000.0)
        val items = computeBreakdown(truck, TRAILER, SCALE)
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("13,040 lb", formatLb(row.actual))
        assertTrue(row.note!!.contains("1,660 lb tongue weight"))
    }

    @Test
    fun `tongue weight clamps at zero when standalone exceeds hitched total`() {
        val truck = TRUCK.copy(standaloneWeightLb = 20000.0)
        val items = computeBreakdown(truck, TRAILER, SCALE)
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("11,380 lb", formatLb(row.actual))
        assertTrue(row.note!!.contains("0 lb tongue weight"))
    }

    // Not covered by tests/test_breakdown.py — the Python truthiness checks
    // (`if standalone_weight:`, `if axle_count_raw else 2`) treat an explicit
    // 0 the same as "not provided." These two cases confirm the Kotlin port
    // replicates that on purpose, rather than diverging via a naive `?:`.

    @Test
    fun `axle count of zero is treated as not provided`() {
        val trailer = TRAILER.copy(axleCount = 0)
        val items = computeBreakdown(TRUCK, trailer, SCALE)
        val row = item(items, "Trailer Axle(s)")
        assertEquals("12,000 lb", formatLb(row.limit))
        assertEquals("Assumes a 2-axle trailer at the tag's per-axle rating.", row.note)
    }

    @Test
    fun `standalone weight of zero is treated as not provided`() {
        val truck = TRUCK.copy(standaloneWeightLb = 0.0)
        val items = computeBreakdown(truck, TRAILER, SCALE)
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("14,225 lb", formatLb(row.actual))
        assertTrue(row.note!!.startsWith("Estimated total weight"))
    }

    // Android-only enhancement (not in tests/test_breakdown.py): dynamic,
    // number-specific explanations on the two rows that sum other rows,
    // matching the 2026-08-17 mockup instead of the Python/web originals'
    // fixed generic sentence.

    @Test
    fun `tow vehicle total note spells out the arithmetic`() {
        val items = computeBreakdown(TRUCK, TRAILER, SCALE)
        val row = item(items, "Tow Vehicle Total (GVWR)")
        assertEquals(
            "Steer (5,620) + drive (9,040) = 14,660 lb, which is 660 lb over this truck's 14,000 lb GVWR.",
            row.note,
        )
    }

    @Test
    fun `combined rig weight note spells out the arithmetic`() {
        val items = computeBreakdown(TRUCK, TRAILER, SCALE)
        val row = item(items, "Combined Rig Weight")
        assertEquals(
            "Truck GVWR (14,000) + trailer GVWR (12,500) = 26,500 lb allowed combined " +
                "weight — your 26,040 lb gross reading is 460 lb to spare.",
            row.note,
        )
    }

    // Fixed 2026-08-21 - see NEXT_STEPS.md and
    // test-vectors/breakdown_cases.json's
    // standalone_without_hitched_falls_back_to_axle_estimate case. A
    // stand-alone reading with no real hitched (steer+drive) reading used
    // to be treated the same as a real hitched+standalone pair, silently
    // producing the wrong trailer total.

    @Test
    fun `standalone weight without a hitched reading falls back to the axle estimate, not the exact-tongue-weight math`() {
        val truck = TRUCK.copy(standaloneWeightLb = 10000.0)
        val scaleTrailerAxleOnly = ScaleTicket(trailerAxleLb = 11380.0)
        val items = computeBreakdown(truck, TRAILER, scaleTrailerAxleOnly)
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("14,225 lb", formatLb(row.actual)) // not 11,380 - the bug's symptom
    }

    @Test
    fun `tow vehicle total is insufficient with neither a hitched nor a standalone reading`() {
        val items = computeBreakdown(TRUCK, TRAILER, ScaleTicket())
        val row = item(items, "Tow Vehicle Total (GVWR)")
        assertEquals(Tone.INSUFFICIENT, row.tone)
    }

    // GVWR-fallback trailer estimate - no scale reading at all, the pre-
    // purchase/predictive case.

    @Test
    fun `trailer total estimates from GVWR when no scale reading exists at all`() {
        val items = computeBreakdown(TRUCK, TRAILER, ScaleTicket())
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("12,500 lb", formatLb(row.actual))
        assertTrue(row.note!!.contains("no scale reading yet"))
    }

    @Test
    fun `blank rig reports every row insufficient, not a false pass`() {
        val items = computeBreakdown(TruckTag(), TrailerTag(), ScaleTicket())
        assertTrue(items.all { it.tone == Tone.INSUFFICIENT })
    }

    // Adjustable pin-weight % - was hardcoded at 80%/20% (DEFAULT_AXLE_TO_TOTAL_RATIO).

    @Test
    fun `custom pin weight pct changes the trailer axle reading estimate`() {
        // 11,380 / (1 - 0.15) = 13,388
        val items = computeBreakdown(TRUCK, TRAILER, SCALE, pinWeightPct = 0.15)
        val row = item(items, "Trailer Total (GVWR)")
        assertEquals("13,388 lb", formatLb(row.actual))
        assertTrue(row.note!!.contains("85% of actual trailer weight"))
    }

    // Round 2 (not built yet) - predictive standalone-only truck-side
    // estimate, mirroring tests/test_breakdown.py's
    // test_truck_total_estimates_from_standalone_weight_when_no_hitched_reading.
    // Written ahead of the feature on purpose (see NEXT_STEPS.md and
    // BreakdownGoldenVectorTest.kt's SUPPORTED_CAPABILITIES comment) -
    // EXPECTED TO FAIL until computeBreakdown gains this branch. When it
    // does, this test should pass with no changes.

    @Test
    fun `tow vehicle total estimates from standalone weight when no hitched reading exists`() {
        // No scale data at all -> trailer total falls to the GVWR-fallback
        // estimate (12,500) -> tongue weight estimate = 12,500 * 0.20 = 2,500
        // -> truck total = 6,000 (standalone) + 2,500 = 8,500.
        val truck = TRUCK.copy(standaloneWeightLb = 6000.0)
        val items = computeBreakdown(truck, TRAILER, ScaleTicket())
        val row = item(items, "Tow Vehicle Total (GVWR)")
        assertEquals(Tone.SUCCESS, row.tone)
        assertEquals("8,500 lb", formatLb(row.actual))
    }
}
