package com.rigcheck.app.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
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
        assertEquals(VerdictStatus.FAIL, verdict.status)
    }

    @Test
    fun `all rows insufficient gives Not Enough Information`() {
        val verdict = verdictFor(listOf(item(Tone.INSUFFICIENT), item(Tone.INSUFFICIENT)))
        assertEquals("Not Enough Information", verdict.headline)
        assertEquals(VerdictStatus.INSUFFICIENT, verdict.status)
    }

    @Test
    fun `some rows insufficient gives Partially Checked`() {
        val verdict = verdictFor(listOf(item(Tone.SUCCESS), item(Tone.INSUFFICIENT)))
        assertEquals("Partially Checked", verdict.headline)
        assertEquals(VerdictStatus.PARTIAL, verdict.status)
    }

    @Test
    fun `a real failure always wins over insufficient rows`() {
        val verdict = verdictFor(listOf(item(Tone.WARNING), item(Tone.INSUFFICIENT), item(Tone.INSUFFICIENT)))
        assertEquals("Not Safe to Tow", verdict.headline)
        assertEquals(VerdictStatus.FAIL, verdict.status)
    }

    // The Combined Rig Weight row is the one Advisory Item (#47): insufficient, it is
    // treated as absent; checked, it counts like any row. The sublines themselves are
    // asserted per case by the golden vectors; these pin the rule on bare tones.

    private fun combined(tone: Tone) = item(tone).copy(label = COMBINED_RIG_WEIGHT_LABEL)

    @Test
    fun `an insufficient combined row does not make a checked rig Partially Checked`() {
        val verdict = verdictFor(listOf(item(Tone.SUCCESS), combined(Tone.INSUFFICIENT)))
        assertEquals(VerdictStatus.PASS, verdict.status)
        assertTrue(verdict.subline.endsWith(GCWR_UNCHECKED_CAVEAT))
    }

    @Test
    fun `a checked combined row counts as checked, an insufficient one does not`() {
        val verdict = verdictFor(listOf(item(Tone.INSUFFICIENT), combined(Tone.SUCCESS)))
        assertEquals(VerdictStatus.PARTIAL, verdict.status)
        val allBlank = verdictFor(listOf(item(Tone.INSUFFICIENT), combined(Tone.INSUFFICIENT)))
        assertEquals(VerdictStatus.INSUFFICIENT, allBlank.status)
    }

    @Test
    fun `a checked combined row removes the caveat, and a failing one fails the rig`() {
        val pass = verdictFor(listOf(item(Tone.SUCCESS), combined(Tone.SUCCESS)))
        assertEquals("Every axle checks out under its rated limit.", pass.subline)
        assertEquals(VerdictStatus.FAIL, verdictFor(listOf(item(Tone.SUCCESS), combined(Tone.WARNING))).status)
    }

    @Test
    fun `status is never derived from headline text`() {
        // Regression guard: "Not Safe to Tow" and "Not Enough Information"
        // both start with "Not" - status must come from the explicit field.
        val verdict = verdictFor(listOf(item(Tone.INSUFFICIENT)))
        assertTrue(verdict.headline.startsWith("Not"))
        assertEquals(VerdictStatus.INSUFFICIENT, verdict.status)
    }
}
