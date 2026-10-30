package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.RigCheckStyles

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

// The "Scan failed" dialog both Scan entry points show, in the design's dialog (components.md, "Dialog"). OK always
// dismisses; when the failure has a way forward (signing in, buying Scans, trying again, another photo, typing the
// numbers in) the dialog offers each as a button above OK and passes the chosen step to `onNextStep`. The buttons are
// stacked at full width: the first next step is the primary, any further one a secondary, OK a ghost button last.
// Each next step sits in a wrapper tagged `scan_error_next_step_button`, so the tag measures one button, as the map's
// frames do, and the step's own tag stays on the button.
@Composable
fun ScanErrorDialog(
    error: ScanUiState.Error,
    onDismiss: () -> Unit,
    onNextStep: (ScanNextStep) -> Unit,
) {
    RigCheckDialog(
        onDismissRequest = onDismiss,
        title = {
            Text("Scan failed", style = RigCheckStyles.titleLg, color = Ink, modifier = Modifier.testTag(UiTags.SCAN_ERROR_TITLE))
        },
        body = {
            Text(
                error.message,
                style = RigCheckStyles.body.copy(lineHeight = 24.sp),
                color = Ink,
                modifier = Modifier.testTag(UiTags.SCAN_ERROR_MESSAGE),
            )
        },
    ) {
        error.nextSteps.forEachIndexed { index, step ->
            Box(modifier = Modifier.fillMaxWidth().testTag(UiTags.SCAN_ERROR_NEXT_STEP_BUTTON)) {
                RigCheckButton(
                    text = labelFor(step),
                    onClick = { onNextStep(step) },
                    kind = if (index == 0) RigCheckButtonKind.Primary else RigCheckButtonKind.Secondary,
                    size = RigCheckButtonSize.Dialog,
                    modifier = Modifier.fillMaxWidth().testTag(tagFor(step)),
                )
            }
        }
        RigCheckButton(
            text = "OK",
            onClick = onDismiss,
            kind = RigCheckButtonKind.Ghost,
            size = RigCheckButtonSize.Dialog,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.SCAN_ERROR_OK_BUTTON),
        )
    }
}
