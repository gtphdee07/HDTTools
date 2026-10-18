package com.rigcheck.app.ui.components

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable

// Tells the user about a Scan that answered after they left its check (#118):
// the message already says whether a Scan Credit was used. Shown by the
// navigation host, so it appears on whichever screen the user is on; OK is the
// only way forward, since the check the Scan belonged to is gone.
@Composable
fun LateScanDialog(message: String, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onClick = onDismiss) { Text("OK") } },
        title = { Text("A Scan finished late") },
        text = { Text(message) },
    )
}
