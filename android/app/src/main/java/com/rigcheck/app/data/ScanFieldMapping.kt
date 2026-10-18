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

// One field a Scan can fill: its key in the Worker's `fields`, the label the
// entry screen shows for it, and how to tell whether the screen's value is
// still blank. The notice after a Scan (ui/ScanNotice.kt) names the fields the
// Scan did not read by this label.
class ScanField<T>(
    val key: String,
    val label: String,
    private val numeric: Boolean,
    val isBlankIn: (T) -> Boolean,
) {
    fun wasReadIn(fields: JsonObject): Boolean =
        if (numeric) fields.doubleField(key) != null else !fields.stringField(key).isNullOrBlank()
}

val TRUCK_SCAN_FIELDS = listOf(
    ScanField<TruckTag>("manufacturer", "Description", numeric = false) { it.description.isNullOrBlank() },
    ScanField<TruckTag>("gvwr_lb", "GVWR", numeric = true) { it.gvwrLb == null },
    ScanField<TruckTag>("front_gawr_lb", "Front GAWR", numeric = true) { it.frontGawrLb == null },
    ScanField<TruckTag>("rear_gawr_lb", "Rear GAWR", numeric = true) { it.rearGawrLb == null },
)

val TRAILER_SCAN_FIELDS = listOf(
    ScanField<TrailerTag>("manufacturer", "Description", numeric = false) { it.description.isNullOrBlank() },
    ScanField<TrailerTag>("gvwr_lb", "GVWR", numeric = true) { it.gvwrLb == null },
    ScanField<TrailerTag>("gawr_per_axle_lb", "GAWR per axle", numeric = true) { it.gawrPerAxleLb == null },
    ScanField<TrailerTag>("uvw_lb", "Unloaded weight (UVW)", numeric = true) { it.uvwLb == null },
)

val SCALE_SCAN_FIELDS = listOf(
    ScanField<ScaleTicket>("location_name", "Scale location", numeric = false) { it.locationName.isNullOrBlank() },
    ScanField<ScaleTicket>("steer_axle_lb", "Steer axle", numeric = true) { it.steerAxleLb == null },
    ScanField<ScaleTicket>("drive_axle_lb", "Drive axle", numeric = true) { it.driveAxleLb == null },
    ScanField<ScaleTicket>("trailer_axle_lb", "Trailer axle(s)", numeric = true) { it.trailerAxleLb == null },
    ScanField<ScaleTicket>("gross_weight_lb", "Gross weight", numeric = true) { it.grossWeightLb == null },
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
