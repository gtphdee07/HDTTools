package com.rigcheck.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

// Light-only for now - the mockups show no dark variant, and dynamic color
// (Material You) is deliberately off so this fixed brand palette is never
// overridden by the device's wallpaper-derived theme.
private val RigCheckLightColorScheme = lightColorScheme(
    primary = SunsetOrange,
    onPrimary = White,
    primaryContainer = SunsetOrangeLight,
    onPrimaryContainer = Charcoal,
    secondary = TrailGreen,
    onSecondary = White,
    secondaryContainer = TrailGreenLight,
    onSecondaryContainer = Charcoal,
    tertiary = DuskMauve,
    onTertiary = White,
    error = DangerRed,
    onError = White,
    background = Cream,
    onBackground = Charcoal,
    surface = White,
    onSurface = Charcoal,
    surfaceVariant = CreamDark,
    onSurfaceVariant = CharcoalSoft,
    outline = Mist,
    outlineVariant = Mist,
)

@Composable
fun RigCheckTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = RigCheckLightColorScheme,
        typography = Typography,
        content = content,
    )
}
