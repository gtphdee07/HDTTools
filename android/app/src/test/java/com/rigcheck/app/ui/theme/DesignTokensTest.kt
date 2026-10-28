package com.rigcheck.app.ui.theme

import androidx.compose.foundation.shape.CornerBasedShape
import androidx.compose.material3.ColorScheme
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import java.io.File
import kotlin.math.roundToInt
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// The theme against the designer's tokens.json (docs/android-redesign/design-return/): every colour, text style
// size and line height, radius, elevation, size and opacity in the code must equal the file. A change on either
// side fails here, so the theme cannot drift from the design (or the design file from the theme) unseen.
class DesignTokensTest {

    private val tokens: JsonObject = Json.parseToJsonElement(findTokens().readText()).jsonObject

    @Test
    fun everyColourEqualsTheDesignFile() {
        val named = tokenColours()
        // Only this one is deliberately not an app colour (tokens.json says "Design frames only").
        val designFramesOnly = setOf("keyboard-placeholder")
        assertEquals(
            "colours in tokens.json that the theme lacks, or the other way round",
            named.keys - designFramesOnly,
            DesignColors.keys,
        )
        for ((name, expected) in named) {
            if (name in designFramesOnly) continue
            assertColourEquals(name, expected, DesignColors.getValue(name))
        }
    }

    @Test
    fun theSkyGradientEqualsTheDesignFile() {
        val sky = tokens.getValue("gradients").jsonArray.map { it.jsonObject }.single { it.string("name") == "sky" }
        assertColourEquals("sky from", parseColour(sky.string("from")), SkyGradientTop)
        assertColourEquals("sky to", parseColour(sky.string("to")), SkyGradientBottom)
    }

    @Test
    fun everyTextStyleEqualsTheDesignFileWithTheBundledFonts() {
        assertTextStyles(RigCheckTextStyles(RigCheckFonts.Bundled), RigCheckFonts.Bundled)
    }

    @Test
    fun everyTextStyleStillEqualsTheDesignFileWhenTheFontsFallBack() {
        // The design lists the fallback for both families: "system sans-serif".
        val families = tokens.getValue("typography").jsonObject.getValue("families").jsonObject
        for (family in families.values) {
            assertTrue(family.jsonObject.string("fallback").contains("sans-serif"))
        }
        assertTextStyles(RigCheckTextStyles(RigCheckFonts.Fallback), RigCheckFonts.Fallback)
    }

    @Test
    fun theBundledFamiliesAreTheOnesTheDesignNames() {
        val families = tokens.getValue("typography").jsonObject.getValue("families").jsonObject
        assertEquals(setOf("Outfit", "DM Sans"), families.values.map { it.jsonObject.string("name") }.toSet())
        val weights = families.values.associate { it.jsonObject.string("name") to it.jsonObject.getValue("weights").jsonArray.map { w -> w.jsonPrimitive.int } }
        // Every weight a text style asks for is one of the family's listed weights.
        for (style in styleTokens()) {
            assertTrue(
                "${style.string("name")} asks for weight ${style.int("weight")} of ${style.string("family")}",
                style.int("weight") in weights.getValue(style.string("family")),
            )
        }
    }

    @Test
    fun theSpacingScaleAndScreenMarginEqualTheDesignFile() {
        assertEquals(tokens.getValue("spacing_dp").jsonArray.map { it.jsonPrimitive.int }, Spacing.values.map { it.value.toInt() })
        assertEquals(tokens.getValue("screen_margin_dp").jsonPrimitive.int.toFloat(), Spacing.ScreenMargin.value)
    }

    @Test
    fun theRadiiEqualTheDesignFile() {
        val expected = mapOf(
            "input" to Radii.Input, "card" to Radii.Card, "panel" to Radii.Panel, "band" to Radii.Band,
            "sheet_top" to Radii.SheetTop, "dialog" to Radii.Dialog, "pill" to Radii.Pill,
        )
        assertDpMap(tokens.getValue("radii_dp").jsonObject, expected)
    }

    @Test
    fun theElevationsEqualTheDesignFile() {
        val expected = mapOf("sm" to Elevations.Sm, "md" to Elevations.Md, "footer" to Elevations.Footer)
        val elevations = tokens.getValue("elevation").jsonArray.map { it.jsonObject }
        assertEquals(expected.keys, elevations.map { it.string("name") }.toSet())
        for (e in elevations) {
            assertEquals(e.string("name"), e.int("compose_dp").toFloat(), expected.getValue(e.string("name")).value)
        }
    }

