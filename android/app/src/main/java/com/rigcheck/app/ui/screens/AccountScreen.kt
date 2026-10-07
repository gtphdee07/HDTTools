package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.rigcheck.app.data.AccountResult

private const val MIN_PASSWORD_LENGTH = 6

// Sign in / create an account with email, Google or Apple. Shown only when
// something needs an account (buying or scanning) - the free manual-entry
// flow never reaches it. A successful sign-in isn't reported here: the
// caller's account state flips to signed-in and swaps this screen out.
@Composable
fun AccountScreen(
    reason: String,
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

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            if (creating) "Create your account" else "Sign in",
            style = MaterialTheme.typography.headlineMedium,
        )
        Text(reason, style = MaterialTheme.typography.bodyLarge)

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            supportingText = if (creating) {
                { Text("At least $MIN_PASSWORD_LENGTH characters") }
            } else {
                null
            },
            modifier = Modifier.fillMaxWidth(),
        )

        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        info?.let { Text(it, color = MaterialTheme.colorScheme.primary) }

        Button(
            enabled = canSubmit,
            onClick = {
                if (creating) perform(null) { cb -> onSignUp(email.trim(), password, cb) }
                else perform(null) { cb -> onSignIn(email.trim(), password, cb) }
            },
            modifier = Modifier.fillMaxWidth().testTag("account_submit"),
        ) {
            Text(if (creating) "Create account" else "Sign in")
        }

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TextButton(enabled = !isBusy, onClick = { creating = !creating; error = null; info = null }) {
                Text(if (creating) "Have an account? Sign in" else "New here? Create an account")
            }
            if (!creating) {
                TextButton(
                    enabled = !isBusy && email.isNotBlank(),
                    onClick = {
                        perform("If that email has an account, a reset link is on its way.") { cb ->
                            onForgotPassword(email.trim(), cb)
                        }
                    },
                ) { Text("Forgot password?") }
            }
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))

        OutlinedButton(
            enabled = !isBusy,
            onClick = { perform(null) { cb -> onGoogle(cb) } },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Continue with Google") }
        OutlinedButton(
            enabled = !isBusy,
            onClick = { perform("Finish signing in with Apple in your browser.") { cb -> onApple(cb) } },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Continue with Apple") }

        TextButton(onClick = onNotNow) { Text("Not now") }
    }
}
