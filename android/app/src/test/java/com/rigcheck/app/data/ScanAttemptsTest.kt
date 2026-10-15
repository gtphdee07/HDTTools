package com.rigcheck.app.data

import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

// A retry of the same photo after a lost Scan answer must carry the same
// client_request_id, so the Worker charges once; any other outcome, or another
// photo, starts a fresh one. The Scan client is faked: it records the id of
// each request and answers from a script, so no network or live Worker is used.
class ScanAttemptsTest {

    private val success = ScanResult.Success(JsonObject(emptyMap()))
    private fun failure(code: String) = ScanResult.Failure(code, "message for $code")

    private class FakeScanClient(vararg answers: ScanResult) {
        private val script = answers.toMutableList()
        val sentIds = mutableListOf<String>()

        suspend fun scan(clientRequestId: String): ScanResult {
            sentIds += clientRequestId
            return script.removeAt(0)
        }
    }

    // Scans `photo` once per scripted answer and returns the ids sent.
    private suspend fun scanRepeatedly(
        attempts: ScanAttempts,
        photo: String,
        vararg answers: ScanResult,
        module: EntryModule = EntryModule.TRUCK,
    ): List<String> {
        val client = FakeScanClient(*answers)
        repeat(answers.size) { attempts.run(module, photo, client::scan) }
        return client.sentIds
    }

    @Test
    fun `a lost answer keeps the id for the next scan of the same photo`() = runTest {
        for (lost in listOf("network_error", "parse_error", "billing_error", "extraction_failed_no_refund")) {
            val ids = scanRepeatedly(ScanAttempts(), "content://photo/a", failure(lost), success)

            assertEquals("after $lost", ids[0], ids[1])
        }
    }

    @Test
    fun `the id stays the same through several lost answers in a row`() = runTest {
        val ids = scanRepeatedly(
            ScanAttempts(),
            "content://photo/a",
            failure("network_error"),
            failure("parse_error"),
            failure("billing_error"),
            success,
        )

        assertEquals(1, ids.toSet().size)
    }

    @Test
    fun `a settled answer starts a fresh id for the next scan of the same photo`() = runTest {
        val settled = listOf(
            success,
            failure("insufficient_credits"),
            failure("extraction_failed"),
            failure("unauthorized"),
            failure("bad_request"),
            failure("auth_unavailable"),
        )
        for (answer in settled) {
            val ids = scanRepeatedly(ScanAttempts(), "content://photo/a", answer, success)

            assertNotEquals("after ${(answer as? ScanResult.Failure)?.code ?: "success"}", ids[0], ids[1])
        }
    }

    @Test
    fun `a different photo gets a fresh id even if the last answer was lost`() = runTest {
        val attempts = ScanAttempts()

        val first = scanRepeatedly(attempts, "content://photo/a", failure("network_error"))
        val second = scanRepeatedly(attempts, "content://photo/b", success)

        assertNotEquals(first[0], second[0])
    }

    @Test
    fun `going back to the first photo after a different one starts a fresh id`() = runTest {
        val attempts = ScanAttempts()

        val first = scanRepeatedly(attempts, "content://photo/a", failure("network_error"))
        scanRepeatedly(attempts, "content://photo/b", failure("network_error"))
        val third = scanRepeatedly(attempts, "content://photo/a", success)

        assertNotEquals(first[0], third[0])
    }

    @Test
    fun `the same photo for a different document is a different scan`() = runTest {
        val attempts = ScanAttempts()
        val client = FakeScanClient(failure("network_error"), success)

        attempts.run(EntryModule.TRUCK, "content://photo/a", client::scan)
        attempts.run(EntryModule.TRAILER, "content://photo/a", client::scan)

        assertNotEquals(client.sentIds[0], client.sentIds[1])
    }

    @Test
    fun `a scan that throws leaves the id for a retry of the same photo`() = runTest {
        val attempts = ScanAttempts()
        val sent = mutableListOf<String>()

        runCatching { attempts.run(EntryModule.TRUCK, "content://photo/a") { sent += it; error("interrupted") } }
        attempts.run(EntryModule.TRUCK, "content://photo/a") { sent += it; success }

        assertEquals(sent[0], sent[1])
    }

    @Test
    fun `the answer is passed through unchanged`() = runTest {
        val lost = failure("network_error")

        val result = ScanAttempts().run(EntryModule.SCALE, "content://photo/a") { lost }

        assertEquals(lost, result)
    }
}
