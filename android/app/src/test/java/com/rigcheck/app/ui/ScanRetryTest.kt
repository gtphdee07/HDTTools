package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanAttempts
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

// "Try again" re-sends the photo the user last scanned, through the same entry
// point (a document's Scan or the stand-alone ticket's), and so under the same
// client_request_id after a lost answer. The Scan client is faked: it records
// what it was sent, so no network or live Worker is used.
class ScanRetryTest {
    private val success = ScanResult.Success(JsonObject(emptyMap()))

    private data class Sent(val entry: String, val photo: String, val id: String)

    // Both Scan entry points of the view model, over one ScanAttempts, answering
    // from a script. `retry.again` is what the dialog's Try again calls.
    private class Harness(vararg answers: ScanResult) {
        private val script = answers.toMutableList()
        private val attempts = ScanAttempts()
        val retry = ScanRetry<String>()
        val sent = mutableListOf<Sent>()

        private suspend fun send(entry: String, module: EntryModule, photo: String): ScanResult =
            attempts.run(module, photo) { id ->
                sent += Sent(entry, photo, id)
                script.removeAt(0)
            }

        suspend fun scan(module: EntryModule, photo: String): ScanResult {
            retry.started(module, photo)
            return send("main", module, photo)
        }

        suspend fun scanStandalone(photo: String): ScanResult {
            retry.startedStandalone(photo)
            return send("standalone", EntryModule.SCALE, photo)
        }

        // `again` picks the entry point; the pick is a thunk here because the
        // fake send suspends and `again` does not.
        suspend fun tryAgain(): ScanResult? = retry.again<suspend () -> ScanResult>(
            main = { module, photo -> { send("main", module, photo) } },
            standalone = { photo -> { send("standalone", EntryModule.SCALE, photo) } },
        )?.invoke()
    }

    @Test
    fun `Try again with no Scan started sends nothing`() = runTest {
        val harness = Harness()

        assertNull(harness.tryAgain())
        assertEquals(emptyList<Sent>(), harness.sent)
    }

    @Test
    fun `Try again after a document Scan sends the same photo for the same document under the same id`() = runTest {
        val harness = Harness(ScanResult.Failure("network_error", "m"), success)

        harness.scan(EntryModule.TRAILER, "content://photo/a")
        harness.tryAgain()

        assertEquals(2, harness.sent.size)
        assertEquals(harness.sent[0], harness.sent[1])
        assertEquals("main", harness.sent[1].entry)
    }

    @Test
    fun `Try again after a stand-alone ticket Scan goes through the stand-alone entry point with the same id`() = runTest {
        val harness = Harness(ScanResult.Failure("timeout", "m"), success)

        harness.scanStandalone("content://photo/b")
        harness.tryAgain()

        assertEquals(2, harness.sent.size)
        assertEquals(harness.sent[0], harness.sent[1])
        assertEquals("standalone", harness.sent[1].entry)
    }

    @Test
    fun `Try again sends the photo of the latest Scan, not an earlier one`() = runTest {
        val harness = Harness(ScanResult.Failure("network_error", "m"), ScanResult.Failure("network_error", "m"), success)

        harness.scan(EntryModule.TRUCK, "content://photo/a")
        harness.scanStandalone("content://photo/b")
        harness.tryAgain()

        assertEquals("content://photo/b", harness.sent.last().photo)
        assertEquals("standalone", harness.sent.last().entry)
    }

    @Test
    fun `Try again after a refunded failure is a new Scan with a new id`() = runTest {
        val harness = Harness(ScanResult.Failure("extraction_failed", "m"), success)

        harness.scan(EntryModule.TRUCK, "content://photo/a")
        harness.tryAgain()

        assertEquals(harness.sent[0].photo, harness.sent[1].photo)
        assertEquals(false, harness.sent[0].id == harness.sent[1].id)
    }
}
