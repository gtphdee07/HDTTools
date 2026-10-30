package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.FeedbackLink
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckButtonKind
import com.rigcheck.app.ui.components.RigCheckButtonSize
import com.rigcheck.app.ui.components.RigCheckFooter
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckTextField
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.RigCheckStyles

private const val MIN_PASSWORD_LENGTH = 6

// Sign in / create an account with email, Google or Apple. Shown only when
// something needs an account (buying or scanning) - the free manual-entry
// flow never reaches it. A successful sign-in isn't reported here: the
// caller's account state flips to signed-in and swaps this screen out.
//
// On the design's skeleton (resize-rules.md, "What scrolls and what is pinned"): the top bar (Back and the title) is
// pinned, the reason, the fields and the buttons scroll as one column, and Not now is pinned in the footer. Back and
// Not now both leave through `onNotNow`.
@Composable
fun AccountScreen(
    reason: String,
    // Off until Apple sign-in is set up (#77); the flow itself is built.
    showApple: Boolean,
    onSignIn: (email: String, password: String, (AccountResult) -> Unit) -> Unit,
    onSignUp: (email: String, password: String, (AccountResult) -> Unit) -> Unit,
    onGoogle: ((AccountResult) -> Unit) -> Unit,
    onApple: ((AccountResult) -> Unit) -> Unit,
    onForgotPassword: (email: String, (AccountResult) -> Unit) -> Unit,
    onNotNow: () -> Unit,
) {
    var creating by remember { mutableStateOf(false) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isBusy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var info by remember { mutableStateOf<String?>(null) }

    // Every action funnels through here: clears the old message, disables
    // the form while in flight, and turns the outcome into one message.
    fun perform(successInfo: String?, action: ((AccountResult) -> Unit) -> Unit) {
        isBusy = true
        error = null
        info = null
        action { result ->
            isBusy = false
            when (result) {
                is AccountResult.Success -> info = successInfo
                is AccountResult.NeedsConfirmation ->
                    info = "Check your email to confirm your account, then sign in."
                is AccountResult.Cancelled -> Unit
                is AccountResult.Failure -> error = result.message
            }
        }
    }

    val canSubmit = !isBusy && email.isNotBlank() && password.length >= MIN_PASSWORD_LENGTH

    Column(modifier = Modifier.fillMaxSize()) {
        RigCheckTopBar(
            title = if (creating) "Create your account" else "Sign in",
            onBack = onNotNow,
            titleModifier = Modifier.testTag(UiTags.ACCOUNT_TITLE),
            backModifier = Modifier.testTag(UiTags.ACCOUNT_BACK),
        )

        Column(
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, top = 20.dp, end = 16.dp, bottom = 24.dp),
        ) {
            Text(
                reason,
                style = RigCheckStyles.body,
                color = InkMuted,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.ACCOUNT_REASON),
            )

            RigCheckTextField(
                label = "Email",
                value = email,
                onValueChange = { email = it },
                keyboardType = KeyboardType.Email,
                inputModifier = Modifier.testTag(UiTags.ACCOUNT_EMAIL_FIELD),
            )
            RigCheckTextField(
                label = "Password",
                value = password,
                onValueChange = { password = it },
                keyboardType = KeyboardType.Password,
                visualTransformation = PasswordVisualTransformation(),
                help = if (creating) "At least $MIN_PASSWORD_LENGTH characters" else null,
                inputModifier = Modifier.testTag(UiTags.ACCOUNT_PASSWORD_FIELD),
            )

            // What went wrong is a line of words, not only the red: the same message the form always gave.
            error?.let {
                Text(
                    it,
                    style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Medium),
                    color = DangerText,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.ACCOUNT_ERROR),
                )
            }
            info?.let {
                RigCheckNoticeCard(
                    text = it,
                    tone = RigCheckNoticeTone.Scan,
                    icon = Icons.Outlined.Info,
                    modifier = Modifier.testTag(UiTags.ACCOUNT_INFO),
                )
            }

            RigCheckButton(
                text = if (creating) "Create account" else "Sign in",
                enabled = canSubmit,
                onClick = {
                    if (creating) perform(null) { cb -> onSignUp(email.trim(), password, cb) }
                    else perform(null) { cb -> onSignIn(email.trim(), password, cb) }
                },
                modifier = Modifier.testTag(UiTags.ACCOUNT_SUBMIT),
            )

            // One under the other, each as wide as its words (the frames), not side by side.
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                RigCheckButton(
                    text = if (creating) "Have an account? Sign in" else "New here? Create an account",
                    onClick = { creating = !creating; error = null; info = null },
                    kind = RigCheckButtonKind.Ghost,
                    size = RigCheckButtonSize.Compact,
                    enabled = !isBusy,
                    modifier = Modifier.testTag(UiTags.ACCOUNT_TOGGLE_MODE),
                )
                if (!creating) {
                    RigCheckButton(
                        text = "Forgot password?",
                        onClick = {
                            perform("If that email has an account, a reset link is on its way.") { cb ->
                                onForgotPassword(email.trim(), cb)
                            }
                        },
                        kind = RigCheckButtonKind.Ghost,
                        size = RigCheckButtonSize.Compact,
                        enabled = !isBusy && email.isNotBlank(),
                        modifier = Modifier.testTag(UiTags.ACCOUNT_FORGOT_PASSWORD),
                    )
                }
            }

            HorizontalDivider(color = Border, thickness = 1.dp, modifier = Modifier.testTag(UiTags.ACCOUNT_DIVIDER))

            RigCheckButton(
                text = "Continue with Google",
                enabled = !isBusy,
                onClick = { perform(null) { cb -> onGoogle(cb) } },
                kind = RigCheckButtonKind.Secondary,
                modifier = Modifier.testTag(UiTags.ACCOUNT_GOOGLE_BUTTON),
            )
            if (showApple) {
                RigCheckButton(
                    text = "Continue with Apple",
                    enabled = !isBusy,
                    onClick = { perform("Finish signing in with Apple in your browser.") { cb -> onApple(cb) } },
                    kind = RigCheckButtonKind.Secondary,
                    modifier = Modifier.testTag(UiTags.ACCOUNT_APPLE_BUTTON),
                )
            }

            // Trouble signing in is a thing a tester needs to report from here (#182).
            FeedbackLink(modifier = Modifier.fillMaxWidth(), linkModifier = Modifier.testTag(UiTags.ACCOUNT_FEEDBACK_LINK))
        }

        RigCheckFooter {
            RigCheckButton(
                text = "Not now",
                onClick = onNotNow,
                kind = RigCheckButtonKind.Ghost,
                modifier = Modifier.testTag(UiTags.ACCOUNT_NOT_NOW_BUTTON),
            )
        }
    }
}
