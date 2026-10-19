package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanAttempts
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.navigation.EntryModule
import java.io.File
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Android against the shared Scan outcomes (test-vectors/scan_outcomes.json,
// written up as "Scan outcomes" in workers/scan-proxy/CONTEXT.md). Every row is
// produced the way the app produces it: the real error wording and next steps
// (scanErrorFor), the real request-id bookkeeping (ScanAttempts) and the real
// notice (applyScan). A row that disagrees with what the app does fails here,
// and so does a client change the row does not allow. Web runs the same file
// (web/src/scanOutcomes.test.ts). What the Worker charges and refunds is the
// Worker's own tests; this is what the user is told and how a retry behaves.
//
// A row field marked pending for Android in the fixture is not checked and is
// printed, so what is still to build is visible; the ticket that builds it
// removes the entry from the fixture and the field is checked from then on.
class ScanOutcomesFixtureTest {
    private val fixture = Json.parseToJsonElement(findFixture().readText()).jsonObject
    private val rows = fixture["cases"]!!.jsonArray.map { it.jsonObject }
        .filter { row -> row.strings("appliesTo").contains("android") }

    private fun findFixture(): File {
        var dir: File? = File("").absoluteFile
        repeat(8) {
            val candidate = File(dir, "test-vectors/scan_outcomes.json")
            if (candidate.isFile) return candidate
            dir = dir?.parentFile
        }
        error("Could not find test-vectors/scan_outcomes.json by walking up from ${File("").absoluteFile}")
    }

    private fun JsonObject.string(key: String) = this[key]!!.jsonPrimitive.content

    private fun JsonObject.strings(key: String) = this[key]!!.jsonArray.map { it.jsonPrimitive.content }

    private val JsonObject.id get() = string("id")

    private fun JsonObject.isPending(field: String): Boolean =
        this["pending"]!!.jsonObject["android"]?.jsonObject?.containsKey(field) == true

    private fun trigger(row: JsonObject) = row["trigger"]!!.jsonObject

    // What the Scan client answers for a row, the way the app's client reports it.
    private fun resultFor(row: JsonObject): ScanResult {
        val t = trigger(row)
        return when (val kind = t.string("kind")) {
            "worker_error" -> ScanResult.Failure(t.string("code"), "the Worker, for developers")
            "no_connection" -> ScanResult.Failure("network_error", "Unable to resolve host")
            "unreadable_reply" -> ScanResult.Failure("parse_error", "Could not parse the server's response.")
            "no_answer_in_time" -> ScanResult.Failure("timeout", "timeout")
            "unsendable_photo" -> PHOTO_UNSENDABLE
            "delivered", "delivered_no_weight" -> ScanResult.Success(JsonObject(emptyMap()))
            else -> error("${row.id}: this test has no way to produce a '$kind' trigger")
        }
    }

    private fun fieldsFor(fieldsRead: String): JsonObject = Json.parseToJsonElement(
        when (fieldsRead) {
            "none" -> "{}"
            "some" -> """{"manufacturer":"Ford","gvwr_lb":10000}"""
            "all" -> """{"manufacturer":"Ford","gvwr_lb":10000,"front_gawr_lb":5000,"rear_gawr_lb":6000}"""
            else -> error("unknown fieldsRead '$fieldsRead'")
        },
    ).jsonObject

    // The error screen's state for a row that did not deliver, or null for a delivered one.
    private fun errorFor(row: JsonObject): ScanUiState.Error? = when (trigger(row).string("kind")) {
        "delivered" -> null
        "delivered_no_weight" -> NO_WEIGHT_ERROR
        else -> scanErrorFor(resultFor(row) as ScanResult.Failure)
    }

    // The words the user reads for a row: the error message, or the notice on the entry screen.
    private fun wordsFor(row: JsonObject): String? {
        val t = trigger(row)
        if (t.string("kind") != "delivered") return errorFor(row)!!.message
        val applied = applyScan(
            EntryModule.TRUCK, fieldsFor(t.string("fieldsRead")), TruckTag(), TrailerTag(), ScaleTicket(),
        )
        return applied.notice?.textFor(applied.truck)
    }

    private fun checkedRows(field: String, check: (JsonObject, MutableList<String>) -> Unit) {
        val problems = mutableListOf<String>()
        rows.filterNot { it.isPending(field) }.forEach { check(it, problems) }
        assertTrue("Android disagrees with the fixture on $field:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    @Test
    fun `the message the user reads contains the phrases the fixture requires`() = checkedRows("messageContains") { row, problems ->
        val phrases = row.strings("messageContains")
        val words = wordsFor(row)
        if (phrases.isEmpty()) {
            if (words != null) problems += "${row.id}: expected no message, got \"$words\""
            return@checkedRows
        }
        if (words == null) {
            problems += "${row.id}: expected a message, got none"
            return@checkedRows
        }
        phrases.filterNot { words.lowercase().contains(it.lowercase()) }
            .forEach { problems += "${row.id}: \"$words\" does not contain \"$it\"" }
    }

    @Test
    fun `a retry of the same photo keeps or changes the request id as the fixture says`() = runTest {
        val problems = mutableListOf<String>()
        rows.filterNot { it.isPending("retryKeepsRequestId") }.forEach { row ->
            val attempts = ScanAttempts()
            val sent = mutableListOf<String>()
            repeat(2) {
                attempts.run(EntryModule.TRUCK, "content://photo/1") { id ->
                    sent += id
                    resultFor(row)
                }
            }
            val kept = sent[0] == sent[1]
            if (kept != row["retryKeepsRequestId"]!!.jsonPrimitive.boolean) {
                problems += "${row.id}: the fixture says the retry ${if (kept) "changes" else "keeps"} the id, the app ${if (kept) "keeps" else "changes"} it"
            }
        }
        assertTrue("Android disagrees with the fixture on retryKeepsRequestId:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    @Test
    fun `Try again is offered only where the fixture says`() = checkedRows("offersTryAgain") { row, problems ->
        // A delivered Scan with fields left blank shows a notice, which is text only and has no buttons.
        val error = errorFor(row) ?: return@checkedRows
        val offered = ScanNextStep.TRY_AGAIN in error.nextSteps
        if (offered != row["offersTryAgain"]!!.jsonPrimitive.boolean) {
            problems += "${row.id}: the fixture says Try again is ${if (offered) "not " else ""}offered, the app ${if (offered) "offers" else "does not offer"} it"
        }
    }

    @Test
    fun `the steps the user is offered are exactly the fixture's next steps`() = checkedRows("nextStep") { row, problems ->
        val error = errorFor(row) ?: return@checkedRows
        val steps = error.nextSteps.map { it.name.lowercase() }.toSet()
        val expected = row.strings("nextStep").toSet()
        if (steps != expected) problems += "${row.id}: the fixture says $expected, the app offers $steps"
    }

    @Test
    fun `the unread fields are named the way the fixture says`() {
        val lists = fixture["noticeFieldLists"]!!.jsonArray
        assertTrue(lists.isNotEmpty())
        lists.map { it.jsonObject }.forEach { list ->
            assertEquals(list.string("message"), ScanMessages.someNotRead(list.strings("labels")))
        }
    }

    @Test
    fun `the fixture has one row for each case and lists what is pending for Android`() {
        val all: JsonArray = fixture["cases"]!!.jsonArray
        assertEquals(16, all.size)
        assertEquals("ids are unique", all.size, all.map { it.jsonObject.id }.toSet().size)
        val pending = rows.flatMap { row ->
            (row["pending"]!!.jsonObject["android"]?.jsonObject ?: JsonObject(emptyMap())).map { (field, ticket) ->
                "${row.id}.$field -> ${ticket.jsonPrimitive.content}"
            }
        }
        pending.forEach { assertTrue("a pending entry names its ticket: $it", Regex("-> #\\d+").containsMatchIn(it)) }
        println("Scan outcomes pending for Android (${pending.size}):" + pending.joinToString("") { "\n  $it" })
    }
}
