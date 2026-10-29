package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

// resize-rules.md, "Layout skeleton, every screen": the primary action is pinned in a footer with a top shadow, under
// the part of the screen that scrolls. The 64 dp the frames leave under it is the navigation bar; here RigCheckApp's
// safe-drawing padding already keeps the screen clear of the bars, so the footer adds only the 12 dp of the design.
@Composable
fun RigCheckFooter(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Surface(color = SurfaceWhite, shadowElevation = Elevations.Footer, modifier = modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(start = 16.dp, top = 12.dp, end = 16.dp, bottom = 12.dp), content = content)
    }
}
