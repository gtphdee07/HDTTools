package com.rigcheck.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Intent
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.platform.testTag
import com.rigcheck.app.ui.util.FEEDBACK_EMAIL
import com.rigcheck.app.ui.util.feedbackIntent

// "Send feedback": opens a new email to the beta feedback address (#182), as Web's footer link does. A phone
// with no mail app gets a line saying so and the address to write to, not a crash. `startActivity` is a seam
// so a test can see the intent and fake a phone without a mail app.
@Composable
fun FeedbackLink(
    modifier: Modifier = Modifier,
    startActivity: (Intent) -> Unit = LocalContext.current::startActivity,
) {
    var noMailApp by remember { mutableStateOf(false) }
    Column(modifier = modifier) {
        TextButton(
            onClick = {
                noMailApp = try {
                    startActivity(feedbackIntent())
                    false
                } catch (_: ActivityNotFoundException) {
                    true
                }
            },
            modifier = Modifier.testTag("send_feedback"),
        ) {
            Text("Send feedback")
        }
        if (noMailApp) {
            Text(
                "This phone has no email app. Write to $FEEDBACK_EMAIL instead.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.testTag("send_feedback_no_mail_app"),
            )
        }
    }
}
