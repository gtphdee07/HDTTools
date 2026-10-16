package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanHttp
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.navigation.EntryModule
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import okhttp3.OkHttpClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

// What the user is shown, and which next step the dialog offers, when a Scan
// does not deliver. The Worker's own replies come from a fake HTTP server (no
// live Worker, no network, no money); the app's own `not_signed_in` comes from
// the constant the view model returns when it has no account token.
class ScanFailureTest {
    private lateinit var server: MockWebServer
    private lateinit var http: ScanHttp

    @Before
    fun startServer() {
        server = MockWebServer()
        server.start()
        http = ScanHttp(
            OkHttpClient.Builder().readTimeout(5, TimeUnit.SECONDS).build(),
            server.url("/v1/scan").toString(),
        )
    }

    @After
    fun stopServer() {
        server.close()
    }

    // Sends one Scan to the fake Worker, which answers with `status` and `body`,
    // and returns what the Scan screens would then show.
    private fun shownAfterWorkerReply(status: Int, code: String, message: String): ScanUiState.Error {
        server.enqueue(
            MockResponse.Builder().code(status).body("""{"ok":false,"code":"$code","message":"$message"}""").build(),
        )
        val result = runBlocking {
            withTimeout(10_000) { http.scan("jwt-abc", EntryModule.TRUCK, "aGk=", "image/jpeg", clientRequestId = null) }
        }
        return scanErrorFor(result as ScanResult.Failure)
    }

    @Test
    fun `a rejected token says the sign-in expired and offers signing in again`() {
        val shown = shownAfterWorkerReply(401, "unauthorized", "Missing or invalid account token.")
        assertEquals(ScanUiState.Error("Your sign-in has expired. Sign in again to scan.", ScanNextStep.SIGN_IN), shown)
    }

    @Test
    fun `an account the Worker could not check says nothing was charged and offers no sign-in`() {
        val shown = shownAfterWorkerReply(503, "auth_unavailable", "Could not verify your account right now.")
        assertEquals(
            ScanUiState.Error(
                "We couldn't verify your account just now, so nothing was scanned and you were not charged. " +
                    "Try again in a moment.",
                ScanNextStep.NONE,
            ),
            shown,
        )
    }

    @Test
    fun `no scans left says so and offers buying scans`() {
        val shown = shownAfterWorkerReply(402, "insufficient_credits", "Not enough scan credits.")
        assertEquals(ScanUiState.Error("You're out of scans.", ScanNextStep.BUY_SCANS), shown)
    }

    @Test
    fun `no account token on this device says to sign in and offers signing in`() {
        assertEquals(
            ScanUiState.Error("Sign in to scan.", ScanNextStep.SIGN_IN),
            scanErrorFor(NOT_SIGNED_IN),
        )
    }

    @Test
    fun `any other failure shows the message it came with and offers nothing`() {
        val shown = scanErrorFor(ScanResult.Failure("extraction_failed", "Could not read the image. Credit refunded."))
        assertEquals(ScanUiState.Error("Could not read the image. Credit refunded.", ScanNextStep.NONE), shown)
    }

    // The path the view model takes for a failed Scan: show the error, and read
    // the balance again (a refund or a failed refund may have changed it),
    // except when the Worker said there was nothing to spend: the balance then
    // cannot have changed.
    private class Reported {
        val shown = mutableListOf<ScanUiState.Error>()
        var balanceReads = 0
    }

    private fun report(failure: ScanResult.Failure) = Reported().also { reported ->
        reportScanFailure(failure, show = { reported.shown += it }, refreshBalance = { reported.balanceReads++ })
    }

    @Test
    fun `insufficient_credits is shown with its next step and the balance is not read again`() {
        val reported = report(ScanResult.Failure("insufficient_credits", "Not enough scan credits."))
        assertEquals(listOf(ScanUiState.Error("You're out of scans.", ScanNextStep.BUY_SCANS)), reported.shown)
        assertEquals(0, reported.balanceReads)
    }

    @Test
    fun `every other failure is shown and the balance is read again once`() {
        for (code in listOf("unauthorized", "auth_unavailable", "extraction_failed", "billing_error", "network_error")) {
            val failure = ScanResult.Failure(code, "message")
            val reported = report(failure)
            assertEquals(code, listOf(scanErrorFor(failure)), reported.shown)
            assertEquals(code, 1, reported.balanceReads)
        }
    }

    @Test
    fun `no account token is shown with its next step and the balance is read again`() {
        val reported = report(NOT_SIGNED_IN)
        assertEquals(listOf(ScanUiState.Error("Sign in to scan.", ScanNextStep.SIGN_IN)), reported.shown)
        assertEquals(1, reported.balanceReads)
    }
}
