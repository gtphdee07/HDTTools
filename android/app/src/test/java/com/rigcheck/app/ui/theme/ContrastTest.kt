package com.rigcheck.app.ui.theme

import androidx.compose.ui.graphics.Color
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ContrastTest {

    @Test
    fun blackOnWhiteIs21To1() {
        assertEquals(21.0, contrastRatio(Color.Black, Color.White), 0.01)
    }

    @Test
    fun theRatioIsTheSameEitherWayRound() {
        assertEquals(contrastRatio(Ink, Orange), contrastRatio(Orange, Ink), 1e-9)
    }

    @Test
    fun theDesignsStatedRatiosHold() {
        // tokens.json: "danger #b5473a is 4.4:1 on tint-red; danger-text is 5.8:1".
        assertEquals(4.4, contrastRatio(DangerRed, TintRed), 0.1)
        assertEquals(5.8, contrastRatio(DangerText, TintRed), 0.1)
        // "border-strong ... (3:1 on white)".
        assertTrue(contrastRatio(BorderStrong, Surface) >= 3.0)
    }

    @Test
    fun aTranslucentForegroundIsLaidOverTheFillFirst() {
        // The 72% white wash over teal is lighter than teal, so ink on it is clearer than ink on teal.
        assertTrue(contrastRatio(Ink, OnTealWash, behind = Teal) > contrastRatio(Ink, Teal))
    }

    @Test
    fun largeTextNeedsOnlyThreeToOne() {
        // White on orange is under 3:1, so it fails even as large text (the design puts ink on orange).
        assertFalse(meetsAa(Surface, Orange))
        assertFalse(meetsAa(Surface, Orange, largeText = true))
        // A mid-grey at about 3.5:1 on white passes only as large text.
        val grey = Color(0xFF8A8A8A)
        assertFalse(meetsAa(grey, Surface))
        assertTrue(meetsAa(grey, Surface, largeText = true))
    }

    @Test
    fun everyMaterial3TextRoleMeetsAaOnItsOwnFill() {
        val scheme = RigCheckLightColorScheme
        val pairs = mapOf(
            "onPrimary/primary" to (scheme.onPrimary to scheme.primary),
            "onSecondary/secondary" to (scheme.onSecondary to scheme.secondary),
            "onTertiary/tertiary" to (scheme.onTertiary to scheme.tertiary),
            "onError/error" to (scheme.onError to scheme.error),
            "onBackground/background" to (scheme.onBackground to scheme.background),
            "onSurface/surface" to (scheme.onSurface to scheme.surface),
            "onSurfaceVariant/surfaceVariant" to (scheme.onSurfaceVariant to scheme.surfaceVariant),
            "onPrimaryContainer/primaryContainer" to (scheme.onPrimaryContainer to scheme.primaryContainer),
            "onSecondaryContainer/secondaryContainer" to (scheme.onSecondaryContainer to scheme.secondaryContainer),
            "onTertiaryContainer/tertiaryContainer" to (scheme.onTertiaryContainer to scheme.tertiaryContainer),
            "onErrorContainer/errorContainer" to (scheme.onErrorContainer to scheme.errorContainer),
            "inverseOnSurface/inverseSurface" to (scheme.inverseOnSurface to scheme.inverseSurface),
        )
        for ((name, pair) in pairs) {
            val ratio = contrastRatio(pair.first, pair.second)
            assertTrue("$name is $ratio:1, below AA 4.5:1", ratio >= AA_NORMAL_TEXT)
        }
    }
}
