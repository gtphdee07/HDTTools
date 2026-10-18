package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanHttp
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.navigation.EntryModule
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import mockwebserver3.SocketEffect
import okhttp3.OkHttpClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

// What the user is shown, and which next steps the dialog offers, when a Scan
// does not deliver. The Worker's own replies come from a fake HTTP server (no
// live Worker, no network, no money); the app's own failures come from the
// constants and codes the view model produces without a Worker. Every message is
// asserted as the literal words the user reads (docs/research/scan-failure-handling.md,
// R2), so rewording one is a visible change.
class ScanFailureTest {
    private lateinit var server: MockWebServer
    private lateinit var http: ScanHttp

    @Before
    fun startServer() {
        server = MockWebServer()
        server.start()
        http = ScanHttp(
            OkHttpClient.Builder().readTimeout(1, TimeUnit.SECONDS).build(),
            server.url("/v1/scan").toString(),
        )
    }

    @After
    fun stopServer() {
        server.close()
    }

    private fun scanThroughTheClient(): ScanResult.Failure {
        val result = runBlocking {
            withTimeout(10_000) { http.scan("jwt-abc", EntryModule.TRUCK, "aGk=", "image/jpeg", clientRequestId = null) }
        }
        return result as ScanResult.Failure
    }

    // Sends one Scan to the fake Worker, which answers with `status` and `body`,
    // and returns what the Scan screens would then show.
    private fun shownAfterWorkerReply(status: Int, code: String, message: String): ScanUiState.Error {
        server.enqueue(
            MockResponse.Builder().code(status).body("""{"ok":false,"code":"$code","message":"$message"}""").build(),
        )
        return scanErrorFor(scanThroughTheClient())
    }

    private fun assertShown(message: String, steps: List<ScanNextStep>, shown: ScanUiState.Error) {
        assertEquals(ScanUiState.Error(message, steps), shown)
    }

    // --- The Worker's named answers (R1 rows 1 to 7) ----------------------

    @Test
    fun `no scans left says nothing was used and offers buying Scans`() {
        val shown = shownAfterWorkerReply(402, "insufficient_credits", "Not enough scan credits.")
        assertShown(
            "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself.",
            listOf(ScanNextStep.BUY_SCANS),
            shown,
        )
    }

    @Test
    fun `a rejected token says nothing was used and offers signing in again`() {
        val shown = shownAfterWorkerReply(401, "unauthorized", "Missing or invalid account token.")
        assertShown(
            "Your sign-in has expired. Nothing was used. Sign in again to scan.",
            listOf(ScanNextStep.SIGN_IN),
            shown,
        )
    }

    @Test
    fun `an account the Worker could not check says nothing was used and offers Try again`() {
        val shown = shownAfterWorkerReply(503, "auth_unavailable", "Could not verify your account right now.")
        assertShown(
            "We couldn't verify your account just now. Nothing was used. Try again in a moment.",
            listOf(ScanNextStep.TRY_AGAIN),
            shown,
        )
    }

    @Test
    fun `a photo that could not be read says the Scan Credit was refunded, that a retry uses another, and offers Try again`() {
        val shown = shownAfterWorkerReply(502, "extraction_failed", "Could not read the image. Credit refunded.")
        assertShown(
            "We couldn't read that photo, and your Scan Credit was refunded. Trying again uses another Scan. " +
                "A clearer photo may work better, or type the numbers in yourself.",
            listOf(ScanNextStep.TRY_AGAIN),
            shown,
        )
    }

    @Test
    fun `a photo that could not be read and not refunded says so, that a retry is free, and offers Try again`() {
        val shown = shownAfterWorkerReply(
            502,
            "extraction_failed_no_refund",
            "Could not read the image, and we weren't able to automatically refund your credit.",
        )
        assertShown(
            "We couldn't read that photo, and couldn't refund your Scan Credit automatically. " +
                "Trying this photo again won't charge you again. If it keeps happening, contact support.",
            listOf(ScanNextStep.TRY_AGAIN),
            shown,
        )
    }

    @Test
    fun `a balance the Worker could not confirm says you may not have been charged and offers Try again`() {
        val shown = shownAfterWorkerReply(502, "billing_error", "Could not verify scan credits.")
        assertShown(
            "We couldn't confirm your Scan balance, so nothing was read. You may not have been charged. " +
                "Try again in a moment; a retry is not charged twice.",
            listOf(ScanNextStep.TRY_AGAIN),
            shown,
        )
    }

    @Test
    fun `a rejected request says nothing was used, hides the Worker's detail and offers typing or a different photo`() {
        val shown = shownAfterWorkerReply(400, "bad_request", "Body must be valid JSON.")
        assertShown(
            "We couldn't use that photo. Try a different photo, or type the numbers in yourself. Nothing was used.",
            listOf(ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO),
            shown,
        )
        assertFalse(shown.message.contains("valid JSON"))
    }

    // --- The app's own failures (R1 rows 8, 10, 11 and the sign-in gate) ----

    @Test
    fun `a photo that cannot be sent says nothing was used and offers typing or a different photo`() {
        val shown = scanErrorFor(ScanResult.Failure("photo_unsendable", "Could not decode the captured photo."))
        assertShown(
            "We couldn't open that photo. Try a different photo, or type the numbers in yourself. Nothing was used.",
            listOf(ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO),
            shown,
        )
    }

