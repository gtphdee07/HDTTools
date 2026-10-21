package com.rigcheck.app.data

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test

// The scan fields Android fills (TRUCK_/TRAILER_/SCALE_SCAN_FIELDS), by key and
// type, against the shared fixture test-vectors/scan_form_fields.json that
// Streamlit and Web check their own forms against. The fixture's `scanned`
// fields are the ones a Scan can fill; its `manual_only` fields (stand-alone
// weight, axle count) live on the entry screens and a Scan never returns them,
// so none may be in a list. ScanFieldKeysSchemaTest checks the same keys against
// the tool schema; this one fails on its own when the forms drift apart.

private fun findFixtureFile(): File {
    var dir = File("").absoluteFile
    repeat(6) {
        val candidate = File(dir, "test-vectors/scan_form_fields.json")
        if (candidate.isFile) return candidate
        dir = dir.parentFile ?: return@repeat
    }
    error("Could not find test-vectors/scan_form_fields.json by walking up from ${File("").absoluteFile}")
}

private fun fixtureFields(docType: String, section: String): Set<Pair<String, String>> {
    val root = Json.parseToJsonElement(findFixtureFile().readText()).jsonObject
    return root[docType]!!.jsonObject[section]!!.jsonArray.map {
        val field = it.jsonObject
        field["name"]!!.jsonPrimitive.content to field["type"]!!.jsonPrimitive.content
    }.toSet()
}

// `numeric` is private, so the type is read the way a Scan sees it: a number
// field does not read a non-numeric string, a text field reads any string.
private fun typeOf(field: ScanField<*>): String {
    val notANumber = JsonObject(mapOf(field.key to JsonPrimitive("not a number")))
    return if (field.wasReadIn(notANumber)) "text" else "number"
}

private fun listFields(list: List<ScanField<*>>): Set<Pair<String, String>> =
    list.map { it.key to typeOf(it) }.toSet()

// What differs between the list's (name, type) pairs and the fixture's, one line
// per difference; empty when they agree.
private fun differences(list: Set<Pair<String, String>>, fixture: Set<Pair<String, String>>): List<String> =
    (list - fixture).map { "in the list, not the fixture: $it" } +
        (fixture - list).map { "in the fixture, not the list: $it" }

private val DOC_LISTS: Map<String, List<ScanField<*>>> = mapOf(
    "truck_tag" to TRUCK_SCAN_FIELDS,
    "trailer_tag" to TRAILER_SCAN_FIELDS,
    "scale_ticket" to SCALE_SCAN_FIELDS,
)

class ScanFormFieldsFixtureTest {
    @Test
    fun `each scan field list is the fixture's scanned fields, by name and type`() {
        for ((docType, list) in DOC_LISTS) {
            assertEquals(docType, emptyList<String>(), differences(listFields(list), fixtureFields(docType, "scanned")))
        }
    }

    @Test
    fun `no scan field list holds a manual-only field`() {
        for ((docType, list) in DOC_LISTS) {
            val manualOnly = fixtureFields(docType, "manual_only").map { it.first }.toSet()
            assertEquals(docType, emptyList<String>(), list.map { it.key }.filter { it in manualOnly })
        }
    }

    @Test
    fun `a missing field, an extra field and a changed type are each reported`() {
        val fixture = setOf("manufacturer" to "text", "gvwr_lb" to "number")
        assertEquals(
            listOf("in the fixture, not the list: (gvwr_lb, number)"),
            differences(setOf("manufacturer" to "text"), fixture),
        )
        assertEquals(
            listOf("in the list, not the fixture: (uvw_lb, number)"),
            differences(fixture + ("uvw_lb" to "number"), fixture),
        )
        assertEquals(
            listOf(
                "in the list, not the fixture: (gvwr_lb, text)",
                "in the fixture, not the list: (gvwr_lb, number)",
            ),
            differences(setOf("manufacturer" to "text", "gvwr_lb" to "text"), fixture),
        )
    }

    @Test
    fun `a field's type is read as number when numeric and text when not`() {
        assertEquals("number", typeOf(ScanField<Unit>("w", "W", numeric = true) { true }))
        assertEquals("text", typeOf(ScanField<Unit>("t", "T", numeric = false) { true }))
    }
}
