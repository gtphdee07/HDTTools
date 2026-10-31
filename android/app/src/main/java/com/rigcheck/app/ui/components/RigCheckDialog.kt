package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.DialogWindowProvider
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

// components.md, "Dialog": 24 dp radius, 24 dp padding, 364 dp wide (the screen's width less 16 dp on each side on a
// narrower phone), shadow md, a scrim at 55%. The title, the body, then the buttons stacked full width at 52 dp
// (RigCheckButtonSize.Dialog): the primary first, the secondary second, a ghost OK or Cancel last. The caller passes
// the pieces and their tags. A dialog with no heading of its own (the crash report's "no email app" line, #197) has
// only a body.
@Composable
fun RigCheckDialog(
    onDismissRequest: () -> Unit,
    modifier: Modifier = Modifier,
    title: (@Composable () -> Unit)? = null,
    body: (@Composable () -> Unit)? = null,
    buttons: @Composable ColumnScope.() -> Unit,
) {
    Dialog(onDismissRequest = onDismissRequest, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        val window = (LocalView.current.parent as? DialogWindowProvider)?.window
        SideEffect { window?.setDimAmount(Opacity.Scrim) }
        Surface(
            shape = RoundedCornerShape(Radii.Dialog),
            color = SurfaceWhite,
            shadowElevation = Elevations.Md,
            modifier = modifier.padding(horizontal = 16.dp).widthIn(max = 364.dp).fillMaxWidth(),
        ) {
            // Scrolls, so that at a large font on a small phone the buttons are still reachable.
            Column(modifier = Modifier.verticalScroll(rememberScrollState()).padding(24.dp)) {
                title?.invoke()
                if (body != null) {
                    Column(modifier = Modifier.padding(top = if (title != null) 12.dp else 0.dp)) { body() }
                }
                Column(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(top = 20.dp),
                    content = buttons,
                )
            }
        }
    }
}
