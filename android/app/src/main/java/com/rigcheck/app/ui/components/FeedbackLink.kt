package com.rigcheck.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.util.FEEDBACK_EMAIL
import com.rigcheck.app.ui.util.feedbackIntent

// "Send feedback": opens a new email to the beta feedback address (#182), as Web's footer link does. A phone
// with no mail app gets a line saying so and the address to write to, not a crash. `startActivity` is a seam
// so a test can see the intent and fake a phone without a mail app. `linkModifier` is for the button itself (its
// test tag differs per screen). Drawn as the design's text link (components.md, "Text link (Send feedback)"): a
// ghost button at 48 dp, centred, with the no-mail line under it in `caption`.
@Composable
fun FeedbackLink(
    modifier: Modifier = Modifier,
    linkModifier: Modifier = Modifier,
    startActivity: (Intent) -> Unit = LocalContext.current::startActivity,
) {
    var noMailApp by remember { mutableStateOf(false) }
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
        modifier = modifier,
    ) {
        RigCheckButton(
            text = "Send feedback",
            kind = RigCheckButtonKind.Ghost,
            size = RigCheckButtonSize.Compact,
            modifier = linkModifier,
            onClick = {
                noMailApp = try {
                    startActivity(feedbackIntent())
                    false
                } catch (_: ActivityNotFoundException) {
                    true
                }
            },
        )
        if (noMailApp) {
            Text(
                "This phone has no email app. Write to $FEEDBACK_EMAIL instead.",
                style = RigCheckStyles.caption,
                color = InkMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.testTag(UiTags.SEND_FEEDBACK_NO_MAIL_APP),
            )
        }
    }
}
