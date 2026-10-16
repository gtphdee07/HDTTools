package com.rigcheck.app.data

import com.rigcheck.app.ui.navigation.EntryModule
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

// The already-deployed, already-verified (2026-08-17) Worker - see
// workers/scan-proxy/README.md for the full contract this client
// implements: POST /v1/scan with an `Authorization: Bearer <account token>`
// header, {doc_type, image_base64, media_type} ->
// {ok:true, doc_type, fields} or {ok:false, code, message}.
private const val SCAN_ENDPOINT = "https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev/v1/scan"
private val JSON_MEDIA_TYPE = "application/json".toMediaType()

sealed interface ScanResult {
    data class Success(val fields: JsonObject) : ScanResult
    // code matches the Worker's error taxonomy: insufficient_credits,
    // extraction_failed, billing_error, bad_request - plus client-side
    // network_error/parse_error for transport failures.
    data class Failure(val code: String, val message: String) : ScanResult
}

fun EntryModule.toDocType(): String = when (this) {
    EntryModule.TRUCK -> "truck_tag"
    EntryModule.TRAILER -> "trailer_tag"
    EntryModule.SCALE -> "scale_ticket"
}

// The Worker takes the account to charge from the signed-in user's access
// token and ignores any user id in the body, so none is sent.
internal fun buildScanRequest(
    accessToken: String,
    module: EntryModule,
    imageBase64: String,
    mediaType: String,
    clientRequestId: String?,
    endpoint: String = SCAN_ENDPOINT,
): Request {
    val requestJson = buildJsonObject {
        put("doc_type", module.toDocType())
        put("image_base64", imageBase64)
        put("media_type", mediaType)
        clientRequestId?.let { put("client_request_id", it) }
    }
    return Request.Builder()
        .url(endpoint)
        .header("Authorization", "Bearer $accessToken")
        .post(requestJson.toString().toRequestBody(JSON_MEDIA_TYPE))
        .build()
}

object ScanApiClient {
    private val http = ScanHttp(
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .build(),
        SCAN_ENDPOINT,
    )

    // No client-side auto-retry on failure, deliberately - the Worker
    // already charges-then-refunds server-side; a client retry after a
    // lost response risks a redundant paid Claude call.
    suspend fun scan(
        accessToken: String,
        module: EntryModule,
        imageBase64: String,
        mediaType: String = "image/jpeg",
        // Stable across retries of the same logical scan attempt - lets the
        // Worker dedupe the RevenueCat charge if a retry follows a
        // lost/timed-out response. Optional and omittable: absent falls
        // back to the Worker's own random-key behavior.
        clientRequestId: String? = null,
    ): ScanResult = http.scan(accessToken, module, imageBase64, mediaType, clientRequestId)
}

private val replyJson = Json { ignoreUnknownKeys = true }

// Any reply that is not the Worker's documented shape is a parse_error. It
// must never throw: a throw inside the OkHttp callback would leave the scan
// waiting for an answer that never comes.
internal fun readScanReply(body: String): ScanResult = runCatching {
    val parsed = replyJson.parseToJsonElement(body).jsonObject
    if (parsed["ok"]?.jsonPrimitive?.boolean ?: false) {
        ScanResult.Success(parsed["fields"]?.jsonObject ?: JsonObject(emptyMap()))
    } else {
        val code = parsed["code"]?.jsonPrimitive?.contentOrNull ?: "unknown_error"
        val message = parsed["message"]?.jsonPrimitive?.contentOrNull ?: "Unknown error."
        ScanResult.Failure(code, message)
    }
}.getOrElse { ScanResult.Failure("parse_error", "Could not parse the server's response.") }

// The send-and-read half of the client, with the HTTP client and endpoint
// passed in so tests can point it at a fake server.
internal class ScanHttp(private val client: OkHttpClient, private val endpoint: String) {
    suspend fun scan(
        accessToken: String,
        module: EntryModule,
        imageBase64: String,
        mediaType: String,
        clientRequestId: String?,
    ): ScanResult {
        val request = buildScanRequest(accessToken, module, imageBase64, mediaType, clientRequestId, endpoint)

        return suspendCancellableCoroutine { continuation ->
            val call = client.newCall(request)
            continuation.invokeOnCancellation { call.cancel() }
            call.enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    continuation.resume(ScanResult.Failure("network_error", e.message ?: "Network error"))
                }

                override fun onResponse(call: Call, response: Response) {
                    response.use { resp ->
                        val bodyString = resp.body?.string().orEmpty()
                        continuation.resume(readScanReply(bodyString))
                    }
                }
            })
        }
    }
}
