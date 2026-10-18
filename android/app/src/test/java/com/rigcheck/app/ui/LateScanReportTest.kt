package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanResult
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Test

// What the user is told when a Scan answers after its check has ended (#118).
// The report only ever shows a message and re-reads the balance: it is given no
// way to change the current rig, so a late answer cannot merge into it.
class LateScanReportTest {
    private class Recorder {
        val shown = mutableListOf<String>()
        var balanceReads = 0
        val balanceSets = mutableListOf<Int>()

        fun report(result: ScanResult) = reportLateScan(
            result,
            show = { shown += it },
            refreshBalance = { balanceReads++ },
            setBalance = { balanceSets += it },
        )
    }

    @Test
    fun `a delivered Scan says it was used and its result was not, and the balance is read again`() {
        val r = Recorder()

        r.report(ScanResult.Success(JsonObject(emptyMap())))

        assertEquals(
            listOf("A Scan finished after you left that check, so its result wasn't used. It used a Scan Credit."),
            r.shown,
        )
        assertEquals(1, r.balanceReads)
        assertEquals(emptyList<Int>(), r.balanceSets)
    }

    @Test
    fun `a refunded failure shows its own message and no next steps, and the balance is read again`() {
        val r = Recorder()

        r.report(ScanResult.Failure("extraction_failed", "worker text"))

        assertEquals(listOf(ScanMessages.EXTRACTION_FAILED), r.shown)
        assertEquals(1, r.balanceReads)
    }

    @Test
    fun `a failure that kept the charge says so`() {
        val r = Recorder()

        r.report(ScanResult.Failure("extraction_failed_no_refund", "worker text"))

        assertEquals(listOf(ScanMessages.EXTRACTION_FAILED_NO_REFUND), r.shown)
    }

    @Test
    fun `out of Scans sets the balance to 0 without a read, as for a current Scan`() {
        val r = Recorder()

        r.report(ScanResult.Failure("insufficient_credits", "worker text"))

        assertEquals(listOf(ScanMessages.OUT_OF_SCANS), r.shown)
        assertEquals(listOf(0), r.balanceSets)
        assertEquals(0, r.balanceReads)
    }

    @Test
    fun `an unknown code claims nothing about the charge`() {
        val r = Recorder()

        r.report(ScanResult.Failure("something_new", "worker text"))

        assertEquals(listOf(ScanMessages.UNKNOWN), r.shown)
    }
}
