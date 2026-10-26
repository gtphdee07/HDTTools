package com.rigcheck.app.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.rigcheck.app.ui.theme.RigCheckTheme

// The app's root: the theme, a background that fills the whole window, and the one rule
// that keeps every screen clear of the system bars (#186). MainActivity draws edge to
// edge, so the window reaches behind the status bar and the navigation bar (the keys of
// 3-button navigation, or the gesture handle); the safe-drawing padding here pushes the
// screens' content and controls inside them, along with any display cutout and the
// keyboard. The background still paints behind the bars. A screen needs no padding of
// its own for this; one that wants to draw behind the bars (a camera preview) would
// have to opt out explicitly.
@Composable
fun RigCheckApp(content: @Composable () -> Unit = { RigCheckNavHost() }) {
    RigCheckTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Box(modifier = Modifier.fillMaxSize().safeDrawingPadding()) {
                content()
            }
        }
    }
}
