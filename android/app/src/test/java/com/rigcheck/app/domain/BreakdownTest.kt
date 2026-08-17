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
}
