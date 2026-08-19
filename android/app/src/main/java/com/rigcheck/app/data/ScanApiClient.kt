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
// implements: POST /v1/scan, {app_user_id, doc_type, image_base64,
// media_type} -> {ok:true, doc_type, fields} or {ok:false, code, message}.
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

object ScanApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()
    private val json = Json { ignoreUnknownKeys = true }

    // No client-side auto-retry on failure, deliberately - the Worker
    // already charges-then-refunds server-side; a client retry after a
    // lost response risks a redundant paid Claude call.
    suspend fun scan(
        appUserId: String,
        module: EntryModule,
        imageBase64: String,
        mediaType: String = "image/jpeg",
    ): ScanResult {
        val requestJson = buildJsonObject {
            put("app_user_id", appUserId)
            put("doc_type", module.toDocType())
            put("image_base64", imageBase64)
            put("media_type", mediaType)
        }
        val body = requestJson.toString().toRequestBody(JSON_MEDIA_TYPE)
        val request = Request.Builder().url(SCAN_ENDPOINT).post(body).build()

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
                        val parsed = runCatching { json.parseToJsonElement(bodyString).jsonObject }.getOrNull()
                        if (parsed == null) {
                            continuation.resume(ScanResult.Failure("parse_error", "Could not parse the server's response."))
                            return
                        }
                        val ok = parsed["ok"]?.jsonPrimitive?.boolean ?: false
                        if (ok) {
                            val fields = parsed["fields"]?.jsonObject ?: JsonObject(emptyMap())
                            continuation.resume(ScanResult.Success(fields))
                        } else {
                            val code = parsed["code"]?.jsonPrimitive?.contentOrNull ?: "unknown_error"
                            val message = parsed["message"]?.jsonPrimitive?.contentOrNull ?: "Unknown error."
                            continuation.resume(ScanResult.Failure(code, message))
                        }
                    }
                }
            })
        }
    }
}
