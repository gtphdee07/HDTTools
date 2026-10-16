package com.rigcheck.app.ui.components

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState

// The "Scan failed" dialog both Scan entry points show. OK always dismisses;
// when the failure has a way forward (signing in, buying scans) the dialog
// offers it as the main button and passes the step to `onNextStep`.
@Composable
fun ScanErrorDialog(
    error: ScanUiState.Error,
    onDismiss: () -> Unit,
    onNextStep: (ScanNextStep) -> Unit,
) {
    val nextStepLabel = when (error.nextStep) {
        ScanNextStep.SIGN_IN -> "Sign in"
        ScanNextStep.BUY_SCANS -> "Buy scans"
        ScanNextStep.NONE -> null
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            if (nextStepLabel != null) {
                TextButton(onClick = { onNextStep(error.nextStep) }) { Text(nextStepLabel) }
            } else {
                TextButton(onClick = onDismiss) { Text("OK") }
            }
        },
        dismissButton = if (nextStepLabel != null) {
            { TextButton(onClick = onDismiss) { Text("OK") } }
        } else {
            null
        },
        title = { Text("Scan failed") },
        text = { Text(error.message) },
    )
}
