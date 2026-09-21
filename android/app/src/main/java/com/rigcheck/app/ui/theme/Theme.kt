package com.rigcheck.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

// Light-only for now - the mockups show no dark variant, and dynamic color
// (Material You) is deliberately off so this fixed brand palette is never
// overridden by the device's wallpaper-derived theme.
private val RigCheckLightColorScheme = lightColorScheme(
    primary = Orange,
    onPrimary = OnOrange,
    primaryContainer = TintOrange,
    onPrimaryContainer = Ink,
    secondary = Teal,
    onSecondary = OnTeal,
    secondaryContainer = TintTeal,
    onSecondaryContainer = Ink,
    tertiary = Purple,
    onTertiary = OnPurple,
    error = DangerRed,
    onError = Surface,
    background = Surface,
    onBackground = Ink,
    surface = Surface,
    onSurface = Ink,
    surfaceVariant = SurfaceSunken,
    onSurfaceVariant = InkMuted,
    outline = BorderStrong,
    outlineVariant = Border,
)

@Composable
fun RigCheckTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = RigCheckLightColorScheme,
        typography = Typography,
        content = content,
    )
}
