package com.rigcheck.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.rigcheck.app.R

// Outfit (display) and DM Sans (body) are bundled as app resources (res/font, SIL Open Font License, texts in
// android/font-licenses/), so the first launch with no network does not fall back to the system font. Each file is a
// variable font; a weight is picked by its variation setting.

/**
 * The two families the text styles are built on. [Bundled] is what the app uses. [Fallback] is the design's own
 * fallback for either family (tokens.json: "system sans-serif"), for a build or a test where the bundled files are
 * not available; every text style is still set explicitly, never left on the platform default.
 */
class RigCheckFonts(val display: FontFamily, val body: FontFamily) {
    // The font builders live here, not at file level: a file-level function would initialise TypeKt, whose own
    // properties read Bundled before it is assigned.
    companion object {
        @OptIn(ExperimentalTextApi::class)
        private fun variable(resId: Int, weight: Int) = Font(
            resId,
            FontWeight(weight),
            variationSettings = FontVariation.Settings(FontVariation.weight(weight)),
        )

        val Bundled = RigCheckFonts(
            display = FontFamily(
                variable(R.font.outfit_variable, 600),
                variable(R.font.outfit_variable, 700),
                variable(R.font.outfit_variable, 800),
            ),
            body = FontFamily(
                variable(R.font.dm_sans_variable, 400),
                variable(R.font.dm_sans_variable, 500),
                variable(R.font.dm_sans_variable, 700),
            ),
        )
        val Fallback = RigCheckFonts(display = FontFamily.SansSerif, body = FontFamily.SansSerif)
    }
}

val OutfitFamily: FontFamily get() = RigCheckFonts.Bundled.display
val DMSansFamily: FontFamily get() = RigCheckFonts.Bundled.body

/** The 17 named text styles of tokens.json, by the token's name (`title-lg`, `body-md`, ...). */
class RigCheckTextStyles(fonts: RigCheckFonts) {
    val headlineVerdict = display(fonts, 800, 30, 34, -0.3)
    val heading = display(fonts, 800, 28, 34, -0.28)
    val topBarTitle = display(fonts, 800, 26, 30, -0.26)
    val titleLg = display(fonts, 700, 22, 28, 0.0)
    val offerTitle = display(fonts, 800, 22, 28, 0.0)
    val title = display(fonts, 700, 18, 22, 0.0)
    val titleSm = display(fonts, 700, 16, 22, 0.0)
    val button = display(fonts, 700, 17, 22, 0.0)
    val buttonCompact = display(fonts, 600, 15, 20, 0.0)
    val chip = display(fonts, 700, 17, 22, 0.0)
    val body = body(fonts, 400, 16, 22, 0.0)
    val bodyMd = body(fonts, 400, 15, 21, 0.0)
    val bodySm = body(fonts, 400, 14, 20, 0.0)
    val caption = body(fonts, 400, 13, 18, 0.0)
    val micro = body(fonts, 400, 12, 16, 0.0)
    val label = body(fonts, 700, 13, 16, 0.52)
    val badge = body(fonts, 700, 13, 18, 0.0)

    /** token name -> style, for the tokens test. */
    val byTokenName: Map<String, TextStyle> = mapOf(
        "headline-verdict" to headlineVerdict, "heading" to heading, "top-bar-title" to topBarTitle,
        "title-lg" to titleLg, "offer-title" to offerTitle, "title" to title, "title-sm" to titleSm,
        "button" to button, "button-compact" to buttonCompact, "chip" to chip, "body" to body, "body-md" to bodyMd,
        "body-sm" to bodySm, "caption" to caption, "micro" to micro, "label" to label, "badge" to badge,
    )

    private fun display(f: RigCheckFonts, weight: Int, size: Int, line: Int, spacing: Double) =
        style(f.display, weight, size, line, spacing)

    private fun body(f: RigCheckFonts, weight: Int, size: Int, line: Int, spacing: Double) =
        style(f.body, weight, size, line, spacing)

    private fun style(family: FontFamily, weight: Int, size: Int, line: Int, spacing: Double) = TextStyle(
        fontFamily = family,
        fontWeight = FontWeight(weight),
        fontSize = size.sp,
        lineHeight = line.sp,
        letterSpacing = spacing.sp,
    )
}

/**
 * Every Material 3 slot is set explicitly, to one of the named styles, so no component can reach the platform default
 * font. The mapping is the app's choice (the design names styles, not M3 slots); screens use the named styles
 * directly where the design says to.
 */
fun rigCheckTypography(styles: RigCheckTextStyles): Typography = Typography(
    displayLarge = styles.headlineVerdict,
    displayMedium = styles.headlineVerdict,
    displaySmall = styles.heading,
    headlineLarge = styles.heading,
    headlineMedium = styles.topBarTitle,
    headlineSmall = styles.titleLg,
    titleLarge = styles.titleLg,
    titleMedium = styles.title,
    titleSmall = styles.titleSm,
    bodyLarge = styles.body,
    bodyMedium = styles.bodyMd,
    bodySmall = styles.bodySm,
    labelLarge = styles.button,
    labelMedium = styles.label,
    labelSmall = styles.micro,
)

val RigCheckStyles = RigCheckTextStyles(RigCheckFonts.Bundled)
val Typography = rigCheckTypography(RigCheckStyles)
