package com.rigcheck.app.data

import com.rigcheck.app.domain.VerdictStatus
import io.github.jan.supabase.createSupabaseClient
import io.github.jan.supabase.postgrest.Postgrest
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.MockRequestHandleScope
import io.ktor.client.engine.mock.respond
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.content.TextContent
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

// The History over Supabase's REST API, with the server faked at the HTTP level: what the app sends to
// PostgREST and how it reads the answer. The cap and the idempotency themselves live in the database
// (historySchema.test.ts on Web runs that SQL); this pins that Android asks the way Web does.
class SupabaseHistoryBackendTest {

    private val requests = mutableListOf<HttpRequestData>()

    private fun backend(handler: MockRequestHandleScope.(HttpRequestData) -> HttpResponseData): SupabaseHistoryBackend {
        val client = createSupabaseClient("https://example.supabase.co", "publishable-key") {
            httpEngine = MockEngine { request ->
                requests += request
                handler(request)
            }
            install(Postgrest)
        }
        return SupabaseHistoryBackend(client)
    }

    private fun MockRequestHandleScope.json(body: String, status: HttpStatusCode = HttpStatusCode.OK) =
        respond(body, status, headersOf(HttpHeaders.ContentType, "application/json"))

    private fun bodyOf(request: HttpRequestData): JsonObject =
        Json.parseToJsonElement((request.body as TextContent).text).jsonObject

    @Test
    fun `the account's checks are read in insertion order, newest first, as Web does`() = runTest {
        val backend = backend {
            json(
                """[{"id":"e-2","rig_nickname":" Goose ","verdict":"fail","checked_at":"2026-10-22T12:00:00.5+00:00"},
                    {"id":"e-1","rig_nickname":"Addie","verdict":"pass","checked_at":"2026-10-21T08:00:00+00:00"}]""",
            )
        }

        val entries = backend.list()

        assertEquals(HttpMethod.Get, requests.single().method)
        assertEquals("/rest/v1/history_entries", requests.single().url.encodedPath)
        assertTrue(requests.single().url.parameters["order"]!!.startsWith("seq.desc"))
        assertEquals(
            listOf(
                HistoryEntry("e-2", "2026-10-22T12:00:00.500Z", "Goose", VerdictStatus.FAIL),
                HistoryEntry("e-1", "2026-10-21T08:00:00Z", "Addie", VerdictStatus.PASS),
            ),
            entries,
        )
    }

    @Test
    fun `a check goes through add_history_entry with the key, the trimmed nickname, the verdict word and the plan`() = runTest {
        val backend = backend { json("{}") }

        backend.addEntry("key-1", "  Goose + Addie ", VerdictStatus.PARTIAL, isPro = true)

        val request = requests.single()
        assertEquals(HttpMethod.Post, request.method)
        assertEquals("/rest/v1/rpc/add_history_entry", request.url.encodedPath)
        val body = bodyOf(request)
        assertEquals("key-1", body.getValue("p_idempotency_key").jsonPrimitive.content)
        assertEquals("Goose + Addie", body.getValue("p_rig_nickname").jsonPrimitive.content)
        assertEquals("partial", body.getValue("p_verdict").jsonPrimitive.content)
        assertEquals(true, body.getValue("p_pro").jsonPrimitive.boolean)
    }

    @Test
    fun `a Free account's add says false and one whose plan is unknown says null`() = runTest {
        val backend = backend { json("{}") }

        backend.addEntry("key-1", "Goose", VerdictStatus.PASS, isPro = false)
        backend.addEntry("key-2", "Goose", VerdictStatus.PASS, isPro = null)

        assertEquals(false, bodyOf(requests[0]).getValue("p_pro").jsonPrimitive.boolean)
        assertEquals(JsonNull, bodyOf(requests[1]).getValue("p_pro"))
    }

    @Test
    fun `a database error on an add is raised, so the caller can retry and then say it was not saved`() = runTest {
        val backend = backend {
            json("""{"code":"P0001","details":null,"hint":null,"message":"plan_caps_missing"}""", HttpStatusCode.BadRequest)
        }

        try {
            backend.addEntry("key-1", "Goose", VerdictStatus.PASS, isPro = false)
            fail("the error should be raised")
        } catch (e: Exception) {
            assertTrue(e.message!!.contains("plan_caps_missing"))
        }
    }

    @Test
    fun `the caps are the history counts of the free and pro rows`() = runTest {
        val backend = backend {
            json("""[{"plan":"pro","history_cap":50},{"plan":"free","history_cap":10}]""")
        }

        val caps = backend.caps()

        assertEquals("/rest/v1/plan_caps", requests.single().url.encodedPath)
        assertEquals(HistoryCaps(free = 10, pro = 50), caps)
    }

    @Test
    fun `caps with a plan missing are an error, not a guess`() = runTest {
        val backend = backend { json("""[{"plan":"free","history_cap":10}]""") }

        try {
            backend.caps()
            fail("a missing Pro row should not be filled in")
        } catch (e: IllegalStateException) {
            assertEquals("plan_caps_missing", e.message)
        }
    }
}
