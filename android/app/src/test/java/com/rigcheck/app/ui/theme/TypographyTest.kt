package com.rigcheck.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

// Before the redesign Typography.kt left headlineSmall and others on the platform font, so "RigCheck" and most
// screen titles rendered in Roboto while the design asked for Outfit. Each slot is now checked by name.
class TypographyTest {

    private fun slots(typography: Typography): Map<String, TextStyle> = mapOf(
        "displayLarge" to typography.displayLarge, "displayMedium" to typography.displayMedium,
        "displaySmall" to typography.displaySmall, "headlineLarge" to typography.headlineLarge,
        "headlineMedium" to typography.headlineMedium, "headlineSmall" to typography.headlineSmall,
        "titleLarge" to typography.titleLarge, "titleMedium" to typography.titleMedium,
        "titleSmall" to typography.titleSmall, "bodyLarge" to typography.bodyLarge,
        "bodyMedium" to typography.bodyMedium, "bodySmall" to typography.bodySmall,
        "labelLarge" to typography.labelLarge, "labelMedium" to typography.labelMedium,
        "labelSmall" to typography.labelSmall,
    )

    @Test
    fun theTestCoversEveryPublicMaterial3Slot() {
        // The 15 slots of Material 3's type scale. Its "emphasized" variants are internal to the library (no public
        // constructor argument sets them and no public property reads them), so the app cannot reach them; a public
        // slot added by a Compose upgrade fails this count and must be added above and set in Type.kt.
        val publicSlots = Typography::class.java.methods.count {
            it.name.startsWith("get") && '$' !in it.name && it.parameterCount == 0 && it.returnType == TextStyle::class.java
        }
        assertEquals(15, publicSlots)
        assertEquals(15, slots(Typography).size)
    }

    @Test
    fun noSlotUsesTheDefaultFontFamily() {
        for ((name, style) in slots(Typography)) {
            assertNotNull("$name has no font family", style.fontFamily)
            assertNotEquals("$name is on the default font family", FontFamily.Default, style.fontFamily)
        }
    }

    @Test
    fun everySlotIsOneOfTheNamedStyles() {
        val named = RigCheckStyles.byTokenName.values.toSet()
        for ((name, style) in slots(Typography)) {
            assertTrue("$name is not one of the 17 named text styles", style in named)
        }
    }

    @Test
    fun withTheFallbackFamiliesNoSlotIsOnTheDefaultFontEither() {
        val fallback = rigCheckTypography(RigCheckTextStyles(RigCheckFonts.Fallback))
        for ((name, style) in slots(fallback)) {
            assertEquals("$name is not on the design's fallback family", FontFamily.SansSerif, style.fontFamily)
        }
    }

    @Test
    fun displayStylesUseTheDisplayFamilyAndBodyStylesTheBodyFamily() {
        val styles = RigCheckStyles
        for (name in listOf("headline-verdict", "heading", "top-bar-title", "title-lg", "offer-title", "title", "title-sm", "button", "button-compact", "chip")) {
            assertEquals(name, RigCheckFonts.Bundled.display, styles.byTokenName.getValue(name).fontFamily)
        }
        for (name in listOf("body", "body-md", "body-sm", "caption", "micro", "label", "badge")) {
            assertEquals(name, RigCheckFonts.Bundled.body, styles.byTokenName.getValue(name).fontFamily)
        }
    }
}
