package com.rigcheck.app.data

import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okio.Buffer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

// The scan service charges whichever account the bearer token names and
// ignores any user id in the body (workers/scan-proxy README, "Auth"), so
// the request on the wire is the contract worth pinning here.
class ScanApiClientTest {

    private fun bodyOf(request: okhttp3.Request) =
        Json.parseToJsonElement(Buffer().also { request.body!!.writeTo(it) }.readUtf8()).jsonObject

    @Test
    fun `scan requests carry the account token as a bearer credential`() {
        val request = buildScanRequest("jwt-abc", EntryModule.TRUCK, "aGk=", "image/jpeg", clientRequestId = null)

        assertEquals("Bearer jwt-abc", request.header("Authorization"))
    }

    @Test
    fun `scan requests no longer name a user in the body`() {
        val body = bodyOf(buildScanRequest("jwt-abc", EntryModule.TRAILER, "aGk=", "image/jpeg", clientRequestId = "req-1"))

        assertFalse("app_user_id" in body)
        assertEquals("trailer_tag", body["doc_type"]!!.jsonPrimitive.content)
        assertEquals("aGk=", body["image_base64"]!!.jsonPrimitive.content)
        assertEquals("req-1", body["client_request_id"]!!.jsonPrimitive.content)
    }

    @Test
    fun `scan requests omit the idempotency key when none is given`() {
        val body = bodyOf(buildScanRequest("jwt-abc", EntryModule.SCALE, "aGk=", "image/jpeg", clientRequestId = null))

        assertFalse("client_request_id" in body)
    }
}
