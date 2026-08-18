package com.rigcheck.app.ui.theme

import androidx.compose.ui.graphics.Color

// Ported from web/src/design-system/tokens.css ("Wandering Trails, Wagging
// Tails" brand palette) - keep in sync if the web app's tokens ever change.
val SunsetOrange = Color(0xFFF0942F)
val SunsetOrangeLight = Color(0xFFFFB050)
val SunsetOrangeDark = Color(0xFFC9701A)

val TrailGreen = Color(0xFF4D7A3A)
val TrailGreenLight = Color(0xFF6F9A56)
val TrailGreenDark = Color(0xFF33552B)

val DuskMauve = Color(0xFF8D7FA0)
val SunsetRose = Color(0xFFC17F8F)

val Charcoal = Color(0xFF2A2A28)
val CharcoalSoft = Color(0xFF4A4844)
val Cream = Color(0xFFF6EFE4)
val CreamDark = Color(0xFFECE1CF)
val Mist = Color(0xFFD9D2D6)
val White = Color(0xFFFFFFFF)

val DangerRed = Color(0xFFB5473A)

// Rig-picker avatar rotation - deterministic, cycles through the three
// non-primary accents by list index (no per-rig color stored/chosen).
val AvatarPalette = listOf(TrailGreen, DuskMauve, SunsetRose)