    @Test
    fun `a dropped connection says you may not have been charged and offers Try again`() {
        server.enqueue(MockResponse.Builder().onResponseStart(SocketEffect.CloseSocket()).build())
        val shown = scanErrorFor(scanThroughTheClient())
        assertShown(
            "We couldn't reach the scan service. You may not have been charged. " +
                "Check your connection and try again; a retry is not charged twice.",
            listOf(ScanNextStep.TRY_AGAIN),
            shown,
        )
    }

    @Test
    fun `a reply that is not the Worker's says you may not have been charged and offers Try again`() {
        server.enqueue(MockResponse.Builder().code(200).body("<html>Bad gateway</html>").build())
        val shown = scanErrorFor(scanThroughTheClient())
        assertShown(
            "We didn't get a usable answer from the scan service. You may not have been charged. " +
                "Try again; a retry is not charged twice.",
            listOf(ScanNextStep.TRY_AGAIN),
            shown,
        )
    }

    @Test
    fun `a request that never answers says it took too long and offers Try again`() {
        server.enqueue(MockResponse.Builder().onResponseStart(SocketEffect.Stall).build())
        val failure = scanThroughTheClient()
        assertEquals("timeout", failure.code)
        assertShown(
            "The scan service took too long to answer. You may not have been charged. " +
                "Try again; a retry is not charged twice.",
            listOf(ScanNextStep.TRY_AGAIN),
            scanErrorFor(failure),
        )
    }

    @Test
    fun `no account token on this device says nothing was used and offers signing in`() {
        assertShown("Sign in to scan. Nothing was used.", listOf(ScanNextStep.SIGN_IN), scanErrorFor(NOT_SIGNED_IN))
    }

    @Test
    fun `a stand-alone ticket with no weight says the Scan was used, a retry uses another, and offers typing or a different photo`() {
        assertShown(
            "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. " +
                "Type the weight in, or choose a different photo.",
            listOf(ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO),
            NO_WEIGHT_ERROR,
        )
    }

    @Test
    fun `a code the app has no wording for claims nothing about the charge and offers no Try again`() {
        val shown = scanErrorFor(ScanResult.Failure("something_new", "The Worker's own text."))
        assertShown(
            "Something went wrong with that Scan, and we can't tell whether a Scan Credit was used. " +
                "Check your Scan balance before you try again.",
            emptyList(),
            shown,
        )
    }

    // --- Where "Try again" is and is not offered (R3) ----------------------

    @Test
    fun `Try again is offered after exactly the cases that allow it`() {
        val offered = listOf(
            "auth_unavailable", "extraction_failed", "extraction_failed_no_refund", "billing_error",
            "network_error", "parse_error", "timeout",
        )
        val notOffered = listOf(
            "insufficient_credits", "unauthorized", "not_signed_in", "bad_request", "photo_unsendable",
            "client_error", "unknown_error",
        )
        for (code in offered) {
            assertTrue(code, ScanNextStep.TRY_AGAIN in scanErrorFor(ScanResult.Failure(code, "m")).nextSteps)
        }
        for (code in notOffered) {
            assertFalse(code, ScanNextStep.TRY_AGAIN in scanErrorFor(ScanResult.Failure(code, "m")).nextSteps)
        }
        assertFalse(ScanNextStep.TRY_AGAIN in NO_WEIGHT_ERROR.nextSteps)
    }

    // --- What the view model does after a failed Scan ----------------------

    // The path the view model takes for a failed Scan: show the error, and read
    // the balance again (a refund or a failed refund may have changed it),
    // except when the Worker said there was nothing to spend: the balance is then
    // set to 0 on the spot, with no read, so the chip never shows a stale number.
    private class Reported {
        val shown = mutableListOf<ScanUiState.Error>()
        var balanceReads = 0
        val balancesSet = mutableListOf<Int>()
    }

    private fun report(failure: ScanResult.Failure) = Reported().also { reported ->
        reportScanFailure(
            failure,
            show = { reported.shown += it },
            refreshBalance = { reported.balanceReads++ },
            setBalance = { reported.balancesSet += it },
        )
    }

    @Test
    fun `insufficient_credits is shown, the balance is set to 0 and it is not read again`() {
        val reported = report(ScanResult.Failure("insufficient_credits", "Not enough scan credits."))
        assertEquals(listOf(scanErrorFor(ScanResult.Failure("insufficient_credits", ""))), reported.shown)
        assertEquals(listOf(0), reported.balancesSet)
        assertEquals(0, reported.balanceReads)
    }

    @Test
    fun `every other failure is shown and the balance is read again once and never set`() {
        for (code in listOf("unauthorized", "auth_unavailable", "extraction_failed", "billing_error", "network_error")) {
            val failure = ScanResult.Failure(code, "message")
            val reported = report(failure)
            assertEquals(code, listOf(scanErrorFor(failure)), reported.shown)
            assertEquals(code, 1, reported.balanceReads)
            assertEquals(code, emptyList<Int>(), reported.balancesSet)
        }
    }

    @Test
    fun `no account token is shown with its next step and the balance is read again`() {
        val reported = report(NOT_SIGNED_IN)
        assertEquals(listOf(scanErrorFor(NOT_SIGNED_IN)), reported.shown)
        assertEquals(1, reported.balanceReads)
    }
}
