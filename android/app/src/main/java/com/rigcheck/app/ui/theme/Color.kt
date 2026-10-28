package com.rigcheck.app.ui.theme

import androidx.compose.ui.graphics.Color

// The hand-back's tokens.json (docs/android-redesign/design-return/) is the source; DesignTokensTest compares
// every constant here with it. Brand colours are the same as web/src/design-system/tokens.css.
val Teal = Color(0xFF12B5AE)
val TealDeep = Color(0xFF087379)
val Purple = Color(0xFF7B3FE4)
val PurpleDeep = Color(0xFF5B25B8)
val Orange = Color(0xFFFF7A1A)
val OrangeDeep = Color(0xFFB84A00)

val Sunshine = Color(0xFFFFB627)
val Sky = Color(0xFF2F9BEF)
val Pine = Color(0xFF3F6B35)
val Slate = Color(0xFF576775)
val Blush = Color(0xFFE9A3A0)

val Ink = Color(0xFF16131F)
val InkMuted = Color(0xFF55506A)
val Surface = Color(0xFFFFFFFF)
val SurfaceSunken = Color(0xFFF4F8F9)
val Border = Color(0xFFD5DEE3)
val BorderStrong = Color(0xFF738490)

val TintTeal = Color(0xFFE3F7F5)
val TintPurple = Color(0xFFF1ECFF)
val TintOrange = Color(0xFFFFF0E1)

val DangerRed = Color(0xFFB5473A)

// Added by the redesign (tokens.json "proposed"): fail as text, the over-limit and within-limit fills, the disabled
// button, and the white wash on the teal bar.
val DangerText = Color(0xFF9A3A2E)
val TintRed = Color(0xFFF8E6E3)
val TintGreen = Color(0xFFE8F0E5)
val DisabledFill = Color(0xFFE4E0EE)
val DisabledContent = Color(0xFF6A647C)
val OnTealWash = Color(0xB8FFFFFF) // rgba(255, 255, 255, 0.72)

// The sky gradient of the app icon and the splash disc (top to bottom).
val SkyGradientTop = Purple
val SkyGradientBottom = Orange

// Text/icons on top of a bright saturated fill - never white on teal or
// orange (both fail contrast at that weight per the brand tokens).
val OnTeal = Ink
val OnPurple = Surface
val OnOrange = Ink

// Rig-picker avatar rotation - deterministic, cycles through the three
// non-primary accents by list index (no per-rig color stored/chosen).
val AvatarPalette = listOf(Pine, Purple, Blush)
