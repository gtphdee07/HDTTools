package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.RigCheckStyles

// Tells the user about a Scan that answered after they left its check (#118): the message already says whether a
// Scan Credit was used. Shown by the navigation host, so it appears on whichever screen the user is on; OK, a ghost
// button in the design's dialog (components.md, "Dialog"), is the only way forward, since the check the Scan belonged
// to is gone.
@Composable
fun LateScanDialog(message: String, onDismiss: () -> Unit) {
    RigCheckDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                "A Scan finished late",
                style = RigCheckStyles.titleLg,
                color = Ink,
                modifier = Modifier.testTag(UiTags.LATE_SCAN_TITLE),
            )
        },
        body = {
            Text(
                message,
                style = RigCheckStyles.body.copy(lineHeight = 24.sp),
                color = Ink,
                modifier = Modifier.testTag(UiTags.LATE_SCAN_MESSAGE),
            )
        },
    ) {
        RigCheckButton(
            text = "OK",
            onClick = onDismiss,
            kind = RigCheckButtonKind.Ghost,
            size = RigCheckButtonSize.Dialog,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.LATE_SCAN_OK_BUTTON),
        )
    }
}
