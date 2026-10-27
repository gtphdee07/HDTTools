package com.rigcheck.app.data

import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
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
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

// The Garage over Supabase's REST API, with the server faked at the HTTP level: what the app sends to PostgREST
// and how it reads the answer, including the way the database says a Garage is full. The cap and the idempotency
// themselves live in the database (garageSchema.test.ts on Web runs that SQL); this pins that Android asks the
// way Web does.
class SupabaseGarageBackendTest {

    private val requests = mutableListOf<HttpRequestData>()

    private fun backend(handler: MockRequestHandleScope.(HttpRequestData) -> HttpResponseData): SupabaseGarageBackend {
        val client = createSupabaseClient("https://example.supabase.co", "publishable-key") {
            httpEngine = MockEngine { request ->
                requests += request
                handler(request)
            }
            install(Postgrest)
        }
        return SupabaseGarageBackend(client)
    }

    private fun MockRequestHandleScope.json(body: String, status: HttpStatusCode = HttpStatusCode.OK) =
        respond(body, status, headersOf(HttpHeaders.ContentType, "application/json"))

    private fun bodyOf(request: HttpRequestData): JsonObject =
        Json.parseToJsonElement((request.body as TextContent).text).jsonObject

    private val rig = RecentRig(
        nickname = "  Goose + Addie ",
        truck = TruckTag(description = "F-450", gvwrLb = 14_000.0),
        trailer = TrailerTag(description = "Brinkley", axleCount = 2),
        lastUsedAt = "2026-10-22T00:00:00Z",
        id = "rig-1",
    )

    @Test
    fun `the account's Rigs are read newest first and open with the figures Web saved`() = runTest {
        val backend = backend {
            json(
                """[{"id":"rig-1","nickname":"Goose","truck":{"manufacturer":"Ford","gvwr_lb":14000,"vin":"V1"},
                    "trailer":{"manufacturer":"Brinkley","axle_count":2},"last_used_at":"2026-10-22T12:00:00.5+00:00"}]""",
            )
        }

        val rigs = backend.list()

        assertEquals(HttpMethod.Get, requests.single().method)
        assertEquals("/rest/v1/garage_rigs", requests.single().url.encodedPath)
        assertTrue(requests.single().url.parameters["order"]!!.startsWith("last_used_at.desc"))
        val rig = rigs.single()
        assertEquals("rig-1", rig.id)
        assertEquals(TruckTag(description = "Ford", gvwrLb = 14_000.0), rig.truck)
        assertEquals(TrailerTag(description = "Brinkley", axleCount = 2), rig.trailer)
        assertEquals(JsonPrimitive("V1"), rig.truckExtra["vin"])
        assertEquals("2026-10-22T12:00:00.500Z", rig.lastUsedAt)
    }

    @Test
    fun `an add goes through add_rig with the key, the trimmed nickname, the Web field names and the plan`() = runTest {
        val backend = backend { json("{}") }

        backend.addRig("key-1", rig, isPro = true)

        val request = requests.single()
        assertEquals(HttpMethod.Post, request.method)
        assertEquals("/rest/v1/rpc/add_rig", request.url.encodedPath)
        val body = bodyOf(request)
        assertEquals("key-1", body.getValue("p_idempotency_key").jsonPrimitive.content)
        assertEquals("Goose + Addie", body.getValue("p_nickname").jsonPrimitive.content)
        assertEquals(14_000.0, body.getValue("p_truck").jsonObject.getValue("gvwr_lb").jsonPrimitive.content.toDouble(), 0.0)
        assertEquals("F-450", body.getValue("p_truck").jsonObject.getValue("manufacturer").jsonPrimitive.content)
        assertEquals(true, body.getValue("p_pro").jsonPrimitive.boolean)
    }

    @Test
    fun `a Free account's add says false and one whose plan is unknown says null`() = runTest {
        val backend = backend { json("{}") }

        backend.addRig("key-1", rig, isPro = false)
        backend.addRig("key-2", rig, isPro = null)

        assertEquals(false, bodyOf(requests[0]).getValue("p_pro").jsonPrimitive.boolean)
        assertEquals(JsonNull, bodyOf(requests[1]).getValue("p_pro"))
    }

    @Test
    fun `the database's garage_full is a full Garage that names its cap`() = runTest {
        val backend = backend {
            json(
                """{"code":"P0001","details":"5","hint":null,"message":"garage_full"}""",
                HttpStatusCode.BadRequest,
            )
        }

        try {
            backend.addRig("key-1", rig, isPro = false)
            fail("a full Garage should be refused")
        } catch (e: GarageFullException) {
            assertEquals(5, e.cap)
        }
    }

    @Test
    fun `any other database error is a failure, not a full Garage`() = runTest {
        val backend = backend {
            json("""{"code":"P0001","details":null,"hint":null,"message":"plan_caps_missing"}""", HttpStatusCode.BadRequest)
        }

        try {
            backend.addRig("key-1", rig, isPro = false)
            fail("the error should be raised")
        } catch (e: GarageFullException) {
            fail("not a full Garage: $e")
        } catch (e: Exception) {
            assertEquals("plan_caps_missing", e.message)
        }
    }

    @Test
    fun `using a Rig rewrites its tags and last-used time, and only that Rig`() = runTest {
        val backend = backend { json("""[{"id":"rig-1"}]""") }

        backend.updateRig(rig)

        val request = requests.single()
        assertEquals(HttpMethod.Patch, request.method)
        assertEquals("eq.rig-1", request.url.parameters["id"])
        val body = bodyOf(request)
        assertEquals("2026-10-22T00:00:00Z", body.getValue("last_used_at").jsonPrimitive.content)
        assertEquals("F-450", body.getValue("truck").jsonObject.getValue("manufacturer").jsonPrimitive.content)
        assertTrue("nickname and ownership are not rewritten", "nickname" !in body && "user_id" !in body)
    }

    @Test
    fun `an update that matched no Rig fails, so the caller adds it`() = runTest {
        val backend = backend { json("[]") }

        try {
            backend.updateRig(rig)
            fail("a Rig that is gone should not look updated")
        } catch (e: IllegalStateException) {
            assertEquals("rig_not_found", e.message)
        }
    }

    @Test
    fun `a delete removes only that Rig, by its id`() = runTest {
        val backend = backend { respond("", HttpStatusCode.NoContent) }

        backend.deleteRig("rig-1")

        val request = requests.single()
        assertEquals(HttpMethod.Delete, request.method)
        assertEquals("/rest/v1/garage_rigs", request.url.encodedPath)
        assertEquals("eq.rig-1", request.url.parameters["id"])
    }

    // PostgREST answers a delete that matched no row (the Rig is already gone) with success too.
    @Test
    fun `deleting a Rig that is already gone is not an error`() = runTest {
        val backend = backend { respond("", HttpStatusCode.NoContent) }

        backend.deleteRig("rig-already-deleted")

        assertEquals(1, requests.size)
    }

    @Test
    fun `a delete the database refuses fails, so the Rig stays`() = runTest {
        val backend = backend { json("""{"message":"permission denied"}""", HttpStatusCode.Forbidden) }

        try {
            backend.deleteRig("rig-1")
            fail("a refused delete should not look done")
        } catch (_: Exception) {
        }
    }
}
