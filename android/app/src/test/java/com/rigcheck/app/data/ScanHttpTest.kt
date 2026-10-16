package com.rigcheck.app.data

import com.rigcheck.app.ui.navigation.EntryModule
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import mockwebserver3.SocketEffect
import okhttp3.OkHttpClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

// How the Scan client reads the Worker's reply, against a fake HTTP server
// (no live Worker, no network, no money). The replies are the ones the
// Worker documents in workers/scan-proxy/README.md ("Errors") plus the
// extraction_failed_no_refund one its source returns; the message strings
// are the Worker's own, so a client that swapped or dropped one would show.
class ScanHttpTest {
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

    private fun reply(status: Int, body: String) {
        server.enqueue(MockResponse.Builder().code(status).body(body).build())
    }

    private fun scan(): ScanResult = runBlocking {
        // A client that never resumes would hang the build; fail instead.
        withTimeout(10_000) { http.scan("jwt-abc", EntryModule.TRUCK, "aGk=", "image/jpeg", clientRequestId = null) }
    }

    private fun workerError(status: Int, code: String, message: String) {
        reply(status, """{"ok":false,"code":"$code","message":"$message"}""")
    }

    private fun assertFailure(code: String, message: String) {
        assertEquals(ScanResult.Failure(code, message), scan())
    }

    // --- One test per Worker error code -----------------------------------

    @Test
    fun `insufficient_credits comes back with the Worker's code and message`() {
        workerError(402, "insufficient_credits", "Not enough scan credits.")
        assertFailure("insufficient_credits", "Not enough scan credits.")
    }

    @Test
    fun `unauthorized comes back with the Worker's code and message`() {
        workerError(401, "unauthorized", "Missing or invalid account token.")
        assertFailure("unauthorized", "Missing or invalid account token.")
    }

    @Test
    fun `auth_unavailable comes back with the Worker's code and message`() {
        workerError(503, "auth_unavailable", "Could not verify your account right now.")
        assertFailure("auth_unavailable", "Could not verify your account right now.")
    }

    @Test
    fun `extraction_failed comes back with the Worker's code and message`() {
        workerError(502, "extraction_failed", "Could not read the image. Credit refunded.")
        assertFailure("extraction_failed", "Could not read the image. Credit refunded.")
    }

    @Test
    fun `extraction_failed_no_refund comes back with the Worker's code and message`() {
        val message = "Could not read the image, and we weren't able to automatically refund your credit. " +
            "Please contact support if this keeps happening."
        workerError(502, "extraction_failed_no_refund", message)
        assertFailure("extraction_failed_no_refund", message)
    }

    @Test
    fun `billing_error comes back with the Worker's code and message`() {
        workerError(502, "billing_error", "Could not verify scan credits.")
        assertFailure("billing_error", "Could not verify scan credits.")
    }

    @Test
    fun `bad_request comes back with the Worker's code and message`() {
        workerError(400, "bad_request", "Body must be valid JSON.")
        assertFailure("bad_request", "Body must be valid JSON.")
    }

    // --- The client's own failures ----------------------------------------

    @Test
    fun `a dropped connection is a network_error`() {
        server.enqueue(MockResponse.Builder().onResponseStart(SocketEffect.CloseSocket()).build())

        val result = scan()

        assertTrue("expected a Failure, got $result", result is ScanResult.Failure)
        assertEquals("network_error", (result as ScanResult.Failure).code)
    }

    @Test
    fun `a reply that is not JSON is a parse_error`() {
        reply(200, "<html>Bad gateway</html>")
        assertFailure("parse_error", "Could not parse the server's response.")
    }

    @Test
    fun `an empty reply is a parse_error`() {
        reply(200, "")
        assertFailure("parse_error", "Could not parse the server's response.")
    }

    @Test
    fun `JSON that is not an object is a parse_error`() {
        reply(200, "[1,2,3]")
        assertFailure("parse_error", "Could not parse the server's response.")
    }

    @Test
    fun `an ok that is not a boolean is a parse_error, not a success`() {
        reply(200, """{"ok":"yes","fields":{"vin":"1"}}""")
        assertFailure("parse_error", "Could not parse the server's response.")
    }

    @Test
    fun `a success whose fields are not an object is a parse_error, not a success`() {
        reply(200, """{"ok":true,"fields":"vin=1"}""")
        assertFailure("parse_error", "Could not parse the server's response.")
    }

    // --- Success ----------------------------------------------------------

    @Test
    fun `a success with fields returns them`() {
        reply(200, """{"ok":true,"doc_type":"truck_tag","fields":{"gvwr":14000,"vin":"1FT"}}""")

        val expected = JsonObject(mapOf("gvwr" to JsonPrimitive(14000), "vin" to JsonPrimitive("1FT")))
        assertEquals(ScanResult.Success(expected), scan())
    }

    @Test
    fun `a success with no fields returns an empty field set`() {
        reply(200, """{"ok":true,"doc_type":"truck_tag"}""")
        assertEquals(ScanResult.Success(JsonObject(emptyMap())), scan())
    }

    @Test
    fun `a success with an empty fields object returns an empty field set`() {
        reply(200, """{"ok":true,"doc_type":"truck_tag","fields":{}}""")
        assertEquals(ScanResult.Success(JsonObject(emptyMap())), scan())
    }

    // --- ok:false without a code ------------------------------------------

    @Test
    fun `ok false with no code is a failure, not a success`() {
        reply(500, """{"ok":false}""")

        val result = scan()

        assertTrue("expected a Failure, got $result", result is ScanResult.Failure)
    }

    @Test
    fun `a reply with no ok at all is a failure, not a success`() {
        reply(200, """{"fields":{"vin":"1"}}""")

        val result = scan()

        assertTrue("expected a Failure, got $result", result is ScanResult.Failure)
    }
}
