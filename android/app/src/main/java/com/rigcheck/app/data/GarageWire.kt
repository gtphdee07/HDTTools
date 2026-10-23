package com.rigcheck.app.data

import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import java.time.OffsetDateTime
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

// How a Rig is stored in the account's Garage (the `garage_rigs` table, supabase/migrations/
// 20261010000000_garage_rigs.sql). Web writes a Rig's truck and trailer in the Core tag shape (snake_case,
// `manufacturer`, `vehicle_name`); Android's TruckTag/TrailerTag are the same data under their own names, so
// a Rig added on either app opens on the other. `description` is the tag's `manufacturer`, as in
// ScanFieldMapping. Fields Android has no place for stay in RecentRig.truckExtra/trailerExtra.

private val TRUCK_KEYS = setOf(
    "manufacturer", "vehicle_name", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb", "standalone_weight_lb", "gcwr_lb",
)
private val TRAILER_KEYS = setOf(
    "manufacturer", "vehicle_name", "gvwr_lb", "gawr_per_axle_lb", "axle_count", "uvw_lb",
)

// A figure of the wrong kind (text where a number belongs, an object, null) reads as not entered.
private fun JsonObject.text(key: String): String? =
    (this[key] as? JsonPrimitive)?.takeIf { it.isString }?.content

private fun JsonObject.number(key: String): Double? =
    (this[key] as? JsonPrimitive)?.takeIf { !it.isString && it !is JsonNull }?.doubleOrNull

private fun JsonObject.count(key: String): Int? =
    (this[key] as? JsonPrimitive)?.takeIf { !it.isString && it !is JsonNull }?.intOrNull

private fun JsonObject.minus(keys: Set<String>) = JsonObject(filterKeys { it !in keys })

// PostgREST answers a timestamp as "2026-10-22T12:00:00.123456+00:00"; the Rig picker and the History screen
// read ISO instants ("...Z"). Anything unreadable is kept as it came.
internal fun asInstant(timestamp: String): String =
    runCatching { OffsetDateTime.parse(timestamp).toInstant().toString() }.getOrDefault(timestamp)

internal fun rigFromGarageRow(
    id: String,
    nickname: String,
    truck: JsonObject,
    trailer: JsonObject,
    lastUsedAt: String,
) = RecentRig(
    id = id,
    nickname = nickname.trim(),
    truck = TruckTag(
        description = truck.text("manufacturer"),
        name = truck.text("vehicle_name"),
        gvwrLb = truck.number("gvwr_lb"),
        frontGawrLb = truck.number("front_gawr_lb"),
        rearGawrLb = truck.number("rear_gawr_lb"),
        standaloneWeightLb = truck.number("standalone_weight_lb"),
        gcwrLb = truck.number("gcwr_lb"),
    ),
    trailer = TrailerTag(
        description = trailer.text("manufacturer"),
        name = trailer.text("vehicle_name"),
        gvwrLb = trailer.number("gvwr_lb"),
        gawrPerAxleLb = trailer.number("gawr_per_axle_lb"),
        axleCount = trailer.count("axle_count"),
        uvwLb = trailer.number("uvw_lb"),
    ),
    lastUsedAt = asInstant(lastUsedAt),
    truckExtra = truck.minus(TRUCK_KEYS),
    trailerExtra = trailer.minus(TRAILER_KEYS),
)

// The truck and trailer as the Garage stores them: what Android does not use, then what it does. A figure
// that is not entered is left out, so clearing one here clears it in the account.
internal fun garageTruckJson(rig: RecentRig): JsonObject = buildJsonObject {
    rig.truckExtra.forEach { (key, value) -> put(key, value) }
    val truck = rig.truck
    truck.description?.let { put("manufacturer", JsonPrimitive(it)) }
    truck.name?.let { put("vehicle_name", JsonPrimitive(it)) }
    truck.gvwrLb?.let { put("gvwr_lb", JsonPrimitive(it)) }
    truck.frontGawrLb?.let { put("front_gawr_lb", JsonPrimitive(it)) }
    truck.rearGawrLb?.let { put("rear_gawr_lb", JsonPrimitive(it)) }
    truck.standaloneWeightLb?.let { put("standalone_weight_lb", JsonPrimitive(it)) }
    truck.gcwrLb?.let { put("gcwr_lb", JsonPrimitive(it)) }
}

internal fun garageTrailerJson(rig: RecentRig): JsonObject = buildJsonObject {
    rig.trailerExtra.forEach { (key, value) -> put(key, value) }
    val trailer = rig.trailer
    trailer.description?.let { put("manufacturer", JsonPrimitive(it)) }
    trailer.name?.let { put("vehicle_name", JsonPrimitive(it)) }
    trailer.gvwrLb?.let { put("gvwr_lb", JsonPrimitive(it)) }
    trailer.gawrPerAxleLb?.let { put("gawr_per_axle_lb", JsonPrimitive(it)) }
    trailer.axleCount?.let { put("axle_count", JsonPrimitive(it)) }
    trailer.uvwLb?.let { put("uvw_lb", JsonPrimitive(it)) }
}

// What the database's `add_rig` raised, as the app understands it: 'garage_full' (with the cap in the
// error's details) is a full Garage, anything else is a failure to save.
internal fun garageFailureFor(message: String?, details: String?): Exception =
    if (message == "garage_full") GarageFullException(details?.trim()?.toIntOrNull()) else Exception(message ?: "garage_error")
