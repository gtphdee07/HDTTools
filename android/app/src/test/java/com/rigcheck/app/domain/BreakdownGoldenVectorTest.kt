package com.rigcheck.app.domain

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.format.badgeLabel
import java.io.File
import kotlin.math.roundToInt
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Runs the shared golden vectors (test-vectors/breakdown_cases.json) - the
// same cases tests/test_breakdown_golden_vectors.py checks against Python,
// the source of truth. Every case runs for real; a case whose "requires"
// names a capability this runner doesn't know FAILS (never skips), so a new
// capability in the fixture can't be silently ignored by this port. This
// file does NOT replace BreakdownTest.kt's hand-written, one-scenario-per-
// test suite; it exists specifically to catch this port drifting from Python.
//
// Parses JSON manually (JsonObject field access) rather than
// kotlinx.serialization's typed decodeFromString, so this file needs no
// changes to the domain model classes (ScaleTicket isn't @Serializable
// today, and shouldn't need to become so just for this test).

// Add a tag here only once the Kotlin port actually has that capability.
private val SUPPORTED_CAPABILITIES = setOf(
    "insufficient_tone",
    "gvwr_fallback_trailer_estimate",
    "adjustable_pin_weight_pct",
    "predictive_truck_estimate",
)

private fun unsupportedCapabilities(requires: List<String>): List<String> =
    requires.filterNot { it in SUPPORTED_CAPABILITIES }

private fun findVectorsFile(): File {
    var dir = File("").absoluteFile
    repeat(6) {
        val candidate = File(dir, "test-vectors/breakdown_cases.json")
        if (candidate.isFile) return candidate
        dir = dir.parentFile ?: return@repeat
    }
    error("Could not find test-vectors/breakdown_cases.json by walking up from ${File("").absoluteFile}")
}

private fun loadCases(): List<JsonObject> {
    val root = Json.parseToJsonElement(findVectorsFile().readText()).jsonObject
    return root["cases"]!!.jsonArray.map { it.jsonObject }
}

private fun JsonObject.double(key: String): Double? = this[key]?.jsonPrimitive?.doubleOrNull
private fun JsonObject.int(key: String): Int? = this[key]?.jsonPrimitive?.intOrNull
private fun JsonObject.string(key: String): String = this[key]!!.jsonPrimitive.content

private fun truckFrom(case: JsonObject): TruckTag {
    val t = case["truck"]!!.jsonObject
    return TruckTag(
        gvwrLb = t.double("gvwr_lb"),
        frontGawrLb = t.double("front_gawr_lb"),
        rearGawrLb = t.double("rear_gawr_lb"),
        standaloneWeightLb = t.double("standalone_weight_lb"),
    )
}

private fun trailerFrom(case: JsonObject): TrailerTag {
    val t = case["trailer"]!!.jsonObject
    return TrailerTag(
        gvwrLb = t.double("gvwr_lb"),
        gawrPerAxleLb = t.double("gawr_per_axle_lb"),
        axleCount = t.int("axle_count"),
    )
}

private fun scaleFrom(case: JsonObject): ScaleTicket {
    val s = case["scale"]!!.jsonObject
    return ScaleTicket(
        steerAxleLb = s.double("steer_axle_lb"),
        driveAxleLb = s.double("drive_axle_lb"),
        trailerAxleLb = s.double("trailer_axle_lb"),
        grossWeightLb = s.double("gross_weight_lb"),
    )
}

private fun item(items: List<BreakdownItem>, label: String): BreakdownItem =
    items.first { it.label == label }

// Rows Android words differently on purpose (see Breakdown.kt); only these may carry "note_android".
private val ANDROID_NOTE_ROWS = setOf("Tow Vehicle Total (GVWR)", "Combined Rig Weight")

