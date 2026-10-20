package com.rigcheck.app.domain

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test

// The pin weight slider works in whole percentage points (15-25, default 20) and
// the breakdown math in a fraction (0.15-0.25). pinWeightFraction is the one place
// that converts, so a wrong divisor is silent wrong safety math. These tests pin
// it to test-vectors/pin_weight_pct_contract.json, the same fixture Web's
// breakdown.test.ts uses. Exact comparison on purpose: /10.0 gives 1.5 and a
// missing division gives 15.0, both far from the fixture.
class PinWeightTest {

    private fun contract() = Json.parseToJsonElement(findContractFile().readText()).jsonObject

    private fun findContractFile(): File {
        var dir = File("").absoluteFile
        repeat(6) {
            val candidate = File(dir, "test-vectors/pin_weight_pct_contract.json")
            if (candidate.isFile) return candidate
            dir = dir.parentFile ?: return@repeat
        }
        error("Could not find test-vectors/pin_weight_pct_contract.json by walking up from ${File("").absoluteFile}")
    }

    @Test
    fun `the shared fixture's UI percent converts to its fraction`() {
        val fixture = contract()
        val uiPercent = fixture["ui_percent"]!!.jsonPrimitive.intOrNull!!
        val fraction = fixture["fraction"]!!.jsonPrimitive.doubleOrNull!!

        assertEquals(fraction, pinWeightFraction(uiPercent), 0.0)
    }

    @Test
    fun `the slider default and both ends convert to 0 20, 0 15 and 0 25`() {
        assertEquals(0.20, pinWeightFraction(20), 0.0)
        assertEquals(0.15, pinWeightFraction(15), 0.0)
        assertEquals(0.25, pinWeightFraction(25), 0.0)
    }

    @Test
    fun `the default UI percent is the default fraction`() {
        assertEquals(DEFAULT_PIN_WEIGHT_PCT, pinWeightFraction(DEFAULT_PIN_WEIGHT_UI_PERCENT), 0.0)
    }
}
