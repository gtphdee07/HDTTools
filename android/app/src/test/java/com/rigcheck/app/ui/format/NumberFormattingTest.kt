package com.rigcheck.app.ui.format

import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import org.junit.Assert.assertEquals
import org.junit.Test

class NumberFormattingTest {

    @Test
    fun `formatLb comma-groups thousands`() {
        assertEquals("14,225 lb", formatLb(14225.0))
        assertEquals("0 lb", formatLb(0.0))
        assertEquals("999 lb", formatLb(999.0))
    }

    @Test
    fun `badgeLabel reads to spare when passing`() {
        val item = BreakdownItem(
            label = "x", tone = Tone.SUCCESS, actual = 8000.0, limit = 9500.0,
            margin = 1500.0, pct = 84, note = null,
        )
        assertEquals("1,500 lb to spare", badgeLabel(item))
    }

    @Test
    fun `badgeLabel reads over when failing`() {
        val item = BreakdownItem(
            label = "x", tone = Tone.WARNING, actual = 11000.0, limit = 9500.0,
            margin = -1500.0, pct = 100, note = null,
        )
        assertEquals("1,500 lb over", badgeLabel(item))
    }
}
