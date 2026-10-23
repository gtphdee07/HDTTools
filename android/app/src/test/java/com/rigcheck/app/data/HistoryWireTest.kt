package com.rigcheck.app.data

import com.rigcheck.app.domain.VerdictStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

// How a check is stored in the account's History, shared with Web: Web writes the Core status words, and a
// check made on either app must open on the other with the same verdict.
class HistoryWireTest {

    @Test
    fun `every verdict is written as the word Web writes and reads back as itself`() {
        val words = mapOf(
            VerdictStatus.PASS to "pass",
            VerdictStatus.FAIL to "fail",
            VerdictStatus.PARTIAL to "partial",
            VerdictStatus.INSUFFICIENT to "insufficient",
        )
        words.forEach { (verdict, word) ->
            assertEquals(word, verdictToWire(verdict))
            assertEquals(verdict, verdictFromWire(word))
        }
    }

    @Test
    fun `a word this app does not know is not a verdict`() {
        assertNull(verdictFromWire("caution"))
        assertNull(verdictFromWire("PASS"))
        assertNull(verdictFromWire(""))
    }

    @Test
    fun `a row Web saved becomes an entry with a trimmed nickname and an instant the screen can read`() {
        val entry = historyEntryFromRow("e-1", "  Goose + Addie ", "fail", "2026-10-22T23:30:00.5+00:00")

        assertEquals(HistoryEntry("e-1", "2026-10-22T23:30:00.500Z", "Goose + Addie", VerdictStatus.FAIL), entry)
    }

    @Test
    fun `a row with a verdict this app cannot read is left out rather than shown as another verdict`() {
        assertNull(historyEntryFromRow("e-1", "Goose", "caution", "2026-10-22T00:00:00Z"))
    }
}
