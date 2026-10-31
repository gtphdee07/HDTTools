package com.rigcheck.app.ui.theme

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// #197: every text/fill pair that tokens.json puts on a screen meets WCAG AA, so a token that is changed (or a new
// pair that is added) cannot take the app under it unseen. The pairs are the ones the design's `use` lines name; they
// are written out here by token name, and DesignTokensTest holds each token to the value in tokens.json. The Material 3
// roles (onPrimary on primary and the rest) are held by ContrastTest; each shared component's own colours by its
// device test (assertAa); this is the table of the design's text colours against every fill they are used on.
class TextFillPairsTest {

    // One text colour (by token name) and the fills it is drawn on. `large` is for text of 18 sp bold or 24 sp and up,
    // which needs only 3:1.
    private class Pairs(val text: String, val fills: List<String>, val large: Boolean = false)

    private val surfaces = listOf("surface", "surface-sunken", "tint-teal", "tint-purple", "tint-orange", "tint-red", "tint-green")

    private val pairs = listOf(
        // Body text and headings, and text on the orange and teal fills ("Ink text on top, never white").
        Pairs("ink", surfaces + listOf("orange", "teal")),
        // Secondary text and hints.
        Pairs("ink-muted", surfaces),
        // White on the saturated fills: the verdict bands, the destructive button, the scan credit badge, the Free badge.
        Pairs("surface", listOf("purple", "danger", "pine", "slate", "ink")),
        // The "deep" colours are the text versions of the brand colours, each on white and on its own tint.
        Pairs("orange-deep", listOf("surface", "tint-orange")),
        Pairs("teal-deep", listOf("surface", "tint-teal")),
        Pairs("purple-deep", listOf("surface", "tint-purple")),
        Pairs("danger-text", listOf("surface", "tint-red")),
        // Pass text: the badge text on its green tint, and the row text on white.
        Pairs("pine", listOf("surface", "tint-green")),
        // The disabled button is exempt from AA (WCAG 1.4.3, inactive components); the design's own pair is 4.35:1 and
        // is held to 3:1 so it stays readable.
        Pairs("disabled-content", listOf("disabled-fill"), large = true),
    )

    private fun needed(large: Boolean) = if (large) AA_LARGE_TEXT else AA_NORMAL_TEXT

    private fun failing(table: List<Pairs>): List<String> = table.flatMap { p ->
        p.fills.mapNotNull { fill ->
            val ratio = contrastRatio(DesignColors.getValue(p.text), DesignColors.getValue(fill))
            "${p.text} on $fill is ${"%.2f".format(ratio)}:1, under ${needed(p.large)}:1".takeIf { ratio < needed(p.large) }
        }
    }

    @Test
    fun everyTextColourOfTheDesignMeetsAaOnEveryFillItIsUsedOn() {
        assertEquals(emptyList<String>(), failing(pairs))
    }

    @Test
    fun theTableNamesOnlyTokensThatExistAndCoversTheTextTokens() {
        val named = pairs.flatMap { listOf(it.text) + it.fills }.toSet()
        assertTrue("tokens the table names that tokens.json lacks: ${named - DesignColors.keys}", DesignColors.keys.containsAll(named))
        // Every colour the design uses as text appears as a text side, and every tint it fills a surface with as a fill.
        val textTokens = setOf("ink", "ink-muted", "orange-deep", "teal-deep", "purple-deep", "danger-text", "pine", "disabled-content")
        assertTrue(pairs.map { it.text }.toSet().containsAll(textTokens))
        val tints = setOf("tint-teal", "tint-purple", "tint-orange", "tint-red", "tint-green", "surface-sunken")
        assertTrue(pairs.flatMap { it.fills }.toSet().containsAll(tints))
    }

    @Test
    fun theWashOnTheTealBarKeepsInkReadable() {
        // "Back button and account status row on the teal bar": ink on a 72% white wash that sits on the teal.
        assertTrue(meetsAa(Ink, OnTealWash, behind = Teal))
        assertTrue(meetsAa(Ink, Teal))
    }

    @Test
    fun aPairUnderAaIsReported() {
        // The check can fail: white on the orange fill is 2.6:1, and orange-deep on a red tint 4.3:1.
        val reported = failing(listOf(Pairs("surface", listOf("orange")), Pairs("orange-deep", listOf("tint-red"))))
        assertEquals(2, reported.size)
        assertTrue(reported[0].startsWith("surface on orange is 2.61:1"))
    }
}