private fun checkCase(case: JsonObject) {
        val name = case.string("name")
        val requires = case["requires"]!!.jsonArray.map { it.jsonPrimitive.content }
        assertEquals("$name: unknown capability", emptyList<String>(), unsupportedCapabilities(requires))

        val pinWeightPct = case.double("pin_weight_pct") ?: DEFAULT_PIN_WEIGHT_PCT
        val items = computeBreakdown(truckFrom(case), trailerFrom(case), scaleFrom(case), pinWeightPct)
        val expected = case["expected"]!!.jsonObject
        val verdict = verdictFor(items)
        assertEquals("$name: verdict status", expected.string("verdict_status"), verdict.status.name.lowercase())
        assertEquals("$name: headline", expected.string("headline"), verdict.headline)
        assertEquals("$name: subline", expected.string("subline"), verdict.subline)

        for (expectedItemElement in expected["items"]!!.jsonArray) {
            val expectedItem = expectedItemElement.jsonObject
            val label = expectedItem.string("label")
            val row = item(items, label)
            assertEquals("$name/$label: tone", expectedItem.string("tone"), row.tone.name.lowercase())
            assertEquals("$name/$label: actual_lb", expectedItem.int("actual_lb"), row.actual.roundToInt())
            assertEquals("$name/$label: limit_lb", expectedItem.int("limit_lb"), row.limit.roundToInt())
            assertEquals("$name/$label: pct", expectedItem.int("pct"), row.pct)
            assertEquals("$name/$label: estimated", expectedItem["estimated"]!!.jsonPrimitive.boolean, row.estimated)
            // Android has no "Not enough info" badge text (the UI renders insufficient rows
            // without a badge), so the badge is compared for checked rows only.
            if (row.tone != Tone.INSUFFICIENT) {
                assertEquals("$name/$label: badge", expectedItem.string("badge"), badgeLabel(row))
            }
            // "note_android" overrides "note" where Android deliberately words a row differently
            // (see towVehicleTotalNote/combinedRigWeightNote in Breakdown.kt); null means no note.
            val noteKey = if ("note_android" in expectedItem) "note_android" else "note"
            assertEquals("$name/$label: note", expectedItem[noteKey]!!.jsonPrimitive.contentOrNull, row.note)
        }
}

class BreakdownGoldenVectorTest {

    @Test
    fun `golden vectors - every case matches the fixture`() {
        loadCases().forEach(::checkCase)
    }

    @Test
    fun `golden vectors - a fixture case with an unknown capability fails the run`() {
        val bad = JsonObject(loadCases().first() + ("requires" to JsonArray(listOf(JsonPrimitive("no_such_capability")))))
        val failure = runCatching { checkCase(bad) }.exceptionOrNull()
        assertTrue("expected an AssertionError", failure is AssertionError)
        assertTrue(failure!!.message!!.contains("unknown capability"))
    }

    @Test
    fun `golden vectors - note_android only appears on the rows Android words differently`() {
        val stray = loadCases().flatMap { case ->
            case["expected"]!!.jsonObject["items"]!!.jsonArray.map { it.jsonObject }
                .filter { "note_android" in it && it.string("label") !in ANDROID_NOTE_ROWS }
                .map { "${case.string("name")}/${it.string("label")}" }
        }
        assertEquals(emptyList<String>(), stray)
    }

    @Test
    fun `golden vectors - every breakdown row has an over-limit case`() {
        val overLimitRows = loadCases().flatMap { case ->
            case["expected"]!!.jsonObject["items"]!!.jsonArray
                .map { it.jsonObject }
                .filter { it.string("tone") == "warning" }
                .map { it.string("label") }
        }.toSet()
        val allRows = computeBreakdown(TruckTag(), TrailerTag(), ScaleTicket(), DEFAULT_PIN_WEIGHT_PCT).map { it.label }
        assertEquals(emptyList<String>(), allRows.filterNot { it in overLimitRows })
    }

    @Test
    fun `golden vectors - an unknown capability is reported, not skipped`() {
        assertEquals(listOf("no_such_capability"), unsupportedCapabilities(listOf("no_such_capability")))
        assertEquals(emptyList<String>(), unsupportedCapabilities(listOf("insufficient_tone")))
    }
}
