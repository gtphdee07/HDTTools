package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState

private fun labelFor(step: ScanNextStep): String = when (step) {
    ScanNextStep.SIGN_IN -> "Sign in"
    ScanNextStep.BUY_SCANS -> "Buy more Scans"
    ScanNextStep.TRY_AGAIN -> "Try again"
    ScanNextStep.CHOOSE_DIFFERENT_PHOTO -> "Choose a different photo"
    ScanNextStep.TYPE_IT_IN -> "Type it in"
}

// The "Scan failed" dialog both Scan entry points show. OK always dismisses;
// when the failure has a way forward (signing in, buying Scans, trying again,
// another photo, typing the numbers in) the dialog offers each as a button above
// OK and passes the chosen step to `onNextStep`.
@Composable
fun ScanErrorDialog(
    error: ScanUiState.Error,
    onDismiss: () -> Unit,
    onNextStep: (ScanNextStep) -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = Alignment.End) {
                error.nextSteps.forEach { step ->
                    TextButton(onClick = { onNextStep(step) }) { Text(labelFor(step)) }
                }
                TextButton(onClick = onDismiss) { Text("OK") }
            }
        },
        title = { Text("Scan failed") },
        text = { Text(error.message) },
    )
}
