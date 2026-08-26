package com.rigcheck.app.testsupport

import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlin.random.Random
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

// Function tests for ScanFixturePool's directory-convention discovery -
// the Android-side mirror of scripts/vehicle_discovery.py (item #13,
// NEXT_STEPS.md). Uses a fake, in-memory FixtureFileSource rather than a
// real AssetManager, so this runs free of real network/device-asset
// dependencies even though it's in the instrumented (androidTest) source
// set - androidTest code can't be referenced from the JVM-only test
// source set without moving it into main/, which would ship test-support
// code inside the app.
private class FakeFixtureFileSource(
    private val listings: Map<String, List<String>>,
    private val files: Map<String, String>,
) : FixtureFileSource {
    override fun list(path: String): List<String> = listings[path] ?: emptyList()
    override fun readText(path: String): String = files[path] ?: error("no fake file at $path")
}

@RunWith(AndroidJUnit4::class)
class ScanFixturePoolTest {

    @Test
    fun discoversAPassPoolVehicleWithFields() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("truck"),
                "scans/truck" to listOf("chevy_silverado"),
                "scans/truck/chevy_silverado" to listOf("vehicle.json", "photo.jpg"),
            ),
            files = mapOf(
                "scans/truck/chevy_silverado/vehicle.json" to
                    """{"pool": "pass", "fields": {"manufacturer": "CHEVROLET", "gvwr_lb": 10000.0}}""",
            ),
        )

        val vehicles = ScanFixturePool.discover(source).passPool.getValue("truck_tag")

        assertEquals(1, vehicles.size)
        assertEquals("chevy_silverado", vehicles[0].vehicle)
        assertEquals(listOf("scans/truck/chevy_silverado/photo.jpg"), vehicles[0].images)
        assertEquals("CHEVROLET", vehicles[0].fields?.get("manufacturer")?.jsonPrimitive?.contentOrNull)
    }

    @Test
    fun discoversAFailPoolVehicleWithExpectedNoneFields() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("trailer"),
                "scans/trailer" to listOf("unreadable_rv"),
                "scans/trailer/unreadable_rv" to listOf("vehicle.json", "a.jpg", "b.png"),
            ),
            files = mapOf(
                "scans/trailer/unreadable_rv/vehicle.json" to
                    """{"pool": "fail", "expected_none_fields": ["manufacturer", "gvwr_lb"]}""",
            ),
        )

        val vehicles = ScanFixturePool.discover(source).failPool.getValue("trailer_tag")

        assertEquals(
            listOf("scans/trailer/unreadable_rv/a.jpg", "scans/trailer/unreadable_rv/b.png"),
            vehicles[0].images,
        )
        assertEquals(listOf("manufacturer", "gvwr_lb"), vehicles[0].expectedNoneFields)
    }

    // Real bug caught while writing this: an earlier version of
    // ScanFixturePool.discover() returned one map keyed only by doc_type,
    // mixing pass-pool and fail-pool vehicles under the same "truck_tag"
    // key - a random pick could then land on either pool regardless of
    // which one the caller actually wanted. Both pools sharing a doc_type
    // is exactly the real shape (this repo's own pass-pool and fail-pool
    // truck fixtures both use "truck_tag"), so this case guards it directly.
    @Test
    fun passPoolAndFailPoolVehiclesForTheSameDocTypeStayInSeparatePools() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("truck"),
                "scans/truck" to listOf("good_vehicle", "bad_vehicle"),
                "scans/truck/good_vehicle" to listOf("vehicle.json", "good.jpg"),
                "scans/truck/bad_vehicle" to listOf("vehicle.json", "bad.jpg"),
            ),
            files = mapOf(
                "scans/truck/good_vehicle/vehicle.json" to """{"pool": "pass", "fields": {"gvwr_lb": 14000.0}}""",
                "scans/truck/bad_vehicle/vehicle.json" to """{"pool": "fail", "expected_none_fields": ["gvwr_lb"]}""",
            ),
        )

        val pools = ScanFixturePool.discover(source)

        assertEquals(listOf("good_vehicle"), pools.passPool.getValue("truck_tag").map { it.vehicle })
        assertEquals(listOf("bad_vehicle"), pools.failPool.getValue("truck_tag").map { it.vehicle })

        val (passImage, _) = ScanFixturePool.resolveRandom(source, "pass", "truck_tag", Random(1))
        assertEquals("scans/truck/good_vehicle/good.jpg", passImage)
        val (failImage, _) = ScanFixturePool.resolveRandom(source, "fail", "truck_tag", Random(1))
        assertEquals("scans/truck/bad_vehicle/bad.jpg", failImage)
    }

    @Test
    fun ignoresAVehicleDirectoryWithNoVehicleJson() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("truck"),
                "scans/truck" to listOf("stray_photos_only"),
                "scans/truck/stray_photos_only" to listOf("photo.jpg"),
            ),
            files = emptyMap(),
        )

        val pools = ScanFixturePool.discover(source)
        assertTrue(pools.passPool.isEmpty())
        assertTrue(pools.failPool.isEmpty())
    }

    @Test
    fun resolveRandomPicksAmongMultipleRegisteredVehicles() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("truck"),
                "scans/truck" to listOf("vehicle_a", "vehicle_b"),
                "scans/truck/vehicle_a" to listOf("vehicle.json", "a.jpg"),
                "scans/truck/vehicle_b" to listOf("vehicle.json", "b.jpg"),
            ),
            files = mapOf(
                "scans/truck/vehicle_a/vehicle.json" to """{"pool": "pass", "fields": {}}""",
                "scans/truck/vehicle_b/vehicle.json" to """{"pool": "pass", "fields": {}}""",
            ),
        )

        val picks = (1..20).map { ScanFixturePool.resolveRandom(source, "pass", "truck_tag", Random(it)).first }
        assertTrue("expected both vehicles to be reachable across seeds", picks.toSet().size == 2)
    }

    @Test(expected = IllegalArgumentException::class)
    fun aPassPoolEntryMissingFieldsThrows() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("truck"),
                "scans/truck" to listOf("no_fields"),
                "scans/truck/no_fields" to listOf("vehicle.json", "photo.jpg"),
            ),
            files = mapOf("scans/truck/no_fields/vehicle.json" to """{"pool": "pass"}"""),
        )

        ScanFixturePool.discover(source)
    }

    @Test(expected = IllegalArgumentException::class)
    fun aVehicleFolderWithNoImagesThrows() {
        val source = FakeFixtureFileSource(
            listings = mapOf(
                "scans" to listOf("truck"),
                "scans/truck" to listOf("no_images"),
                "scans/truck/no_images" to listOf("vehicle.json"),
            ),
            files = mapOf("scans/truck/no_images/vehicle.json" to """{"pool": "pass", "fields": {}}"""),
        )

        ScanFixturePool.discover(source)
    }
}
