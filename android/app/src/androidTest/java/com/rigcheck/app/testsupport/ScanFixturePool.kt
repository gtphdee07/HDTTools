package com.rigcheck.app.testsupport

import kotlin.random.Random
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

// Android-side mirror of scripts/vehicle_discovery.py (item #13,
// FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md, NEXT_STEPS.md): walks
// scans/<truck|trailer|scale>/<vehicle_slug>/ for a vehicle.json sidecar
// (same schema as the Python side - {"pool": "pass", "fields": {...}}
// or {"pool": "fail", "expected_none_fields": [...]}) plus every image
// file already sitting next to it. Test-support only - stays out of
// main/ (the app's shipped source), mirroring scripts/pass_pool.py's own
// "test infrastructure, not application code" rule.
//
// Pass-pool and fail-pool are kept as two separate maps (mirroring
// vehicle_discovery.py's own {"pass_pool": {...}, "fail_pool": {...}}
// split) rather than one map keyed only by doc_type - a single combined
// map would let a random pick for "truck_tag" land on either a pass-pool
// or a fail-pool vehicle, which is never the right behavior for either
// caller.

data class ScanFixtureVehicle(
    val vehicle: String,
    val images: List<String>,
    val fields: JsonObject?,
    val expectedNoneFields: List<String>?,
)

data class ScanFixturePools(
    val passPool: Map<String, List<ScanFixtureVehicle>>,
    val failPool: Map<String, List<ScanFixtureVehicle>>,
)

private val DOC_TYPE_BY_BUCKET = mapOf(
    "truck" to "truck_tag",
    "trailer" to "trailer_tag",
    "scale" to "scale_ticket",
)
private val IMAGE_EXTENSIONS = listOf(".jpg", ".jpeg", ".png")
private const val ROOT = "scans"

object ScanFixturePool {

    fun discover(source: FixtureFileSource): ScanFixturePools {
        val passPool = mutableMapOf<String, MutableList<ScanFixtureVehicle>>()
        val failPool = mutableMapOf<String, MutableList<ScanFixtureVehicle>>()

        for (bucket in source.list(ROOT)) {
            val docType = DOC_TYPE_BY_BUCKET[bucket] ?: continue

            for (vehicleSlug in source.list("$ROOT/$bucket")) {
                val vehiclePath = "$ROOT/$bucket/$vehicleSlug"
                val entries = source.list(vehiclePath)
                if ("vehicle.json" !in entries) continue

                val (pool, vehicle) = parseVehicle(source, vehiclePath, vehicleSlug, entries)
                val target = if (pool == "pass") passPool else failPool
                target.getOrPut(docType) { mutableListOf() }.add(vehicle)
            }
        }

        return ScanFixturePools(passPool, failPool)
    }

    fun resolveRandom(
        source: FixtureFileSource,
        pool: String,
        docType: String,
        random: Random = Random,
    ): Pair<String, ScanFixtureVehicle> {
        require(pool == "pass" || pool == "fail") { "pool must be 'pass' or 'fail', got '$pool'" }
        val pools = discover(source)
        val vehicles = (if (pool == "pass") pools.passPool else pools.failPool)[docType]
        require(!vehicles.isNullOrEmpty()) { "no $pool-pool vehicles registered for doc_type '$docType'" }

        val vehicle = vehicles[random.nextInt(vehicles.size)]
        val image = vehicle.images[random.nextInt(vehicle.images.size)]
        return image to vehicle
    }

    private fun parseVehicle(
        source: FixtureFileSource,
        vehiclePath: String,
        vehicleSlug: String,
        entries: List<String>,
    ): Pair<String, ScanFixtureVehicle> {
        val sidecarPath = "$vehiclePath/vehicle.json"
        val sidecar = Json.parseToJsonElement(source.readText(sidecarPath)).jsonObject
        val pool = sidecar["pool"]?.jsonPrimitive?.contentOrNull
        require(pool == "pass" || pool == "fail") {
            "$sidecarPath: 'pool' must be 'pass' or 'fail', got $pool"
        }

        val images = entries
            .filter { it != "vehicle.json" && IMAGE_EXTENSIONS.any { ext -> it.endsWith(ext, ignoreCase = true) } }
            .sorted()
            .map { "$vehiclePath/$it" }
        require(images.isNotEmpty()) { "$vehiclePath: has a vehicle.json but no image files" }

        val fields = sidecar["fields"]?.jsonObject
        val expectedNoneFields = sidecar["expected_none_fields"]?.jsonArray?.map { it.jsonPrimitive.content }

        if (pool == "pass") {
            requireNotNull(fields) { "$sidecarPath: pass-pool vehicle.json needs a 'fields' object" }
        } else {
            requireNotNull(expectedNoneFields) { "$sidecarPath: fail-pool vehicle.json needs an 'expected_none_fields' list" }
        }

        return pool to ScanFixtureVehicle(vehicleSlug, images, fields, expectedNoneFields)
    }
}
