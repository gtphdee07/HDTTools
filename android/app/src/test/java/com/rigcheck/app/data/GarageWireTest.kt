package com.rigcheck.app.data

import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// The Garage is shared with Web, which stores a Rig's truck and trailer in its own field names (the Core
// tag shape: snake_case, `manufacturer`, `vehicle_name`). A Rig added on one app must open on the other with
// the same figures, and saving it from here must not erase what only Web keeps (a VIN, tire sizes).
class GarageWireTest {

    // A Rig as Web saves it, with fields Android has no place for.
    private val webTruck = buildJsonObject {
        put("manufacturer", "Ford F-450")
        put("vehicle_name", "Goose")
        put("gvwr_lb", 14_000.0)
        put("front_gawr_lb", 6_000.0)
        put("rear_gawr_lb", 9_750.0)
        put("standalone_weight_lb", 8_400.0)
        put("gcwr_lb", 32_000.0)
        put("vin", "1FT8W4DT0NEC00000")
        put("front_tire", buildJsonObject { put("size", "275/70R18") })
    }
    private val webTrailer = buildJsonObject {
        put("manufacturer", "Brinkley G-4170")
        put("vehicle_name", "Addie")
        put("gvwr_lb", 16_000.0)
        put("gawr_per_axle_lb", 8_000.0)
        put("uvw_lb", 11_900.0)
        put("axle_count", 2)
        put("date", "2024-03")
    }

    @Test
    fun `a Rig saved on Web opens on Android with the same figures`() {
        val rig = rigFromGarageRow("r1", "Goose + Addie", webTruck, webTrailer, "2026-10-22T12:00:00Z")

        assertEquals(
            TruckTag(
                description = "Ford F-450",
                name = "Goose",
                gvwrLb = 14_000.0,
                frontGawrLb = 6_000.0,
                rearGawrLb = 9_750.0,
                standaloneWeightLb = 8_400.0,
                gcwrLb = 32_000.0,
            ),
            rig.truck,
        )
        assertEquals(
            TrailerTag(
                description = "Brinkley G-4170",
                name = "Addie",
                gvwrLb = 16_000.0,
                gawrPerAxleLb = 8_000.0,
                axleCount = 2,
                uvwLb = 11_900.0,
            ),
            rig.trailer,
        )
        assertEquals("r1", rig.id)
        assertEquals("Goose + Addie", rig.nickname)
    }

    @Test
    fun `a Rig saved on Android is written in the names Web reads`() {
        val rig = RecentRig(
            nickname = "Weekender",
            truck = TruckTag(description = "Ram 3500", name = "Ram", gvwrLb = 14_000.0, gcwrLb = 30_000.0),
            trailer = TrailerTag(description = "Keystone", gawrPerAxleLb = 7_000.0, axleCount = 2),
            lastUsedAt = "2026-10-22T12:00:00Z",
        )

        assertEquals(
            buildJsonObject {
                put("manufacturer", "Ram 3500")
                put("vehicle_name", "Ram")
                put("gvwr_lb", 14_000.0)
                put("gcwr_lb", 30_000.0)
            },
            garageTruckJson(rig),
        )
        assertEquals(
            buildJsonObject {
                put("manufacturer", "Keystone")
                put("gawr_per_axle_lb", 7_000.0)
                put("axle_count", 2)
            },
            garageTrailerJson(rig),
        )
    }

    @Test
    fun `saving a Web Rig from Android keeps the fields only Web uses`() {
        val fromWeb = rigFromGarageRow("r1", "Goose", webTruck, webTrailer, "2026-10-22T12:00:00Z")

        val saved = fromWeb.copy(truck = fromWeb.truck.copy(gvwrLb = 14_500.0))

        val written = garageTruckJson(saved)
        assertEquals(JsonPrimitive("1FT8W4DT0NEC00000"), written["vin"])
        assertEquals(buildJsonObject { put("size", "275/70R18") }, written["front_tire"])
        assertEquals(JsonPrimitive(14_500.0), written["gvwr_lb"])
        assertEquals(JsonPrimitive("2024-03"), garageTrailerJson(saved)["date"])
    }

    @Test
    fun `a figure cleared on Android is cleared in the account, not left at its old value`() {
        val fromWeb = rigFromGarageRow("r1", "Goose", webTruck, webTrailer, "2026-10-22T12:00:00Z")

        val saved = fromWeb.copy(truck = fromWeb.truck.copy(gcwrLb = null, description = null))

        val written = garageTruckJson(saved)
        assertTrue("gcwr_lb should be gone", "gcwr_lb" !in written)
        assertTrue("manufacturer should be gone", "manufacturer" !in written)
    }

    @Test
    fun `a Rig whose truck has nothing Android knows still opens`() {
        val rig = rigFromGarageRow("r1", "Bare", JsonObject(emptyMap()), JsonObject(emptyMap()), "2026-10-22T12:00:00Z")

        assertEquals(TruckTag(), rig.truck)
        assertEquals(TrailerTag(), rig.trailer)
    }

    @Test
    fun `a figure of the wrong kind in the account is ignored, not a crash`() {
        val odd = buildJsonObject {
            put("gvwr_lb", "heavy")
            put("front_gawr_lb", JsonNull)
            put("manufacturer", 12)
            put("vehicle_name", buildJsonObject { put("first", "Goose") })
            put("rear_gawr_lb", 9_000.0)
        }

        val rig = rigFromGarageRow("r1", "Odd", odd, JsonObject(emptyMap()), "2026-10-22T12:00:00Z")

        assertEquals(TruckTag(rearGawrLb = 9_000.0), rig.truck)
    }

    // PostgREST answers timestamptz as "2026-10-22T12:00:00.123456+00:00"; the Rig picker's "Last checked"
    // line parses ISO instants ("...Z") and shows nothing for anything else.
    @Test
    fun `the last-used time from the account reads as an instant the Rig picker can show`() {
        val rig = rigFromGarageRow("r1", "Goose", webTruck, webTrailer, "2026-10-22T12:00:00.123456+00:00")

        assertEquals("2026-10-22T12:00:00.123456Z", rig.lastUsedAt)
    }

    @Test
    fun `a last-used time in an unexpected form is kept as it came`() {
        val rig = rigFromGarageRow("r1", "Goose", webTruck, webTrailer, "yesterday")

        assertEquals("yesterday", rig.lastUsedAt)
    }

    @Test
    fun `the account's nickname is shown trimmed`() {
        val rig = rigFromGarageRow("r1", "  Goose ", webTruck, webTrailer, "2026-10-22T12:00:00Z")

        assertEquals("Goose", rig.nickname)
    }

    // The database named the cap in the error's details; a message the app does not know is a failure to save,
    // not a full Garage.
    @Test
    fun `the database's garage_full answer becomes a full Garage with its cap`() {
        val failure = garageFailureFor(message = "garage_full", details = "25")

        assertTrue(failure is GarageFullException)
        assertEquals(25, (failure as GarageFullException).cap)
    }

    @Test
    fun `a full Garage whose cap the database did not name has no cap`() {
        assertEquals(null, (garageFailureFor("garage_full", null) as GarageFullException).cap)
        assertEquals(null, (garageFailureFor("garage_full", "lots") as GarageFullException).cap)
    }

    @Test
    fun `any other database error is not a full Garage`() {
        val failure = garageFailureFor("plan_caps_missing", null)

        assertTrue(failure !is GarageFullException)
        assertEquals("plan_caps_missing", failure.message)
    }
}
