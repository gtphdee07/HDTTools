package com.rigcheck.app.data

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test

// Android reads each scan field by a hard-coded key from the Worker's `fields`
// object, and nothing else checks those keys against the tool schema the Worker
// sends to Claude. A key that is not a property of that schema (a typo, or a
// rename on one side only) is never merged and the Scan notice calls it "not
// read" on every scan. This checks the keys against the shared fixture
// test-vectors/vision_tool_schemas.json, the one the Python and Worker tests
// check their own side against.

private fun findSchemasFile(): File {
    var dir = File("").absoluteFile
    repeat(6) {
        val candidate = File(dir, "test-vectors/vision_tool_schemas.json")
        if (candidate.isFile) return candidate
        dir = dir.parentFile ?: return@repeat
    }
    error("Could not find test-vectors/vision_tool_schemas.json by walking up from ${File("").absoluteFile}")
}

private fun schemaProperties(docType: String): Set<String> {
    val root = Json.parseToJsonElement(findSchemasFile().readText()).jsonObject
    return root["doc_types"]!!.jsonObject[docType]!!.jsonObject["properties"]!!
        .jsonArray.map { it.jsonPrimitive.content }.toSet()
}

private fun keysNotIn(keys: List<String>, properties: Set<String>): List<String> =
    keys.filterNot { it in properties }

// Every key `read` looks up in the `fields` object it is handed. The object is
// empty, so only the lookups are recorded, whatever the values would have been.
private fun keysRead(read: (JsonObject) -> Unit): Set<String> {
    val seen = linkedSetOf<String>()
    val recording = object : HashMap<String, JsonElement>() {
        override fun get(key: String): JsonElement? = null.also { seen += key }
        override fun containsKey(key: String): Boolean = false.also { seen += key }
    }
    read(JsonObject(recording))
    return seen
}

// Never in a scan response (see the comment above mergeScanFields).
private val NEVER_SCANNED = listOf("standalone_weight_lb", "axle_count")

class ScanFieldKeysSchemaTest {
    private val truckKeys = TRUCK_SCAN_FIELDS.map { it.key }
    private val trailerKeys = TRAILER_SCAN_FIELDS.map { it.key }
    private val scaleKeys = SCALE_SCAN_FIELDS.map { it.key }

    @Test
    fun `every scan field key is a property of its document's tool schema`() {
        assertEquals(emptyList<String>(), keysNotIn(truckKeys, schemaProperties("truck_tag")))
        assertEquals(emptyList<String>(), keysNotIn(trailerKeys, schemaProperties("trailer_tag")))
        assertEquals(emptyList<String>(), keysNotIn(scaleKeys, schemaProperties("scale_ticket")))
    }

    @Test
    fun `a key that is not in the schema is reported`() {
        val properties = schemaProperties("truck_tag")
        assertEquals(listOf("gvwr_lbs"), keysNotIn(listOf("gvwr_lb", "gvwr_lbs"), properties))
    }

    @Test
    fun `no scan field list holds a field a scan never returns`() {
        for (keys in listOf(truckKeys, trailerKeys, scaleKeys)) {
            assertEquals(emptyList<String>(), keys.filter { it in NEVER_SCANNED })
        }
    }

    @Test
    fun `every key a merge reads is in its document's list`() {
        assertEquals(truckKeys.toSet(), keysRead { TruckTag().mergeScanFields(it) })
        assertEquals(trailerKeys.toSet(), keysRead { TrailerTag().mergeScanFields(it) })
        assertEquals(scaleKeys.toSet(), keysRead { ScaleTicket().mergeScanFields(it) })
    }
}
