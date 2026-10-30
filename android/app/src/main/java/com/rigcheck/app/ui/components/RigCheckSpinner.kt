package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.TealDeep

// components.md, "Progress bar, spinner, toast, empty state, divider": 40 dp (48 in the Scan overlay), a 4 dp ring in
// `border` with a `teal-deep` arc, indeterminate.
@Composable
fun RigCheckSpinner(modifier: Modifier = Modifier, size: Dp = 40.dp) {
    CircularProgressIndicator(
        modifier = modifier.size(size),
        color = TealDeep,
        trackColor = Border,
        strokeWidth = 4.dp,
    )
}
