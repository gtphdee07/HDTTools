package com.rigcheck.app.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

// The non-colour, non-text tokens of the design hand-back (docs/android-redesign/design-return/tokens.json).
// DesignTokensTest compares each with the file and fails on any difference.

object Spacing {
    val values: List<Dp> = listOf(4.dp, 8.dp, 12.dp, 16.dp, 24.dp, 32.dp, 48.dp, 64.dp)
    val ScreenMargin = 16.dp
}

object Radii {
    val Input = 8.dp
    val Card = 14.dp
    val Panel = 24.dp
    val Band = 24.dp
    val SheetTop = 24.dp
    val Dialog = 24.dp
    val Pill = 999.dp
}

/** Compose elevations of the design's shadows: sm resting cards, buttons and chips; md band, dialogs; footer pinned bars. */
object Elevations {
    val Sm = 2.dp
    val Md = 8.dp
    val Footer = 4.dp
}

object Sizes {
    val TouchTargetMin = 48.dp
    val Button = 56.dp
    val ButtonCompact = 48.dp
    val ButtonInDialog = 52.dp
    val TextField = 56.dp
    val CreditChip = 48.dp
    val CreditChipIcon = 26.dp
    val TopBarLogo = 52.dp
    val IconButton = 48.dp
    val RowStatusIcon = 26.dp
    val ProgressBar = 10.dp
    val SliderThumb = 28.dp
    val StatusBarAllowance = 24.dp
    val NavBarAllowance = 48.dp
}

object Opacity {
    const val Scrim = 0.55f
    const val ScanOverlayWash = 0.88f
    const val OnTealWash = 0.72f
    const val StepConnector = 0.35f
    const val DisabledField = 0.7f
    const val Disabled = 0.38f
}

object Motion {
    const val ShortMs = 100
    const val MediumMs = 200
    const val LongMs = 300
}

/** Material 3 shape slots from `material3_mapping.shapes`. */
val RigCheckShapes = Shapes(
    extraSmall = RoundedCornerShape(Radii.Input),
    small = RoundedCornerShape(Radii.Input),
    medium = RoundedCornerShape(Radii.Card),
    large = RoundedCornerShape(Radii.Panel),
    extraLarge = RoundedCornerShape(Radii.Panel),
)

/** Colours outside Material 3's roles (`material3_mapping.custom_colors_outside_m3`). */
class RigCheckColors(
    val success: Color = Pine,
    val onSuccess: Color = Surface,
    val successContainer: Color = TintGreen,
    val onSuccessContainer: Color = Pine,
    val notChecked: Color = Slate,
    val tealDeep: Color = TealDeep,
    val purpleDeep: Color = PurpleDeep,
    val orangeDeep: Color = OrangeDeep,
    val dangerText: Color = DangerText,
    val topBar: Color = Teal,
    val onTopBar: Color = Ink,
    val onTopBarWash: Color = OnTealWash,
)

/** Every colour of tokens.json by its token name, except the design-frames-only `keyboard-placeholder`. */
val DesignColors: Map<String, Color> = mapOf(
    "orange" to Orange, "teal" to Teal, "purple" to Purple,
    "orange-deep" to OrangeDeep, "teal-deep" to TealDeep, "purple-deep" to PurpleDeep,
    "sunshine" to Sunshine, "sky" to Sky, "pine" to Pine, "slate" to Slate, "blush" to Blush, "danger" to DangerRed,
    "ink" to Ink, "ink-muted" to InkMuted, "surface" to Surface, "surface-sunken" to SurfaceSunken,
    "border" to Border, "border-strong" to BorderStrong,
    "tint-teal" to TintTeal, "tint-purple" to TintPurple, "tint-orange" to TintOrange,
    "danger-text" to DangerText, "tint-red" to TintRed, "tint-green" to TintGreen,
    "disabled-fill" to DisabledFill, "disabled-content" to DisabledContent, "on-teal-wash" to OnTealWash,
)
