package com.rigcheck.app.data

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonPrimitive

private fun JsonObject.stringField(key: String): String? =
    this[key]?.takeIf { it !is JsonNull }?.jsonPrimitive?.contentOrNull

private fun JsonObject.doubleField(key: String): Double? =
    this[key]?.takeIf { it !is JsonNull }?.jsonPrimitive?.doubleOrNull

// Merges scanned fields onto existing state - only overwrites a field when
// the scan actually extracted a value, so a re-scan never blanks out
// something the user already typed. standalone_weight_lb/axle_count never
// appear in a scan response (docTypes.ts confirms this deliberately - see
// ANDROID_DESIGN_BRIEF.md), so they're always left untouched here, and
// "name" is a manual-only field with no scan equivalent either.
fun TruckTag.mergeScanFields(fields: JsonObject): TruckTag = copy(
    description = fields.stringField("manufacturer") ?: description,
    gvwrLb = fields.doubleField("gvwr_lb") ?: gvwrLb,
    frontGawrLb = fields.doubleField("front_gawr_lb") ?: frontGawrLb,
    rearGawrLb = fields.doubleField("rear_gawr_lb") ?: rearGawrLb,
)

fun TrailerTag.mergeScanFields(fields: JsonObject): TrailerTag = copy(
    description = fields.stringField("manufacturer") ?: description,
    gvwrLb = fields.doubleField("gvwr_lb") ?: gvwrLb,
    gawrPerAxleLb = fields.doubleField("gawr_per_axle_lb") ?: gawrPerAxleLb,
    uvwLb = fields.doubleField("uvw_lb") ?: uvwLb,
)

fun ScaleTicket.mergeScanFields(fields: JsonObject): ScaleTicket = copy(
    locationName = fields.stringField("location_name") ?: locationName,
    steerAxleLb = fields.doubleField("steer_axle_lb") ?: steerAxleLb,
    driveAxleLb = fields.doubleField("drive_axle_lb") ?: driveAxleLb,
    trailerAxleLb = fields.doubleField("trailer_axle_lb") ?: trailerAxleLb,
    grossWeightLb = fields.doubleField("gross_weight_lb") ?: grossWeightLb,
)

// A tow-vehicle-only CAT Scale ticket is the same scale_ticket doc type,
// just without a trailer-axle line - so it's scanned via the same
// EntryModule.SCALE endpoint and this only picks a different field back
// out of the response, matching Web's scanStandaloneTicket in App.tsx.
// Prefers steer+drive (a genuine 2-axle-group weighing); falls back to
// gross_weight_lb for tickets that only report one combined figure.
fun standaloneWeightFrom(fields: JsonObject): Double? {
    val steer = fields.doubleField("steer_axle_lb")
    val drive = fields.doubleField("drive_axle_lb")
    return if (steer != null && drive != null) steer + drive else fields.doubleField("gross_weight_lb")
}