    @Test
    fun theSizesEqualTheDesignFile() {
        val expected = mapOf(
            "touch_target_min" to Sizes.TouchTargetMin, "button" to Sizes.Button, "button_compact" to Sizes.ButtonCompact,
            "button_in_dialog" to Sizes.ButtonInDialog, "text_field" to Sizes.TextField, "credit_chip" to Sizes.CreditChip,
            "credit_chip_icon" to Sizes.CreditChipIcon, "top_bar_logo" to Sizes.TopBarLogo, "icon_button" to Sizes.IconButton,
            "row_status_icon" to Sizes.RowStatusIcon, "progress_bar" to Sizes.ProgressBar, "slider_thumb" to Sizes.SliderThumb,
            "status_bar_allowance" to Sizes.StatusBarAllowance, "nav_bar_allowance" to Sizes.NavBarAllowance,
        )
        assertDpMap(tokens.getValue("sizes_dp").jsonObject, expected)
    }

    @Test
    fun theOpacitiesAndMotionEqualTheDesignFile() {
        val opacity = tokens.getValue("opacity").jsonObject
        val expected = mapOf(
            "scrim" to Opacity.Scrim, "scan_overlay_wash" to Opacity.ScanOverlayWash, "on_teal_wash" to Opacity.OnTealWash,
            "step_connector" to Opacity.StepConnector, "disabled_field" to Opacity.DisabledField,
        )
        assertEquals(expected.keys, opacity.keys)
        for ((key, value) in expected) assertEquals(key, opacity.getValue(key).jsonPrimitive.double, value.toDouble(), 1e-6)
        // The wash colour carries the same alpha as the opacity token it is named for.
        assertEquals(Opacity.OnTealWash, OnTealWash.alpha, 0.005f)

        val durations = tokens.getValue("motion").jsonObject.getValue("durations_ms").jsonObject
        assertEquals(
            mapOf("short" to Motion.ShortMs, "medium" to Motion.MediumMs, "long" to Motion.LongMs),
            durations.mapValues { it.value.jsonPrimitive.int },
        )
    }

    @Test
    fun theColourSchemeEqualsTheMaterial3MappingInTheDesignFile() {
        val mapping = tokens.getValue("material3_mapping").jsonObject
        val roles = mapping.filterKeys { it != "custom_colors_outside_m3" && it != "shapes" && it != "notes" }
        assertTrue(roles.isNotEmpty())
        for ((role, token) in roles) {
            val tokenName = token.jsonPrimitive.content
            assertColourEquals("colorScheme.$role", DesignColors.getValue(tokenName), RigCheckLightColorScheme.role(role))
        }
    }

    @Test
    fun theColoursOutsideMaterial3EqualTheMappingInTheDesignFile() {
        val custom = tokens.getValue("material3_mapping").jsonObject.getValue("custom_colors_outside_m3").jsonObject
        val colours = RigCheckColors()
        val actual = mapOf(
            "success" to colours.success, "onSuccess" to colours.onSuccess, "successContainer" to colours.successContainer,
            "onSuccessContainer" to colours.onSuccessContainer, "notChecked" to colours.notChecked,
            "tealDeep" to colours.tealDeep, "purpleDeep" to colours.purpleDeep, "orangeDeep" to colours.orangeDeep,
            "dangerText" to colours.dangerText, "topBar" to colours.topBar, "onTopBar" to colours.onTopBar,
            "onTopBarWash" to colours.onTopBarWash,
        )
        assertEquals(custom.keys, actual.keys)
        for ((name, token) in custom) assertColourEquals(name, DesignColors.getValue(token.jsonPrimitive.content), actual.getValue(name))
    }

    @Test
    fun theShapesEqualTheDesignFile() {
        val shapes = tokens.getValue("material3_mapping").jsonObject.getValue("shapes").jsonObject
        val actual = mapOf(
            "extraSmall" to RigCheckShapes.extraSmall, "small" to RigCheckShapes.small, "medium" to RigCheckShapes.medium,
            "large" to RigCheckShapes.large, "extraLarge" to RigCheckShapes.extraLarge,
        )
        assertEquals(shapes.keys, actual.keys)
        for ((slot, shape) in actual) {
            val corners = shape as CornerBasedShape
            val size = Size(1000f, 1000f)
            val density = Density(1f)
            val expected = shapes.getValue(slot).jsonPrimitive.int.toFloat()
            assertEquals(slot, expected, corners.topStart.toPx(size, density), 0.01f)
            assertEquals(slot, expected, corners.bottomEnd.toPx(size, density), 0.01f)
        }
    }

    // ---- helpers

