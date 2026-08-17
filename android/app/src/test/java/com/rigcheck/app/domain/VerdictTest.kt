package com.rigcheck.app.domain

import org.junit.Assert.assertEquals
import org.junit.Test

private fun item(tone: Tone) = BreakdownItem(
    label = "x", tone = tone, actual = 1.0, limit = 1.0, margin = 0.0, pct = 100, note = null,
)

class VerdictTest {

    @Test
    fun `all passing gives Safe to Tow`() {
        val verdict = verdictFor(listOf(item(Tone.SUCCESS), item(Tone.SUCCESS)))
        assertEquals("Safe to Tow", verdict.headline)
        assertEquals(Tone.SUCCESS, verdict.tone)
    }

    @Test
    fun `any failure gives Not Safe to Tow`() {
        val verdict = verdictFor(listOf(item(Tone.SUCCESS), item(Tone.WARNING)))
        assertEquals("Not Safe to Tow", verdict.headline)
        assertEquals(Tone.WARNING, verdict.tone)
    }
}
