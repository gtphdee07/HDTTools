package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags

private fun labelFor(step: ScanNextStep): String = when (step) {
    ScanNextStep.SIGN_IN -> "Sign in"
    ScanNextStep.BUY_SCANS -> "Buy more Scans"
    ScanNextStep.TRY_AGAIN -> "Try again"
    ScanNextStep.CHOOSE_DIFFERENT_PHOTO -> "Choose a different photo"
    ScanNextStep.TYPE_IT_IN -> "Type it in"
}

private fun tagFor(step: ScanNextStep): String = when (step) {
    ScanNextStep.SIGN_IN -> UiTags.SCAN_ERROR_NEXT_SIGN_IN
    ScanNextStep.BUY_SCANS -> UiTags.SCAN_ERROR_NEXT_BUY_SCANS
    ScanNextStep.TRY_AGAIN -> UiTags.SCAN_ERROR_NEXT_TRY_AGAIN
    ScanNextStep.CHOOSE_DIFFERENT_PHOTO -> UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO
    ScanNextStep.TYPE_IT_IN -> UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN
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
            Column(
                modifier = Modifier.fillMaxWidth().testTag(UiTags.SCAN_ERROR_NEXT_STEP_BUTTON),
                horizontalAlignment = Alignment.End,
            ) {
                error.nextSteps.forEach { step ->
                    TextButton(onClick = { onNextStep(step) }, modifier = Modifier.testTag(tagFor(step))) {
                        Text(labelFor(step))
                    }
                }
                TextButton(onClick = onDismiss, modifier = Modifier.testTag(UiTags.SCAN_ERROR_OK_BUTTON)) { Text("OK") }
            }
        },
        title = { Text("Scan failed", modifier = Modifier.testTag(UiTags.SCAN_ERROR_TITLE)) },
        text = { Text(error.message, modifier = Modifier.testTag(UiTags.SCAN_ERROR_MESSAGE)) },
    )
}
