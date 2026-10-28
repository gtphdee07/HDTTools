package com.rigcheck.app.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf

// Light-only - the design has no dark variant, and dynamic color (Material You) is deliberately off so this fixed
// brand palette is never overridden by the device's wallpaper-derived theme. The roles are `material3_mapping` in
// tokens.json (DesignTokensTest compares them). The container roles tokens.json does not name are white, because
// the design draws every dialog, sheet and menu white (the Material defaults would tint them lilac).
val RigCheckLightColorScheme: ColorScheme = lightColorScheme(
    primary = Orange,
    onPrimary = Ink,
    primaryContainer = TintOrange,
    onPrimaryContainer = OrangeDeep,
    secondary = Teal,
    onSecondary = Ink,
    secondaryContainer = TintTeal,
    onSecondaryContainer = TealDeep,
    tertiary = Purple,
    onTertiary = Surface,
    tertiaryContainer = TintPurple,
    onTertiaryContainer = PurpleDeep,
    background = Surface,
    onBackground = Ink,
    surface = Surface,
    onSurface = Ink,
    surfaceVariant = SurfaceSunken,
    onSurfaceVariant = InkMuted,
    outline = BorderStrong,
    outlineVariant = Border,
    error = DangerRed,
    onError = Surface,
    errorContainer = TintRed,
    onErrorContainer = DangerText,
    scrim = Ink,
    inverseSurface = Ink,
    inverseOnSurface = Surface,
    inversePrimary = Orange,
    surfaceTint = Surface,
    surfaceDim = Surface,
    surfaceBright = Surface,
    surfaceContainerLowest = Surface,
    surfaceContainerLow = Surface,
    surfaceContainer = Surface,
    surfaceContainerHigh = Surface,
    surfaceContainerHighest = SurfaceSunken,
)

val LocalRigCheckColors = staticCompositionLocalOf { RigCheckColors() }

/** `MaterialTheme.rigCheckColors.success` etc.: the design's colours that Material 3 has no role for. */
val MaterialTheme.rigCheckColors: RigCheckColors
    @Composable
    @ReadOnlyComposable
    get() = LocalRigCheckColors.current

@Composable
fun RigCheckTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalRigCheckColors provides RigCheckColors()) {
        MaterialTheme(
            colorScheme = RigCheckLightColorScheme,
            typography = Typography,
            shapes = RigCheckShapes,
            content = content,
        )
    }
}
