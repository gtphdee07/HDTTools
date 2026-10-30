package com.rigcheck.app.ui.screens

import android.content.ActivityNotFoundException
import android.content.ContextWrapper
import android.content.Intent
import android.os.Bundle
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.layoutcapture.CaptureScope
import com.rigcheck.app.layoutcapture.DisplayFrame
import com.rigcheck.app.layoutcapture.Frame
import com.rigcheck.app.layoutcapture.TaggedBounds
import com.rigcheck.app.testsupport.Dim
import com.rigcheck.app.testsupport.LayoutStateRunner
import com.rigcheck.app.testsupport.Probe
import com.rigcheck.app.testsupport.Size
import com.rigcheck.app.testsupport.about
import com.rigcheck.app.testsupport.absent
import com.rigcheck.app.testsupport.fakePackage
import com.rigcheck.app.testsupport.fixed
import com.rigcheck.app.testsupport.hasTagShowing
import com.rigcheck.app.testsupport.noneWiderThanTheScreen
import com.rigcheck.app.testsupport.nodesWithTagShowing
import com.rigcheck.app.testsupport.order
import com.rigcheck.app.testsupport.reach
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.testsupport.shown
import com.rigcheck.app.testsupport.sizes
import com.rigcheck.app.testsupport.square
import com.rigcheck.app.testsupport.touchTargets
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.LateScanDialog
import com.rigcheck.app.ui.components.ScanErrorDialog
import kotlin.math.abs
import kotlinx.coroutines.awaitCancellation
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #196: the Paywall, the Account screen and the two Scan dialogs, checked against the designer's map
// (docs/android-redesign/design-return/ui-redesign-map.json and its follow-up). For every element of the four, in the
// states below (the frames of annotation-legends.json: paywall free_pro_offer, free_busy, free_no_pro, pro_packs,
// pro_no_packs, pro_bought_waiting, loading, load_error and plan_unknown; account sign_in, create_account, error,
// info_reset_sent, busy, keyboard_open, feedback_no_mail and apple_enabled_future; scan_error_dialog message_only,
// one_next_step, two_next_steps and long_message; late_scan_dialog credit_used):
//   - it is displayed (found by its UiTags tag, scrolled into view if it is in the scrolling body, and then wholly on
//     the screen);
//   - the reading order is the frame's: the bands, one per row or block, come one after the other by their tops (see
//     `order` in testsupport/LayoutChecks.kt), and what is stacked inside a card or a dialog is in order by its top;
//   - its measured width and height are the map's `new_width` and `new_height`. TOLERANCE: 1.5 dp where the map gives a
//     fixed size, 2 dp on a single line of text, 3 dp on a single line of 15/22 copy (Compose trims 2.4 dp of the line's
//     extra space, so the box is 19.6 where the frame's line is 22), 4 dp on the notices', the title's, the offer card's
//     and the toast's ~values, and 12 dp on copy of three or four lines (the explainer, the reason), whose wrap can differ
//     a line's worth in the bundled font from the browser the frames were drawn in; "fill" is the screen less the 16 dp margins
//     of the page (or less what the card or the dialog holds around it), "wrap" has no width to check. A repeated
//     element (the offer card and its parts) is measured on its first instance;
//   - every clickable element is at least 48 x 48 dp.
// And on a 360 x 640 dp phone, at font scale 2.0, with the keyboard open on the Account screen, the primary action
// of each screen (Restore purchase and the offers, Not now and the form, the dialogs' OK) is on show or scrolled to,
// nothing is wider than the screen, and Restore purchase and Not now are pinned: they do not move when the body scrolls.
//
// It changes the display's size, density and font scale for the run and puts them back (as LayoutCaptureTest does),
// and sends no Scan and calls no store: RevenueCat is faked as the Offering's packages.
@RunWith(AndroidJUnit4::class)
class PaywallAccountLayoutTest {

    @get:Rule
    val composeRule = createEmptyComposeRule()

    private val display = DisplayFrame(InstrumentationRegistry.getInstrumentation())
    private val runner = LayoutStateRunner(composeRule, screenshotFolder = "ticket-196-screenshots")

    private fun putOnTheDisplay(frame: Frame) {
        runner.frameName = frame.name
        display.apply(frame)
    }

    @After
    fun putTheDisplayBack() {
        display.reset()
    }

    private fun inState(
        name: String,
        content: @Composable () -> Unit,
        setUp: CaptureScope.() -> Unit = {},
        check: (Probe) -> List<String>,
    ): List<String> = runner.inState(name, content, setUp = setUp, check = check)

    // --- 412 x 892: the Paywall ----------------------------------------------------------------------------

    @Test
    fun thePaywallFrames412x892MatchTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()
        var betaAccountLabelTop = 0.0

