package com.rigcheck.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Intent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.rigcheck.app.data.CrashReportStore
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

    AlertDialog(
        onDismissRequest = ::answered,
        text = {
            Column {
                if (noMailApp) {
                    Text("This phone has no email app. Write to $FEEDBACK_EMAIL instead.")
                } else {
                    Text("RigCheck closed unexpectedly last time. Send details?")
                    Text(
                        "It holds the error, the app version, your Android version and phone model. " +
                            "Nothing about your account or your rigs. Nothing is sent unless you tap Send.",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }
        },
        confirmButton = {
            if (!noMailApp) {
                TextButton(
                    onClick = {
                        try {
                            startActivity(crashReportIntent(pendingReport))
                            answered()
                        } catch (_: ActivityNotFoundException) {
                            noMailApp = true
                        }
                    },
                ) {
                    Text("Send")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = ::answered) {
                Text(if (noMailApp) "OK" else "Not now")
            }
        },
    )
}
