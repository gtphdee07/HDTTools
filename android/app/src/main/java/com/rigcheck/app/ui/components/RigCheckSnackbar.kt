package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarData
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

// components.md, "Progress bar, spinner, toast, empty state, divider" and "Beta notice and Snackbar": an `ink` fill, white
// `body-md` text, a 14 dp radius and 16 dp side margins; no action button. Shown for 4 s (SnackbarDuration.Short) and
// then it fades. The caller puts the host where the design wants it and tags the snackbar.
@Composable
fun RigCheckSnackbarHost(
    state: SnackbarHostState,
    modifier: Modifier = Modifier,
    snackbarModifier: Modifier = Modifier,
) {
    SnackbarHost(hostState = state, modifier = modifier.padding(horizontal = 16.dp)) { data: SnackbarData ->
        Snackbar(
            modifier = snackbarModifier,
            shape = RoundedCornerShape(14.dp),
            containerColor = Ink,
            contentColor = SurfaceWhite,
        ) {
            Text(data.visuals.message, style = RigCheckStyles.bodyMd, color = SurfaceWhite)
        }
    }
}
