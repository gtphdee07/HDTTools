package com.rigcheck.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Intent
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.sp
import com.rigcheck.app.data.CrashReportStore
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.util.FEEDBACK_EMAIL
import com.rigcheck.app.ui.util.crashReportIntent

// The next-launch question after a crash (#184). Shows only while a saved report is waiting. "Send" opens an
// email to the feedback address with the report as the body, "Not now" (or tapping outside, or Back) throws
// it away; either answer deletes the report, so the question is asked once. The report stays on the phone
// until then, so turning the screen or reopening the app without answering shows the same question.
// `startActivity` is a seam so a test can see the intent and fake a phone without a mail app.
@Composable
fun CrashReportPrompt(
    store: CrashReportStore,
    startActivity: (Intent) -> Unit = LocalContext.current::startActivity,
) {
    var report by remember { mutableStateOf(store.pending()) }
    var noMailApp by remember { mutableStateOf(false) }
    val pendingReport = report ?: return

    fun answered() {
        store.clear()
        report = null
        noMailApp = false
    }

    // The design's dialog (components.md, "Dialog"; frames crash_report_dialog__question and __no_email_app): the question
    // is its heading and the details its body; once there is no mail app the question and details go and the line about
    // it is the whole dialog. Send, then Not now (OK after the no-mail line), stacked full width.
    RigCheckDialog(
        onDismissRequest = ::answered,
        title = if (noMailApp) {
            null
        } else {
            {
                Text(
                    "RigCheck closed unexpectedly last time. Send details?",
                    style = RigCheckStyles.titleLg,
                    color = Ink,
                    modifier = Modifier.testTag(UiTags.CRASH_PROMPT_QUESTION),
                )
            }
        },
        body = {
            if (noMailApp) {
                Text(
                    "This phone has no email app. Write to $FEEDBACK_EMAIL instead.",
                    style = RigCheckStyles.body.copy(lineHeight = 24.sp),
                    color = Ink,
                    modifier = Modifier.testTag(UiTags.CRASH_PROMPT_NO_MAIL_APP),
                )
            } else {
                Text(
                    "It holds the error, the app version, your Android version and phone model. " +
                        "Nothing about your account or your rigs. Nothing is sent unless you tap Send.",
                    style = RigCheckStyles.bodySm,
                    color = InkMuted,
                    modifier = Modifier.testTag(UiTags.CRASH_PROMPT_DETAILS),
                )
            }
        },
    ) {
        if (!noMailApp) {
            RigCheckButton(
                text = "Send",
                onClick = {
                    try {
                        startActivity(crashReportIntent(pendingReport))
                        answered()
                    } catch (_: ActivityNotFoundException) {
                        noMailApp = true
                    }
                },
                size = RigCheckButtonSize.Dialog,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.CRASH_PROMPT_SEND),
            )
        }
        RigCheckButton(
            text = if (noMailApp) "OK" else "Not now",
            onClick = ::answered,
            kind = RigCheckButtonKind.Ghost,
            size = RigCheckButtonSize.Dialog,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.CRASH_PROMPT_DISMISS),
        )
    }
}