    private fun assertTextStyles(styles: RigCheckTextStyles, fonts: RigCheckFonts) {
        val expected = styleTokens()
        assertEquals(
            "text styles in tokens.json that the theme lacks, or the other way round",
            expected.map { it.string("name") }.toSet(),
            styles.byTokenName.keys,
        )
        for (token in expected) {
            val name = token.string("name")
            val style: TextStyle = styles.byTokenName.getValue(name)
            assertEquals("$name size", token.double("size_sp").toFloat(), style.fontSize.value, 0.001f)
            assertEquals("$name line height", token.double("line_height_sp").toFloat(), style.lineHeight.value, 0.001f)
            assertEquals("$name letter spacing", token.double("letter_spacing_sp").toFloat(), style.letterSpacing.value, 0.001f)
            assertEquals("$name weight", token.int("weight"), style.fontWeight!!.weight)
            val family = if (token.string("family") == "Outfit") fonts.display else fonts.body
            assertEquals("$name family", family, style.fontFamily)
        }
    }

    private fun styleTokens(): List<JsonObject> =
        tokens.getValue("typography").jsonObject.getValue("styles").jsonArray.map { it.jsonObject }

    private fun tokenColours(): Map<String, Color> {
        val groups = tokens.getValue("colors").jsonObject
        return groups.values.flatMap { (it as JsonArray).map { entry -> entry.jsonObject } }
            .associate { it.string("name") to parseColour(it.string("hex")) }
    }

    private fun parseColour(text: String): Color {
        val rgba = Regex("""rgba\((\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\)""").matchEntire(text)
        if (rgba != null) {
            val (r, g, b, a) = rgba.destructured
            return Color(r.toInt(), g.toInt(), b.toInt(), (a.toDouble() * 255).roundToInt())
        }
        assertTrue("not a #rrggbb colour: $text", Regex("#[0-9a-fA-F]{6}").matches(text))
        return Color(text.substring(1).toLong(16).toInt() or 0xFF000000.toInt())
    }

    private fun assertColourEquals(what: String, expected: Color, actual: Color) {
        assertEquals("$what (expected ${expected.hex()}, was ${actual.hex()})", expected.hex(), actual.hex())
    }

    private fun Color.hex(): String = "#%08X".format(
        (alpha * 255).roundToInt().toLong() shl 24 or ((red * 255).roundToInt().toLong() shl 16) or
            ((green * 255).roundToInt().toLong() shl 8) or (blue * 255).roundToInt().toLong(),
    )

    private fun assertDpMap(json: JsonObject, expected: Map<String, Dp>) {
        assertEquals("keys in tokens.json that the theme lacks, or the other way round", json.keys, expected.keys)
        for ((key, dp) in expected) assertEquals(key, json.getValue(key).jsonPrimitive.int.toFloat(), dp.value, 0.001f)
    }

    private fun ColorScheme.role(name: String): Color = when (name) {
        "primary" -> primary
        "onPrimary" -> onPrimary
        "primaryContainer" -> primaryContainer
        "onPrimaryContainer" -> onPrimaryContainer
        "secondary" -> secondary
        "onSecondary" -> onSecondary
        "secondaryContainer" -> secondaryContainer
        "onSecondaryContainer" -> onSecondaryContainer
        "tertiary" -> tertiary
        "onTertiary" -> onTertiary
        "tertiaryContainer" -> tertiaryContainer
        "onTertiaryContainer" -> onTertiaryContainer
        "background" -> background
        "onBackground" -> onBackground
        "surface" -> surface
        "onSurface" -> onSurface
        "surfaceVariant" -> surfaceVariant
        "onSurfaceVariant" -> onSurfaceVariant
        "outline" -> outline
        "outlineVariant" -> outlineVariant
        "error" -> error
        "onError" -> onError
        "errorContainer" -> errorContainer
        "onErrorContainer" -> onErrorContainer
        "scrim" -> scrim
        "inverseSurface" -> inverseSurface
        "inverseOnSurface" -> inverseOnSurface
        else -> error("tokens.json maps the Material 3 role '$name', which this test does not know")
    }

    private fun JsonObject.string(key: String) = getValue(key).jsonPrimitive.content
    private fun JsonObject.int(key: String) = getValue(key).jsonPrimitive.int
    private fun JsonObject.double(key: String) = getValue(key).jsonPrimitive.double

    private fun findTokens(): File {
        var dir: File? = File("").absoluteFile
        while (dir != null) {
            val candidate = File(dir, "docs/android-redesign/design-return/tokens.json")
            if (candidate.exists()) return candidate
            dir = dir.parentFile
        }
        error("Could not find docs/android-redesign/design-return/tokens.json by walking up from ${File("").absoluteFile}")
    }
}
