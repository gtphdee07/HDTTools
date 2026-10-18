package com.rigcheck.app.ui

import com.rigcheck.app.ui.navigation.EntryModule
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

// When the Scan notice goes (#120): it lasts until the user leaves the entry
// screen, enters the document by hand, starts another Scan or starts a rig.
class ScanNoticeStateTest {
    private val notice = ScanNotice(EntryModule.TRUCK, setOf("gvwr_lb"), setOf("gvwr_lb"))

    private fun stateWithNotice() = ScanNoticeState().also { it.scanDelivered(notice) }

    @Test
    fun `a delivered Scan's notice is held`() {
        assertEquals(notice, stateWithNotice().notice)
    }

    @Test
    fun `a Scan that read every field leaves no notice`() {
        val state = stateWithNotice()
        state.scanDelivered(null)
        assertNull(state.notice)
    }

    @Test
    fun `nothing is held before any Scan`() {
        assertNull(ScanNoticeState().notice)
    }

    @Test
    fun `entering the document by hand drops it`() {
        val state = stateWithNotice()
        state.enteredManually()
        assertNull(state.notice)
    }

    @Test
    fun `leaving the entry screen drops it`() {
        val state = stateWithNotice()
        state.leftEntryScreen()
        assertNull(state.notice)
    }

    @Test
    fun `starting another Scan drops it`() {
        val state = stateWithNotice()
        state.scanStarted()
        assertNull(state.notice)
    }

    @Test
    fun `starting a rig drops it`() {
        val state = stateWithNotice()
        state.rigStarted()
        assertNull(state.notice)
    }

    @Test
    fun `a newer Scan replaces the older notice`() {
        val state = stateWithNotice()
        val newer = ScanNotice(EntryModule.SCALE, setOf("gross_weight_lb"), setOf("gross_weight_lb"))
        state.scanDelivered(newer)
        assertEquals(newer, state.notice)
    }
}
