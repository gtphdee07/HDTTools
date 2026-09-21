package com.rigcheck.app.ui.theme

import androidx.compose.ui.graphics.Color

// Ported from web/src/design-system/tokens.css ("Wandering Trails, Wagging
// Tails" brand palette) - keep in sync if the web app's tokens ever change.
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

// Text/icons on top of a bright saturated fill - never white on teal or
// orange (both fail contrast at that weight per the brand tokens).
val OnTeal = Ink
val OnPurple = Surface
val OnOrange = Ink

// Rig-picker avatar rotation - deterministic, cycles through the three
// non-primary accents by list index (no per-rig color stored/chosen).
val AvatarPalette = listOf(Pine, Purple, Blush)
