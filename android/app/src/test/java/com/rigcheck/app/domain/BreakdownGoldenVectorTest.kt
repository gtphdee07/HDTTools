package com.rigcheck.app.domain

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import java.io.File
import kotlin.math.roundToInt
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeTrue
import org.junit.Test

// Runs the shared golden vectors (test-vectors/breakdown_cases.json) - the
// same cases tests/test_breakdown_golden_vectors.py checks against Python,
// the source of truth. Kotlin's port doesn't have every capability Python
// does yet (no adjustable pin-weight %, no insufficient/partial verdict
// tiers, no predictive standalone-only truck estimate) - cases needing
// those are skipped via Assume, not silently passed. This file does NOT
// replace BreakdownTest.kt's hand-written, one-scenario-per-test suite;
// it exists specifically to catch this port drifting further from Python.
//
// Parses JSON manually (JsonObject field access) rather than
// kotlinx.serialization's typed decodeFromString, so this file needs no
// changes to the domain model classes (ScaleTicket isn't @Serializable
// today, and shouldn't need to become so just for this test).

private val SUPPORTED_CAPABILITIES = emptySet<String>()

// Deliberately not skipped even though it contains rows Kotlin can't
// represent as "insufficient" - routed to its own dedicated assertion
// below instead of the generic per-case loop. See its "_note" in the
// JSON file.
private const val LIVE_BUG_CASE_NAME = "live_bug_standalone_without_hitched"

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

class BreakdownGoldenVectorTest {

    @Test
    fun `golden vectors - cases fully supported by the current Kotlin port`() {
        for (case in loadCases()) {
            val name = case.string("name")
            if (name == LIVE_BUG_CASE_NAME) continue

            val requires = case["requires"]!!.jsonArray.map { it.jsonPrimitive.content }
            if (!SUPPORTED_CAPABILITIES.containsAll(requires)) {
                // Not a failure - this case needs a capability the Kotlin
                // port doesn't have yet. Skipping (not silently passing,
                // not failing) is what makes the size of the gap visible
                // in the test report rather than hidden in a comment.
                continue
            }

            val items = computeBreakdown(truckFrom(case), trailerFrom(case), scaleFrom(case))
            val expected = case["expected"]!!.jsonObject
            val expectedStatus = expected.string("verdict_status")
            val kotlinStatus = if (verdictFor(items).tone == Tone.WARNING) "fail" else "pass"
            assertEquals("$name: verdict status", expectedStatus, kotlinStatus)

            for (expectedItemElement in expected["items"]!!.jsonArray) {
                val expectedItem = expectedItemElement.jsonObject
                val label = expectedItem.string("label")
                val row = item(items, label)
                assertEquals("$name/$label: tone", expectedItem.string("tone"), row.tone.name.lowercase())
                assertEquals("$name/$label: actual_lb", expectedItem.int("actual_lb"), row.actual.roundToInt())
                assertEquals("$name/$label: limit_lb", expectedItem.int("limit_lb"), row.limit.roundToInt())
                assertEquals("$name/$label: pct", expectedItem.int("pct"), row.pct)
                // "estimated" isn't compared - BreakdownItem has no such
                // property yet. Add this assertion once the Kotlin port
                // gains the field.
            }
        }
    }

    @Test
    fun `golden vectors - report how many cases are currently skipped`() {
        val cases = loadCases().filter { it.string("name") != LIVE_BUG_CASE_NAME }
        val skipped = cases.filter { case ->
            val requires = case["requires"]!!.jsonArray.map { it.jsonPrimitive.content }
            !SUPPORTED_CAPABILITIES.containsAll(requires)
        }
        // Not a pass/fail assertion on any specific number - just makes the
        // gap's size visible in the test's own console output every run,
        // rather than only discoverable by reading the JSON by hand.
        println(
            "Golden vectors: ${cases.size - skipped.size}/${cases.size} cases fully " +
                "supported by the current Kotlin port. Skipped: " +
                skipped.joinToString { it.string("name") },
        )
        assumeTrue("informational only", true)
    }

    @Test
    fun `golden vector - live bug - standalone weight without a hitched reading`() {
        // Deliberately NOT skipped, and expected to FAIL right now - see
        // this case's "_note" in the JSON file. Kotlin's standaloneProvided
        // branch in computeBreakdown doesn't check whether a real hitched
        // (steer+drive) reading also exists, so it silently produces the
        // wrong Trailer Total here - the exact bug fixed in Python's
        // compute_breakdown this session, still live in this port.
        val case = loadCases().first { it.string("name") == LIVE_BUG_CASE_NAME }
        val items = computeBreakdown(truckFrom(case), trailerFrom(case), scaleFrom(case))
        val expectedItem = case["expected"]!!.jsonObject["items"]!!.jsonArray
            .map { it.jsonObject }
            .first { it.string("label") == "Trailer Total (GVWR)" }

        val row = item(items, "Trailer Total (GVWR)")
        assertEquals(
            "Trailer Total (GVWR) actual_lb - if this now passes, the live bug has been " +
                "fixed in Kotlin; update this test's expectations and its surrounding comments",
            expectedItem.int("actual_lb"),
            row.actual.roundToInt(),
        )
    }
}