        // paywall__free_pro_offer: one large Pro card, as a beta build shows it (the beta notice at the top).
        problems += inState("paywall: free_pro_offer", paywall(isPro = false) { listOf(proOffer) }) { p ->
            val b = p.bounds()
            betaAccountLabelTop = b[UiTags.PAYWALL_ACCOUNT_LABEL]?.y ?: 0.0
            sizes(b, p.widthDp, paywallSizes.only(chrome + freeParts)) +
                absent(b, listOf(UiTags.PAYWALL_TOAST, UiTags.PAYWALL_NO_PRO, UiTags.PAYWALL_LOADING)) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_OFFER_CARD), restore), freeStacks) +
                reach(p, *(chrome + freeParts).toTypedArray()) + pinnedFooter(p) + touchTargets(p)
        }
        // A production build leaves the beta notice out and everything below it moves up by 80 dp.
        problems += inState("paywall: free_pro_offer production", paywall(isPro = false, isBeta = false) { listOf(proOffer) }) { p ->
            val b = p.bounds()
            val top = b[UiTags.PAYWALL_ACCOUNT_LABEL]?.y ?: 0.0
            absent(b, listOf(UiTags.PAYWALL_BETA_LABEL)) +
                listOfNotNull(
                    "the account line moves up ${betaAccountLabelTop - top} dp without the beta notice, not 80"
                        .takeIf { abs(betaAccountLabelTop - top - 80.0) > 2.0 },
                )
        }
        // paywall__free_busy: a purchase is out, so the buy button, Sign out, Restore purchase and Back are off.
        problems += inState(
            "paywall: free_busy", paywall(isPro = false, onPurchase = { _, _ -> }) { listOf(proOffer) },
            setUp = { tap(UiTags.PAYWALL_BUY_BUTTON) },
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, paywallSizes.only(chrome + freeParts)) +
                enabled(p, false, UiTags.PAYWALL_BUY_BUTTON, UiTags.PAYWALL_RESTORE_BUTTON, UiTags.PAYWALL_BACK, UiTags.PAYWALL_SIGN_OUT_BUTTON) +
                reach(p, *(chrome + freeParts).toTypedArray()) + pinnedFooter(p)
        }
        // paywall__free_no_pro: the store has no Pro package to sell.
        problems += inState("paywall: free_no_pro", paywall(isPro = false) { listOf(smallPack) }) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, paywallSizes.only(chrome + UiTags.PAYWALL_NO_PRO)) +
                absent(b, listOf(UiTags.PAYWALL_OFFER_CARD, UiTags.PAYWALL_BUY_BUTTON)) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_NO_PRO), restore)) +
                reach(p, *(chrome + UiTags.PAYWALL_NO_PRO).toTypedArray()) + pinnedFooter(p)
        }
        // paywall__pro_packs: one white row per pack with the store's own price (short and long), and the Snackbar a
        // restore raises above Restore purchase.
        problems += inState(
            "paywall: pro_packs", paywall(isPro = true, balance = 12, onRestore = { report -> report(true, null) }) { packs },
            setUp = { tap(UiTags.PAYWALL_RESTORE_BUTTON) },
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, (paywallSizes + proSizes).only(chrome + packParts + UiTags.PAYWALL_TOAST)) +
                absent(b, listOf(UiTags.PAYWALL_NO_PACKS, UiTags.PAYWALL_LOADING)) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_OFFER_CARD), listOf(UiTags.PAYWALL_TOAST), restore), packStacks) +
                toastClearsRestore(b) + everyPriceIsOneLine(p) +
                reach(p, *(chrome + packParts).toTypedArray()) + pinnedFooter(p) + touchTargets(p)
        }
        // paywall__pro_no_packs: a Pro account with nothing to buy.
        problems += inState("paywall: pro_no_packs", paywall(isPro = true, balance = 12) { emptyList() }) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, (paywallSizes + proSizes).only(chrome + UiTags.PAYWALL_NO_PACKS)) +
                absent(b, listOf(UiTags.PAYWALL_OFFER_CARD)) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_NO_PACKS), restore)) +
                reach(p, *(chrome + UiTags.PAYWALL_NO_PACKS).toTypedArray()) + pinnedFooter(p)
        }
        // paywall__pro_bought_waiting: Pro was bought here and the plan has not caught up. (The frame draws the Pro
        // card away and the plan as Pro; the app keeps the card, off, as the code and its test do: nothing may buy Pro twice.)
        problems += inState(
            "paywall: pro_bought_waiting", paywall(isPro = false, onPurchase = { _, report -> report(true, null) }) { listOf(proOffer) },
            setUp = { tap(UiTags.PAYWALL_BUY_BUTTON) },
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, paywallSizes.only(chrome + UiTags.PAYWALL_PRO_BOUGHT + UiTags.PAYWALL_RETRY_BUTTON)) +
                enabled(p, false, UiTags.PAYWALL_BUY_BUTTON) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_OFFER_CARD), listOf(UiTags.PAYWALL_PRO_BOUGHT), listOf(UiTags.PAYWALL_RETRY_BUTTON), restore)) +
                reach(p, *(chrome + UiTags.PAYWALL_PRO_BOUGHT + UiTags.PAYWALL_RETRY_BUTTON).toTypedArray()) + pinnedFooter(p)
        }
        // paywall__loading: the offers are on their way.
        problems += inState("paywall: loading", paywall(isPro = false) { awaitCancellation() }) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, paywallSizes.only(chrome + UiTags.PAYWALL_LOADING)) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_LOADING), restore)) +
                reach(p, *(chrome + UiTags.PAYWALL_LOADING).toTypedArray()) + pinnedFooter(p)
        }
        // paywall__load_error: the offers could not be read.
        problems += inState("paywall: load_error", paywall(isPro = false) { error("Network request failed") }) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, paywallSizes.only(chrome + UiTags.PAYWALL_LOAD_ERROR)) +
                order(b, chromeBands + listOf(listOf(UiTags.PAYWALL_LOAD_ERROR), restore)) +
                reach(p, *(chrome + UiTags.PAYWALL_LOAD_ERROR).toTypedArray()) + pinnedFooter(p)
        }
        // paywall__plan_unknown: the plan could not be read, so no plan label and nothing to buy. (The frame draws the
        // Free account's explainer; the app's own, with the plan not known, is the words without the plan's sentence,
        // so the explainer's height is not compared.)
        problems += inState("paywall: plan_unknown", paywall(isPro = null) { listOf(proOffer, smallPack) }) { p ->
            val b = p.bounds()
            val parts = chrome - UiTags.PAYWALL_PLAN_LABEL - UiTags.PAYWALL_EXPLAINER
            sizes(b, p.widthDp, paywallSizes.only(parts + UiTags.PAYWALL_PLAN_UNKNOWN + UiTags.PAYWALL_RETRY_BUTTON)) +
                absent(b, listOf(UiTags.PAYWALL_PLAN_LABEL, UiTags.PAYWALL_OFFER_CARD)) +
                order(b, chromeBands.take(3) + listOf(listOf(UiTags.PAYWALL_EXPLAINER), listOf(UiTags.PAYWALL_PLAN_UNKNOWN), listOf(UiTags.PAYWALL_RETRY_BUTTON), restore)) +
                reach(p, *(parts + UiTags.PAYWALL_EXPLAINER + UiTags.PAYWALL_PLAN_UNKNOWN + UiTags.PAYWALL_RETRY_BUTTON).toTypedArray()) +
                pinnedFooter(p)
        }

        assertTrue("the Paywall frames differ from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- 412 x 892: the Account screen -----------------------------------------------------------------------

    @Test
    fun theAccountFrames412x892MatchTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()
        val formBands = listOf(
            accountHeader, listOf(UiTags.ACCOUNT_REASON), listOf(UiTags.ACCOUNT_EMAIL_FIELD), listOf(UiTags.ACCOUNT_PASSWORD_FIELD),
        )

        // account__sign_in
        problems += inState("account: sign_in", account()) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, accountSizes.only(signInTags)) +
                absent(b, listOf(UiTags.ACCOUNT_ERROR, UiTags.ACCOUNT_INFO, UiTags.ACCOUNT_APPLE_BUTTON)) +
                order(b, formBands + signInRest.map { listOf(it) }) +
                reach(p, *signInTags.toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON) + touchTargets(p)
        }
        // account__create_account: the title and the button say so, the forgot-password link is not offered, and the
        // password field tells how long it has to be.
        problems += inState("account: create_account", account(), setUp = { tap(UiTags.ACCOUNT_TOGGLE_MODE) }) { p ->
            val b = p.bounds()
            val tags = signInTags - UiTags.ACCOUNT_FORGOT_PASSWORD
            sizes(b, p.widthDp, accountSizes.only(tags)) +
                absent(b, listOf(UiTags.ACCOUNT_FORGOT_PASSWORD)) +
                order(b, formBands + createRest.map { listOf(it) }) +
                says(p, UiTags.ACCOUNT_TITLE to "Create your account", UiTags.ACCOUNT_SUBMIT to "Create account") +
                helpUnderThePassword(p, "At least 6 characters") +
                reach(p, *tags.toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON) + touchTargets(p)
        }
        // account__error: a sign-in the server refused, in words under the password field.
        problems += inState(
            "account: error", account(),
            setUp = {
                type(UiTags.ACCOUNT_EMAIL_FIELD, "alice@example.com")
                type(UiTags.ACCOUNT_PASSWORD_FIELD, "a-long-password")
                hideKeyboard()
                tap(UiTags.ACCOUNT_SUBMIT)
            },
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, accountSizes.only(signInTags + UiTags.ACCOUNT_ERROR)) +
                order(b, formBands + listOf(listOf(UiTags.ACCOUNT_ERROR), listOf(UiTags.ACCOUNT_SUBMIT), listOf(UiTags.ACCOUNT_TOGGLE_MODE))) +
                says(p, UiTags.ACCOUNT_ERROR to "Invalid login credentials") +
                reach(p, *(signInTags + UiTags.ACCOUNT_ERROR).toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON)
        }
        // account__info_reset_sent: the answer to Forgot password, in the notice.
        problems += inState(
            "account: info_reset_sent", account(),
            setUp = {
                type(UiTags.ACCOUNT_EMAIL_FIELD, "alice@example.com")
                hideKeyboard()
                tap(UiTags.ACCOUNT_FORGOT_PASSWORD)
            },
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, accountSizes.only(signInTags + UiTags.ACCOUNT_INFO)) +
                order(b, formBands + listOf(listOf(UiTags.ACCOUNT_INFO), listOf(UiTags.ACCOUNT_SUBMIT), listOf(UiTags.ACCOUNT_TOGGLE_MODE))) +
                says(p, UiTags.ACCOUNT_INFO to "If that email has an account, a reset link is on its way.") +
                reach(p, *(signInTags + UiTags.ACCOUNT_INFO).toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON)
        }
        // account__busy: a Google sign-in is out; every control of the form is off, Send feedback and Not now are not.
        problems += inState(
            "account: busy", account(onGoogle = { }),
            setUp = { tap(UiTags.ACCOUNT_GOOGLE_BUTTON) },
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, accountSizes.only(signInTags)) +
                enabled(p, false, UiTags.ACCOUNT_SUBMIT, UiTags.ACCOUNT_TOGGLE_MODE, UiTags.ACCOUNT_FORGOT_PASSWORD, UiTags.ACCOUNT_GOOGLE_BUTTON) +
                enabled(p, true, UiTags.ACCOUNT_FEEDBACK_LINK, UiTags.ACCOUNT_NOT_NOW_BUTTON, UiTags.ACCOUNT_BACK) +
                reach(p, *signInTags.toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON)
        }
        // account__keyboard_open: the footer stays above the keyboard.
        problems += inState(
            "account: keyboard_open", account(),
            setUp = {
                tap(UiTags.ACCOUNT_EMAIL_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.ACCOUNT_BACK, UiTags.ACCOUNT_TITLE)) +
                reach(p, UiTags.ACCOUNT_EMAIL_FIELD, UiTags.ACCOUNT_PASSWORD_FIELD, UiTags.ACCOUNT_SUBMIT, UiTags.ACCOUNT_NOT_NOW_BUTTON)
        }
        // account__feedback_no_mail: Send feedback on a phone with no email app says so under the link.
        problems += inState(
            "account: feedback_no_mail", withNoMailApp(account()),
            setUp = { tap(UiTags.ACCOUNT_FEEDBACK_LINK) },
        ) { p ->
            val b = p.bounds()
            shown(b, listOf(UiTags.SEND_FEEDBACK_NO_MAIL_APP)) +
                order(b, listOf(listOf(UiTags.ACCOUNT_GOOGLE_BUTTON), listOf(UiTags.ACCOUNT_FEEDBACK_LINK), listOf(UiTags.SEND_FEEDBACK_NO_MAIL_APP))) +
                reach(p, UiTags.ACCOUNT_FEEDBACK_LINK, UiTags.SEND_FEEDBACK_NO_MAIL_APP) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON)
        }
        // account__apple_enabled_future: the Apple button, in the Google button's style, under it.
        problems += inState("account: apple_enabled_future", account(showApple = true)) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, accountSizes.only(signInTags + UiTags.ACCOUNT_APPLE_BUTTON)) +
                order(
                    b,
                    formBands + (signInRest - UiTags.ACCOUNT_FEEDBACK_LINK - UiTags.ACCOUNT_NOT_NOW_BUTTON + UiTags.ACCOUNT_APPLE_BUTTON)
                        .map { listOf(it) } + listOf(listOf(UiTags.ACCOUNT_FEEDBACK_LINK), listOf(UiTags.ACCOUNT_NOT_NOW_BUTTON)),
                ) +
                reach(p, *(signInTags + UiTags.ACCOUNT_APPLE_BUTTON).toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON)
        }

        assertTrue("the Account frames differ from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- 412 x 892: the dialogs -------------------------------------------------------------------------------

    @Test
    fun theDialogFrames412x892MatchTheMap() {
        putOnTheDisplay(Frame(412, 892))
        val problems = mutableListOf<String>()
        val dialogParts = listOf(UiTags.SCAN_ERROR_TITLE, UiTags.SCAN_ERROR_MESSAGE)

        // scan_error_dialog__message_only: no way forward, so OK alone, as a ghost button.
        problems += inState("scan_error_dialog: message_only", scanError(messageOnly, emptyList())) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, dialogSizes.only(dialogParts + UiTags.SCAN_ERROR_OK_BUTTON)) +
                absent(b, listOf(UiTags.SCAN_ERROR_NEXT_STEP_BUTTON)) +
                order(b, listOf(listOf(UiTags.SCAN_ERROR_TITLE), listOf(UiTags.SCAN_ERROR_MESSAGE), listOf(UiTags.SCAN_ERROR_OK_BUTTON))) +
                wholeLines(b, UiTags.SCAN_ERROR_MESSAGE, 24.0, max = 4) +
                reach(p, *(dialogParts + UiTags.SCAN_ERROR_OK_BUTTON).toTypedArray()) + touchTargets(p)
        }
        // __one_next_step: the step first (primary), OK last.
        problems += inState("scan_error_dialog: one_next_step", scanError(oneStepMessage, listOf(ScanNextStep.TRY_AGAIN))) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, dialogSizes.only(dialogParts + UiTags.SCAN_ERROR_NEXT_STEP_BUTTON + UiTags.SCAN_ERROR_NEXT_TRY_AGAIN + UiTags.SCAN_ERROR_OK_BUTTON)) +
                order(b, dialogBands(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN)) +
                steps(p, 1) + reach(p, *(dialogParts + UiTags.SCAN_ERROR_NEXT_TRY_AGAIN + UiTags.SCAN_ERROR_OK_BUTTON).toTypedArray()) + touchTargets(p)
        }
        // __two_next_steps: the first primary, the second secondary, OK last, each 52 dp and in the order the failure gave.
        problems += inState(
            "scan_error_dialog: two_next_steps",
            scanError(oneStepMessage, listOf(ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO)),
        ) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, dialogSizes.only(dialogParts + UiTags.SCAN_ERROR_NEXT_STEP_BUTTON + UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN + UiTags.SCAN_ERROR_OK_BUTTON)) +
                order(b, dialogBands(UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN, UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO)) +
                steps(p, 2) + reach(p, *(dialogParts + UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN + UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO + UiTags.SCAN_ERROR_OK_BUTTON).toTypedArray()) +
                touchTargets(p)
        }
        // __long_message: the message grows and nothing else changes.
        problems += inState("scan_error_dialog: long_message", scanError(longMessage, listOf(ScanNextStep.TRY_AGAIN))) { p ->
            val b = p.bounds()
            order(b, dialogBands(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN)) +
                wholeLines(b, UiTags.SCAN_ERROR_MESSAGE, 24.0) +
                reach(p, *(dialogParts + UiTags.SCAN_ERROR_NEXT_TRY_AGAIN + UiTags.SCAN_ERROR_OK_BUTTON).toTypedArray()) + noneWiderThanTheScreen(p)
        }
        // late_scan_dialog__credit_used: the same dialog with OK alone.
        val lateParts = listOf(UiTags.LATE_SCAN_TITLE, UiTags.LATE_SCAN_MESSAGE, UiTags.LATE_SCAN_OK_BUTTON)
        problems += inState("late_scan_dialog: credit_used", { LateScanDialog(message = ScanMessages.RESULT_NOT_USED, onDismiss = {}) }) { p ->
            val b = p.bounds()
            sizes(b, p.widthDp, dialogSizes.only(lateParts)) +
                order(b, lateParts.map { listOf(it) }) +
                wholeLines(b, UiTags.LATE_SCAN_MESSAGE, 24.0, max = 3) +
                reach(p, *lateParts.toTypedArray()) + touchTargets(p)
        }

        assertTrue("the dialog frames differ from the map:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- A small phone and a large font ----------------------------------------------------------------------

    @Test
    fun aSmallPhone360x640ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640))

    @Test
    fun aSmallPhone360x640AtFontScale2ReachesEveryPrimaryAction() = reachEverything(Frame(360, 640, fontScale = 2f))

    private fun reachEverything(frame: Frame) {
        putOnTheDisplay(frame)
        val problems = mutableListOf<String>()

        problems += inState("paywall: free ${frame.name}", paywall(isPro = false) { listOf(proOffer) }) { p ->
            reach(p, *(chrome + freeParts).toTypedArray()) + pinnedFooter(p) + noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState("paywall: packs ${frame.name}", paywall(isPro = true, balance = 12) { packs }) { p ->
            reach(p, *(chrome + packParts).toTypedArray()) + lastPackReached(p) + pinnedFooter(p) + noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState("paywall: loading ${frame.name}", paywall(isPro = false) { awaitCancellation() }) { p ->
            reach(p, *(chrome + UiTags.PAYWALL_LOADING).toTypedArray()) + pinnedFooter(p) + noneWiderThanTheScreen(p)
        }
        problems += inState("account: sign_in ${frame.name}", account(showApple = true)) { p ->
            reach(p, *(signInTags + UiTags.ACCOUNT_APPLE_BUTTON).toTypedArray()) + pinnedFooter(p, UiTags.ACCOUNT_NOT_NOW_BUTTON) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        // With the keyboard open on a short phone the fields, the button and the footer are all above it.
        problems += inState(
            "account: keyboard open ${frame.name}", account(),
            setUp = {
                tap(UiTags.ACCOUNT_PASSWORD_FIELD)
                awaitKeyboardShown()
            },
        ) { p ->
            reach(p, UiTags.ACCOUNT_EMAIL_FIELD, UiTags.ACCOUNT_PASSWORD_FIELD, UiTags.ACCOUNT_SUBMIT, UiTags.ACCOUNT_NOT_NOW_BUTTON) +
                noneWiderThanTheScreen(p)
        }
        // The dialogs scroll when their buttons do not fit: the five next steps and OK are all reachable.
        problems += inState("scan_error_dialog: five_next_steps ${frame.name}", scanError(longMessage, ScanNextStep.entries)) { p ->
            reach(p, UiTags.SCAN_ERROR_TITLE, UiTags.SCAN_ERROR_NEXT_SIGN_IN, UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN, UiTags.SCAN_ERROR_OK_BUTTON) +
                noneWiderThanTheScreen(p) + touchTargets(p)
        }
        problems += inState("late_scan_dialog: ${frame.name}", { LateScanDialog(message = ScanMessages.RESULT_NOT_USED, onDismiss = {}) }) { p ->
            reach(p, UiTags.LATE_SCAN_TITLE, UiTags.LATE_SCAN_OK_BUTTON) + noneWiderThanTheScreen(p) + touchTargets(p)
        }

        assertTrue("${frame.name}:\n" + problems.joinToString("\n"), problems.isEmpty())
    }

    // --- Checks of these screens -----------------------------------------------------------------------------

    private fun Map<String, Size>.only(tags: List<String>): Map<String, Size> = filterKeys { it in tags }

    // The controls' enabled state: off while a purchase or a sign-in is out, on for what must stay usable.
    private fun enabled(p: Probe, expected: Boolean, vararg tags: String): List<String> = tags.mapNotNull { tag ->
        val node = p.rule.onAllNodesWithTag(tag).fetchSemanticsNodes().firstOrNull() ?: return@mapNotNull "$tag is not on the screen"
        val off = SemanticsProperties.Disabled in node.config
        "$tag is ${if (off) "off" else "on"}, not ${if (expected) "on" else "off"}".takeIf { off == expected }
    }

    // Restore purchase and Not now sit in the footer: they do not move when the body is scrolled to its end, and they
    // are under it, wholly on the screen.
    private fun pinnedFooter(p: Probe, tag: String = UiTags.PAYWALL_RESTORE_BUTTON): List<String> {
        val before = p.bounds()[tag] ?: return listOf("$tag is not on the screen")
        lastInBody(p)?.let { reach(p, it) }
        val after = p.bounds()[tag] ?: return listOf("$tag is not on the screen after the body scrolled")
        return listOfNotNull(
            "$tag moved from ${before.y} to ${after.y} dp when the body scrolled".takeIf { abs(before.y - after.y) > 0.5 },
            "$tag is not under the body: it ends at ${after.y + after.height} dp of ${p.heightDp}"
                .takeIf { after.y + after.height > p.heightDp + 0.5 },
        )
    }

    // The last thing the body holds on the screen the probe is on, to scroll to.
    private fun lastInBody(p: Probe): String? {
        val onScreen = p.bounds()
        return listOf(
            UiTags.PAYWALL_OFFER_CARD, UiTags.PAYWALL_NO_PACKS, UiTags.PAYWALL_NO_PRO, UiTags.PAYWALL_LOAD_ERROR, UiTags.PAYWALL_RETRY_BUTTON,
            UiTags.PAYWALL_LOADING, UiTags.ACCOUNT_FEEDBACK_LINK,
        ).lastOrNull { it in onScreen }
    }

    // Three packs: the last one's price button ("CA$12.99 one time") is reached by a scroll.
    private fun lastPackReached(p: Probe): List<String> {
        val last = p.rule.onAllNodes(hasTagShowing(UiTags.PAYWALL_BUY_BUTTON, "one time", substring = true), useUnmergedTree = true)
        if (last.fetchSemanticsNodes().isEmpty()) return listOf("the last pack's price is not on the screen")
        last.onFirst().scrollToIfScrollable().assertIsDisplayed()
        return emptyList()
    }

    // The Snackbar is above the pinned Restore purchase and clear of it, and 16 dp in from each side.
    private fun toastClearsRestore(b: Map<String, TaggedBounds>): List<String> {
        val toast = b[UiTags.PAYWALL_TOAST] ?: return listOf("${UiTags.PAYWALL_TOAST} is not on the screen")
        val restore = b[UiTags.PAYWALL_RESTORE_BUTTON] ?: return listOf("${UiTags.PAYWALL_RESTORE_BUTTON} is not on the screen")
        return listOfNotNull(
            "the Snackbar ends at ${toast.y + toast.height} dp, over Restore purchase that starts at ${restore.y} dp"
                .takeIf { toast.y + toast.height > restore.y + 0.5 },
            "the Snackbar starts ${toast.x} dp from the left, not 16".takeIf { abs(toast.x - 16.0) > 1.5 },
        )
    }

    // The store's price text is the button's words and the button grows to hold it: every price button is one line
    // (48 dp) tall, "CA$12.99 one time" among them, so no price wraps or is cut off.
    private fun everyPriceIsOneLine(p: Probe): List<String> {
        val prices = p.rule.onAllNodesWithTag(UiTags.PAYWALL_BUY_BUTTON, useUnmergedTree = true).fetchSemanticsNodes()
        val long = p.rule.nodesWithTagShowing(UiTags.PAYWALL_BUY_BUTTON, "one time", substring = true)
        return listOfNotNull("the \"one time\" price is not on the screen".takeIf { long == 0 }) + prices.mapNotNull { node ->
            val height = node.size.height / Frame.PX_PER_DP
            "a price button is $height dp tall, not 48".takeIf { abs(height - 48.0) > 1.5 }
        }
    }

    // The element with the tag says the words (found by tag, as the rest of the suite does; a re-skin may move the words
    // to another element, but not away from the one the tag is on).
    private fun says(p: Probe, vararg words: Pair<String, String>): List<String> = words.mapNotNull { (tag, text) ->
        "$tag does not say \"$text\"".takeIf { p.rule.nodesWithTagShowing(tag, text) == 0 }
    }

    // The password field's help line is not an inventory element, so it has no tag of its own: it is found by its words.
    private fun helpUnderThePassword(p: Probe, text: String): List<String> =
        listOfNotNull(
            "the password field's help \"$text\" is not on the screen".takeIf {
                p.rule.onAllNodes(hasText(text), useUnmergedTree = true).fetchSemanticsNodes().isEmpty()
            },
        )

    // A text in lines of `lineDp` each (the 16/24 of the dialog's body): its height is a whole number of lines to within
    // 4 dp (Compose trims the extra space of the first and last line, 3.2 dp in all, so the box is a little under the
    // lines') and, when the frame has a number of them, no more than one over it (a line's wrap can differ in the font).
    private fun wholeLines(b: Map<String, TaggedBounds>, tag: String, lineDp: Double, max: Int? = null): List<String> {
        val found = b[tag] ?: return listOf("$tag is not on the screen")
        val lines = Math.round(found.height / lineDp)
        return listOfNotNull(
            "$tag is ${found.height} dp tall, not $lines lines of $lineDp dp".takeIf { abs(found.height - lines * lineDp) > 4.0 },
            "$tag is $lines lines, more than the frame's $max".takeIf { max != null && lines > max + 1 },
        )
    }

    // The dialog's bands, top to bottom: the title, the message, the next steps in their order, OK.
    private fun dialogBands(vararg steps: String): List<List<String>> =
        listOf(listOf(UiTags.SCAN_ERROR_TITLE), listOf(UiTags.SCAN_ERROR_MESSAGE)) + steps.map { listOf(it) } +
            listOf(listOf(UiTags.SCAN_ERROR_OK_BUTTON))

    // One wrapper (`scan_error_next_step_button`) per next step.
    private fun steps(p: Probe, expected: Int): List<String> {
        val found = p.rule.onAllNodesWithTag(UiTags.SCAN_ERROR_NEXT_STEP_BUTTON, useUnmergedTree = true).fetchSemanticsNodes().size
        return listOfNotNull("$found next-step buttons are on the screen, not $expected".takeIf { found != expected })
    }

    // --- What the map says ---------------------------------------------------------------------------------

    private val restore = listOf(UiTags.PAYWALL_RESTORE_BUTTON)

    // The top bar's row (Back, the title), then the beta notice, the account line (the label and Sign out), the plan and
    // the explainer: the bands every state of the Paywall that has an account starts with.
    private val chrome = listOf(
        UiTags.PAYWALL_BACK, UiTags.PAYWALL_TITLE, UiTags.PAYWALL_BETA_LABEL, UiTags.PAYWALL_ACCOUNT_LABEL,
        UiTags.PAYWALL_SIGN_OUT_BUTTON, UiTags.PAYWALL_PLAN_LABEL, UiTags.PAYWALL_EXPLAINER, UiTags.PAYWALL_RESTORE_BUTTON,
    )
    private val chromeBands = listOf(
        listOf(UiTags.PAYWALL_BACK, UiTags.PAYWALL_TITLE), listOf(UiTags.PAYWALL_BETA_LABEL),
        listOf(UiTags.PAYWALL_ACCOUNT_LABEL, UiTags.PAYWALL_SIGN_OUT_BUTTON), listOf(UiTags.PAYWALL_PLAN_LABEL),
        listOf(UiTags.PAYWALL_EXPLAINER),
    )
    private val freeParts = listOf(
        UiTags.PAYWALL_OFFER_CARD, UiTags.PAYWALL_OFFER_TITLE, UiTags.PAYWALL_OFFER_DESCRIPTION, UiTags.PAYWALL_BUY_BUTTON,
    )
    private val packParts = freeParts
    private val freeStacks = listOf(listOf(UiTags.PAYWALL_OFFER_CARD, UiTags.PAYWALL_OFFER_TITLE, UiTags.PAYWALL_OFFER_DESCRIPTION, UiTags.PAYWALL_BUY_BUTTON))
    private val packStacks = listOf(listOf(UiTags.PAYWALL_OFFER_CARD, UiTags.PAYWALL_OFFER_TITLE, UiTags.PAYWALL_OFFER_DESCRIPTION))

    // Sizes of the map. The Free account's offer is one large card (a 20 dp padding and a 1.5 dp border inside the page's
    // 16 dp margins, so what it holds is 75 dp narrower than the screen), a Pro account's offers are rows (the title and
    // the description beside the price, so only their heights are the map's); the explainer is four lines for a Free
    // account and three for a Pro one.
    private val paywallSizes: Map<String, Size> = mapOf(
        UiTags.PAYWALL_BACK to square(48),
        UiTags.PAYWALL_TITLE to Size(Dim.Any, about(30)),
        UiTags.PAYWALL_BETA_LABEL to Size(Dim.Fill(32), about(64)),
        UiTags.PAYWALL_ACCOUNT_LABEL to Size(Dim.Any, about(20, 2)),
        UiTags.PAYWALL_SIGN_OUT_BUTTON to Size(Dim.Any, fixed(48)),
        UiTags.PAYWALL_PLAN_LABEL to Size(Dim.Any, about(22, 2)),
        UiTags.PAYWALL_EXPLAINER to Size(Dim.Fill(32), about(88, 12)),
        UiTags.PAYWALL_LOADING to square(40),
        UiTags.PAYWALL_LOAD_ERROR to Size(Dim.Fill(32), about(46)),
        UiTags.PAYWALL_PLAN_UNKNOWN to Size(Dim.Fill(32), about(22, 3)),
        UiTags.PAYWALL_RETRY_BUTTON to Size(Dim.Fill(32), fixed(48)),
        UiTags.PAYWALL_OFFER_CARD to Size(Dim.Fill(32), about(188)),
        UiTags.PAYWALL_OFFER_TITLE to Size(Dim.Fill(75), about(28, 2)),
        UiTags.PAYWALL_OFFER_DESCRIPTION to Size(Dim.Fill(75), about(42, 2)),
        UiTags.PAYWALL_BUY_BUTTON to Size(Dim.Fill(75), fixed(56)),
        UiTags.PAYWALL_NO_PACKS to Size(Dim.Fill(32), about(48)),
        UiTags.PAYWALL_NO_PRO to Size(Dim.Fill(32), about(48)),
        UiTags.PAYWALL_PRO_BOUGHT to Size(Dim.Fill(32), about(22, 3)),
        UiTags.PAYWALL_RESTORE_BUTTON to Size(Dim.Fill(32), fixed(56)),
        UiTags.PAYWALL_TOAST to Size(Dim.Fill(32), about(48)),
    )

    // pro_packs: the first pack's row (the map's ~78 dp), its title (22) and its description (20) in the row.
    private val proSizes: Map<String, Size> = mapOf(
        UiTags.PAYWALL_EXPLAINER to Size(Dim.Fill(32), about(66, 12)),
        UiTags.PAYWALL_OFFER_CARD to Size(Dim.Fill(32), about(78)),
        UiTags.PAYWALL_OFFER_TITLE to Size(Dim.Any, about(22, 2)),
        UiTags.PAYWALL_OFFER_DESCRIPTION to Size(Dim.Any, about(20, 2)),
        UiTags.PAYWALL_BUY_BUTTON to Size(Dim.Any, fixed(48)),
    )

    private val accountHeader = listOf(UiTags.ACCOUNT_BACK, UiTags.ACCOUNT_TITLE)
    private val signInRest = listOf(
        UiTags.ACCOUNT_SUBMIT, UiTags.ACCOUNT_TOGGLE_MODE, UiTags.ACCOUNT_FORGOT_PASSWORD, UiTags.ACCOUNT_DIVIDER,
        UiTags.ACCOUNT_GOOGLE_BUTTON, UiTags.ACCOUNT_FEEDBACK_LINK, UiTags.ACCOUNT_NOT_NOW_BUTTON,
    )
    // Creating an account has no forgot-password link.
    private val createRest = signInRest - UiTags.ACCOUNT_FORGOT_PASSWORD
    private val signInTags = accountHeader +
        listOf(UiTags.ACCOUNT_REASON, UiTags.ACCOUNT_EMAIL_FIELD, UiTags.ACCOUNT_PASSWORD_FIELD) + signInRest

    private val accountSizes: Map<String, Size> = mapOf(
        UiTags.ACCOUNT_BACK to square(48),
        UiTags.ACCOUNT_TITLE to Size(Dim.Any, about(30)),
        UiTags.ACCOUNT_REASON to Size(Dim.Fill(32), about(66, 12)),
        UiTags.ACCOUNT_EMAIL_FIELD to Size(Dim.Fill(32), fixed(56)),
        UiTags.ACCOUNT_PASSWORD_FIELD to Size(Dim.Fill(32), fixed(56)),
        UiTags.ACCOUNT_ERROR to Size(Dim.Fill(32), about(20, 2)),
        UiTags.ACCOUNT_INFO to Size(Dim.Fill(32), about(64)),
        UiTags.ACCOUNT_SUBMIT to Size(Dim.Fill(32), fixed(56)),
        UiTags.ACCOUNT_TOGGLE_MODE to Size(Dim.Any, fixed(48)),
        UiTags.ACCOUNT_FORGOT_PASSWORD to Size(Dim.Any, fixed(48)),
        UiTags.ACCOUNT_DIVIDER to Size(Dim.Fill(32), fixed(1)),
        UiTags.ACCOUNT_GOOGLE_BUTTON to Size(Dim.Fill(32), fixed(56)),
        UiTags.ACCOUNT_APPLE_BUTTON to Size(Dim.Fill(32), fixed(56)),
        UiTags.ACCOUNT_FEEDBACK_LINK to Size(Dim.Any, fixed(48)),
        UiTags.ACCOUNT_NOT_NOW_BUTTON to Size(Dim.Fill(32), fixed(56)),
    )

    // A dialog is 364 dp wide on a 412 dp screen with 24 dp inside: what it holds is the screen less 96.
    private val dialogSizes: Map<String, Size> = mapOf(
        UiTags.SCAN_ERROR_TITLE to Size(Dim.Any, about(28, 2)),
        UiTags.SCAN_ERROR_MESSAGE to Size(Dim.Fill(96), Dim.Any),
        UiTags.SCAN_ERROR_NEXT_STEP_BUTTON to Size(Dim.Fill(96), fixed(52)),
        UiTags.SCAN_ERROR_NEXT_TRY_AGAIN to Size(Dim.Fill(96), fixed(52)),
        UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN to Size(Dim.Fill(96), fixed(52)),
        UiTags.SCAN_ERROR_OK_BUTTON to Size(Dim.Fill(96), fixed(52)),
        UiTags.LATE_SCAN_TITLE to Size(Dim.Any, about(28, 2)),
        UiTags.LATE_SCAN_MESSAGE to Size(Dim.Fill(96), Dim.Any),
        UiTags.LATE_SCAN_OK_BUTTON to Size(Dim.Fill(96), fixed(52)),
    )

    // --- Fixtures ----------------------------------------------------------------------------------------

    // The Pro card of the frame (RigCheck Pro, $24.99), and the three packs: a short price, a short one, a long one.
    private val proOffer = fakePackage(
        "pkg-pro", PackageType.LIFETIME, "RigCheck Pro", "\$24.99", "One-time purchase, yours to keep, with a starter bundle of scans.",
    )
    private val smallPack = fakePackage("pkg-10", PackageType.CUSTOM, "10 Scans", "\$4.99", "Good for a few rigs.")
    private val packs = listOf(
        smallPack,
        fakePackage("pkg-30", PackageType.CUSTOM, "30 Scans", "\$9.99", "Best for a season of checks."),
        fakePackage("pkg-100", PackageType.CUSTOM, "100 Scans", "CA\$12.99 one time", "For the whole fleet."),
    )

    // A beta build, as every frame of the round draws it.
    private fun paywall(
        isPro: Boolean?,
        balance: Int? = 3,
        isBeta: Boolean = true,
        onPurchase: (Package, (Boolean, String?) -> Unit) -> Unit = { _, _ -> },
        onRestore: ((Boolean, String?) -> Unit) -> Unit = {},
        loadPackages: suspend () -> List<Package>,
    ): @Composable () -> Unit = {
        PaywallScreen(
            creditBalance = balance,
            onPurchase = onPurchase,
            onRestore = onRestore,
            onDone = {},
            accountLabel = "alice@example.com",
            onSignOut = {},
            isPro = isPro,
            loadPackages = loadPackages,
            isBeta = isBeta,
        )
    }

    // The words RigCheckNavHost gives the signed-out Paywall route.
    private val reason = "Sign in or create an account to buy scans. Your purchases and scan balance follow your account to every device."

    private fun account(showApple: Boolean = false, onGoogle: ((AccountResult) -> Unit) -> Unit = {}): @Composable () -> Unit = {
        AccountScreen(
            reason = reason,
            showApple = showApple,
            onSignIn = { _, _, report -> report(AccountResult.Failure("Invalid login credentials")) },
            onSignUp = { _, _, _ -> },
            onGoogle = onGoogle,
            onApple = {},
            onForgotPassword = { _, report -> report(AccountResult.Success) },
            onNotNow = {},
        )
    }

    // The screen on a phone with no email app: "Send feedback" starts its mail intent with the screen's Context, which
    // here throws ActivityNotFoundException, so the screen shows the line that says so.
    private fun withNoMailApp(content: @Composable () -> Unit): @Composable () -> Unit = {
        val real = LocalContext.current
        val noMailApp = remember(real) {
            object : ContextWrapper(real) {
                override fun startActivity(intent: Intent) = throw ActivityNotFoundException("no mail app")
                override fun startActivity(intent: Intent, options: Bundle?) = throw ActivityNotFoundException("no mail app")
            }
        }
        CompositionLocalProvider(LocalContext provides noMailApp) { content() }
    }

    private fun scanError(message: String, nextSteps: List<ScanNextStep>): @Composable () -> Unit = {
        ScanErrorDialog(error = ScanUiState.Error(message, nextSteps), onDismiss = {}, onNextStep = {})
    }

    private val messageOnly = "Something went wrong with that Scan, and we can't tell whether a Scan Credit was used. " +
        "Check your Scan balance before you try again."
    private val oneStepMessage = "We couldn't use that photo. Try a different photo, or type the numbers in yourself. Nothing was used."
    private val longMessage = "Something went wrong while we were reading the photo. ".repeat(6).trim()
}
