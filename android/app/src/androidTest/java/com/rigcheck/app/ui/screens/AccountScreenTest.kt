package com.rigcheck.app.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.AccountResult
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// Drives the sign-in / create-account screen with fake callbacks standing in
// for the account manager - no Supabase, Google or Apple involved.
@RunWith(AndroidJUnit4::class)
class AccountScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private class Recorder {
        val calls = mutableListOf<String>()
        var nextResult: AccountResult = AccountResult.Success
        var held: ((AccountResult) -> Unit)? = null
        var hold = false

        fun respond(callback: (AccountResult) -> Unit) {
            if (hold) held = callback else callback(nextResult)
        }
    }

    private fun show(recorder: Recorder, onNotNow: () -> Unit = {}, showApple: Boolean = true) {
        composeRule.setContent {
            AccountScreen(
                reason = "Sign in to buy scans.",
                showApple = showApple,
                onSignIn = { email, password, cb -> recorder.calls += "signIn:$email:$password"; recorder.respond(cb) },
                onSignUp = { email, password, cb -> recorder.calls += "signUp:$email:$password"; recorder.respond(cb) },
                onGoogle = { cb -> recorder.calls += "google"; recorder.respond(cb) },
                onApple = { cb -> recorder.calls += "apple"; recorder.respond(cb) },
                onForgotPassword = { email, cb -> recorder.calls += "reset:$email"; recorder.respond(cb) },
                onNotNow = onNotNow,
            )
        }
    }

    private fun fillCredentials(email: String = "me@example.com", password: String = "hunter22") {
        composeRule.onNodeWithText("Email").performTextInput(email)
        composeRule.onNodeWithText("Password").performTextInput(password)
    }

    @Test
    fun showsTheReasonAndAllThreeSignInMethods() {
        show(Recorder())

        composeRule.onNodeWithText("Sign in to buy scans.").assertIsDisplayed()
        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()
        composeRule.onNodeWithText("Continue with Apple").assertIsDisplayed()
        composeRule.onNodeWithText("Email").assertIsDisplayed()
    }

    @Test
    fun signInStaysDisabledUntilThereIsAnEmailAndAPassword() {
        show(Recorder())

        composeRule.onNodeWithTag("account_submit").assertIsNotEnabled()
        composeRule.onNodeWithText("Email").performTextInput("me@example.com")
        composeRule.onNodeWithTag("account_submit").assertIsNotEnabled()
        composeRule.onNodeWithText("Password").performTextInput("abc")
        // Too short a password still blocks submission.
        composeRule.onNodeWithTag("account_submit").assertIsNotEnabled()
        composeRule.onNodeWithText("Password").performTextInput("def")
        composeRule.onNodeWithTag("account_submit").assertIsEnabled()
    }

    @Test
    fun signInSendsTheTrimmedEmailAndPassword() {
        val recorder = Recorder()
        show(recorder)

        fillCredentials(email = " me@example.com ")
        composeRule.onNodeWithTag("account_submit").performClick()

        assert(recorder.calls == listOf("signIn:me@example.com:hunter22")) { recorder.calls.toString() }
    }

    @Test
    fun createAccountModeSendsASignUpInstead() {
        val recorder = Recorder()
        show(recorder)

        composeRule.onNodeWithText("New here? Create an account").performClick()
        composeRule.onNodeWithText("Create your account").assertIsDisplayed()
        fillCredentials()
        composeRule.onNodeWithTag("account_submit").performClick()

        assert(recorder.calls == listOf("signUp:me@example.com:hunter22")) { recorder.calls.toString() }
    }

    @Test
    fun aFailedSignInShowsTheReasonAndStaysUsable() {
        val recorder = Recorder().apply { nextResult = AccountResult.Failure("Invalid login credentials") }
        show(recorder)

        fillCredentials()
        composeRule.onNodeWithTag("account_submit").performClick()

        composeRule.onNodeWithText("Invalid login credentials").assertIsDisplayed()
        composeRule.onNodeWithText("Continue with Google").assertIsEnabled()
    }

    @Test
    fun aSignUpThatNeedsConfirmationTellsTheUserToCheckEmail() {
        val recorder = Recorder().apply { nextResult = AccountResult.NeedsConfirmation }
        show(recorder)

        composeRule.onNodeWithText("New here? Create an account").performClick()
        fillCredentials()
        composeRule.onNodeWithTag("account_submit").performClick()

        composeRule.onNodeWithText("Check your email to confirm your account, then sign in.").assertIsDisplayed()
    }

    @Test
    fun googleAndAppleButtonsInvokeTheirCallbacks() {
        val recorder = Recorder()
        show(recorder)

        composeRule.onNodeWithText("Continue with Google").performClick()
        composeRule.onNodeWithText("Continue with Apple").performClick()

        assert(recorder.calls == listOf("google", "apple")) { recorder.calls.toString() }
    }

    // Apple is deferred to #77 (needs the iOS app and an Apple Developer
    // account), so the app hides the button rather than ship a dead one.
    @Test
    fun hidesTheAppleButtonWhenAppleIsNotEnabled() {
        show(Recorder(), showApple = false)

        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()
        composeRule.onNodeWithText("Continue with Apple").assertDoesNotExist()
    }

    @Test
    fun appleExplainsThatSigningInContinuesInTheBrowser() {
        show(Recorder())

        composeRule.onNodeWithText("Continue with Apple").performClick()

        composeRule.onNodeWithText("Finish signing in with Apple in your browser.").assertIsDisplayed()
    }

    @Test
    fun aCancelledProviderChooserShowsNoMessage() {
        val recorder = Recorder().apply { nextResult = AccountResult.Cancelled }
        show(recorder)

        composeRule.onNodeWithText("Continue with Google").performClick()

        composeRule.onNodeWithText("Continue with Google").assertIsEnabled()
    }

    @Test
    fun theFormIsDisabledWhileASignInIsInFlight() {
        val recorder = Recorder().apply { hold = true }
        show(recorder)

        composeRule.onNodeWithText("Continue with Google").performClick()

        composeRule.onNodeWithText("Continue with Google").assertIsNotEnabled()
        composeRule.onNodeWithText("Continue with Apple").assertIsNotEnabled()

        composeRule.runOnUiThread { recorder.held?.invoke(AccountResult.Cancelled) }
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Continue with Google").assertIsEnabled()
    }

    @Test
    fun forgotPasswordAsksForTheEmailFirstThenSendsAReset() {
        val recorder = Recorder()
        show(recorder)

        composeRule.onNodeWithText("Forgot password?").assertIsNotEnabled()
        composeRule.onNodeWithText("Email").performTextInput("me@example.com")
        composeRule.onNodeWithText("Forgot password?").performClick()

        assert(recorder.calls == listOf("reset:me@example.com")) { recorder.calls.toString() }
        composeRule.onNodeWithText("If that email has an account, a reset link is on its way.").assertIsDisplayed()
    }

    @Test
    fun notNowLeavesTheScreen() {
        var left = false
        show(Recorder(), onNotNow = { left = true })

        composeRule.onNodeWithText("Not now").performClick()

        assert(left) { "onNotNow should have fired" }
    }
}
