package com.rigcheck.app.ui

import android.content.ActivityNotFoundException
import android.content.Context
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.data.CrashReportStore
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.domain.verdictFor
import com.rigcheck.app.testsupport.fakePackage
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.testsupport.onRigDeleteButton
import com.rigcheck.app.testsupport.scrollToIfScrollable
import com.rigcheck.app.ui.components.CrashReportPrompt
import com.rigcheck.app.ui.components.FeedbackLink
import com.rigcheck.app.ui.components.LateScanDialog
import com.rigcheck.app.ui.components.ScanErrorDialog
import com.rigcheck.app.ui.navigation.EntryModule
import com.rigcheck.app.ui.screens.AccountScreen
import com.rigcheck.app.ui.screens.ChooserScreen
import com.rigcheck.app.ui.screens.DisclaimerScreen
import com.rigcheck.app.ui.screens.HistoryScreen
import com.rigcheck.app.ui.screens.PaywallScreen
import com.rigcheck.app.ui.screens.ResultsScreen
import com.rigcheck.app.ui.screens.RigPickerScreen
import com.rigcheck.app.ui.screens.ScaleTicketEntryScreen
import com.rigcheck.app.ui.screens.TrailerTagEntryScreen
import com.rigcheck.app.ui.screens.TruckTagEntryScreen
import java.io.File
import java.time.Instant
import kotlinx.coroutines.awaitCancellation
import kotlinx.serialization.json.JsonObject
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #188: every element of docs/android-redesign/ui-inventory.json carries its UiTags tag, on a real screen. One test
// per screen (or per state of it that the inventory lists) puts the screen on show in a fixture state and checks that
// every tag the inventory lists for it is displayed; `uv run scripts/ui_inventory.py --check` fails if a UiTags
// constant is named by no test here. A tag lost from a screen fails the test of its screen. The fixtures are the
// ones the screen tests use: a screen is composed directly, RevenueCat is faked as the Offering's packages, and no
// Scan is sent.
@RunWith(AndroidJUnit4::class)
class UiTagsDisplayedTest {

    @get:Rule
    val composeRule = createComposeRule()

    private lateinit var crashFolder: File

    @Before
    fun emptyCrashStore() {
        crashFolder = File(ApplicationProvider.getApplicationContext<Context>().cacheDir, "ui-tags-crash-test")
        crashFolder.deleteRecursively()
    }

    @After
    fun removeCrashStore() {
        crashFolder.deleteRecursively()
    }

    // Looks in the unmerged tree (a tag inside a tappable card or row is only there) and scrolls a form's field
    // into view first. A repeated item counts when its first one is shown.
    private fun assertShown(vararg tags: String) {
        tags.forEach { tag ->
            val nodes = composeRule.onAllNodesWithTag(tag, useUnmergedTree = true)
            assertTrue("$tag is not on the screen", nodes.fetchSemanticsNodes().isNotEmpty())
            nodes.onFirst().scrollToIfScrollable().assertIsDisplayed()
        }
    }

    private fun noticeFor(module: EntryModule) =
        applyScan(module, JsonObject(emptyMap()), TruckTag(), TrailerTag(), ScaleTicket()).notice

    private val rig = RecentRig(
        nickname = "Goose and Addie",
        truck = TruckTag(description = "Ford F-450"),
        trailer = TrailerTag(description = "Brinkley RV"),
        lastUsedAt = Instant.now().minusSeconds(3_600).toString(),
    )

    private fun setPicker(onDeleteRig: (suspend (RecentRig) -> Boolean)?) {
        composeRule.setContent {
            RigPickerScreen(
                recentRigs = listOf(rig),
                creditBalance = 3,
                onSelectRecentRig = {},
                onStartNewRig = {},
                onOpenPaywall = {},
                onOpenHistory = {},
                onDeleteRig = onDeleteRig,
            )
        }
    }

    @Test
    fun rigPicker() {
        setPicker(onDeleteRig = { true })

        assertShown(
            UiTags.PICKER_APP_TITLE, UiTags.OPEN_HISTORY, UiTags.PICKER_CREDIT_CHIP, UiTags.PICKER_HEADER_DIVIDER,
            UiTags.PICKER_HEADING, UiTags.PICKER_SUBHEADING, UiTags.PICKER_RIG_CARD, UiTags.PICKER_RIG_AVATAR,
            UiTags.PICKER_RIG_NICKNAME, UiTags.PICKER_RIG_SUBTITLE, UiTags.PICKER_RIG_LAST_CHECKED,
            UiTags.PICKER_RIG_DELETE, UiTags.PICKER_NEW_RIG_LABEL, UiTags.PICKER_NEW_RIG_INPUT,
            UiTags.PICKER_CREATE_BUTTON, UiTags.PICKER_FEEDBACK_LINK,
        )
    }

    @Test
    fun feedbackLinkOnAPhoneWithNoMailApp() {
        composeRule.setContent {
            FeedbackLink(
                linkModifier = Modifier.testTag(UiTags.PICKER_FEEDBACK_LINK),
                startActivity = { throw ActivityNotFoundException("no mail app") },
            )
        }

        composeRule.onNodeWithTag(UiTags.PICKER_FEEDBACK_LINK).performClick()

        assertShown(UiTags.SEND_FEEDBACK_NO_MAIL_APP)
    }

    @Test
    fun deleteRigDialogAfterAFailedDelete() {
        setPicker(onDeleteRig = { false })

        composeRule.onRigDeleteButton("Goose and Addie").performClick()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CONFIRM).performClick()
        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.DELETE_RIG_ERROR) > 0 }

        assertShown(
            UiTags.DELETE_RIG_DIALOG, UiTags.DELETE_RIG_TITLE, UiTags.DELETE_RIG_BODY, UiTags.DELETE_RIG_ERROR,
            UiTags.DELETE_RIG_CONFIRM, UiTags.DELETE_RIG_CANCEL,
        )
    }

    private fun setChooser(scanState: ScanUiState = ScanUiState.Idle) {
        composeRule.setContent {
            ChooserScreen(
                module = EntryModule.TRUCK,
                creditBalance = 5,
                scanState = scanState,
                onChooseManual = {},
                onPhotoScanned = {},
                onNeedCredits = {},
                onOpenPaywall = {},
                onDismissScanError = {},
                onScanErrorNextStep = {},
            )
        }
    }

    @Test
    fun chooser() {
        setChooser()

        assertShown(
            UiTags.CHOOSER_TITLE, UiTags.CHOOSER_CREDIT_CHIP, UiTags.CHOOSER_STEP_BAR, UiTags.CHOOSER_PROMPT,
            UiTags.CHOOSER_SCAN_CARD, UiTags.CHOOSER_SCAN_BADGE, UiTags.CHOOSER_MANUAL_CARD,
            UiTags.CHOOSER_MANUAL_BADGE, UiTags.CHOOSER_FOOTER_NOTE,
        )
    }

    @Test
    fun chooserWhileAScanIsInFlight() {
        setChooser(ScanUiState.Loading)

        assertShown(UiTags.CHOOSER_LOADING_OVERLAY)
    }

    @Test
    fun photoSourceDialog() {
        setChooser()

        composeRule.onNodeWithTag(UiTags.CHOOSER_SCAN_CARD).performClick()

        assertShown(
            UiTags.PHOTO_DIALOG_TITLE, UiTags.PHOTO_DIALOG_BODY, UiTags.PHOTO_DIALOG_GALLERY,
            UiTags.PHOTO_DIALOG_CAMERA,
        )
    }

    @Test
    fun truckTagEntry() {
        composeRule.setContent {
            TruckTagEntryScreen(
                truck = TruckTag(gvwrLb = 14_000.0, gcwrLb = 13_000.0),
                onTruckChange = {},
                onContinue = {},
                scanNotice = noticeFor(EntryModule.TRUCK),
            )
        }
        composeRule.onNodeWithTag(UiTags.TRUCK_STANDALONE_INFO, useUnmergedTree = true).scrollToIfScrollable()
            .performClick()

        assertShown(
            UiTags.TRUCK_TITLE, UiTags.TRUCK_STEP_BAR, UiTags.SCAN_NOTICE, UiTags.TRUCK_INSTRUCTIONS,
            UiTags.TRUCK_REFERENCE_IMAGE, UiTags.TRUCK_REFERENCE_HINT, UiTags.TRUCK_DESCRIPTION,
            UiTags.TRUCK_NAME_FIELD, UiTags.TRUCK_GVWR_FIELD, UiTags.TRUCK_FRONT_GAWR_FIELD,
            UiTags.TRUCK_REAR_GAWR_FIELD, UiTags.TRUCK_GCWR, UiTags.TRUCK_GCWR_HELP, UiTags.TRUCK_GCWR_WARNING,
            UiTags.TRUCK_STANDALONE_LABEL, UiTags.TRUCK_STANDALONE_INFO, UiTags.TRUCK_STANDALONE_INFO_TEXT,
            UiTags.TRUCK_STANDALONE_FIELD, UiTags.TRUCK_STANDALONE_PANEL, UiTags.TRUCK_STANDALONE_PANEL_TITLE,
            UiTags.TRUCK_STANDALONE_PANEL_BODY, UiTags.SCAN_STANDALONE_TICKET, UiTags.TRUCK_PIN_WEIGHT_LABEL,
            UiTags.PIN_WEIGHT_PCT_SLIDER, UiTags.TRUCK_PIN_WEIGHT_CAPTION, UiTags.TRUCK_NEXT_BUTTON,
        )
    }

    @Test
    fun trailerTagEntry() {
        composeRule.setContent {
            TrailerTagEntryScreen(
                trailer = TrailerTag(),
                onTrailerChange = {},
                onContinue = {},
                scanNotice = noticeFor(EntryModule.TRAILER),
            )
        }

        assertShown(
            UiTags.TRAILER_TITLE, UiTags.TRAILER_STEP_BAR, UiTags.SCAN_NOTICE, UiTags.TRAILER_INSTRUCTIONS,
            UiTags.TRAILER_REFERENCE_IMAGE, UiTags.TRAILER_REFERENCE_HINT, UiTags.TRAILER_DESCRIPTION,
            UiTags.TRAILER_NAME_FIELD, UiTags.TRAILER_GVWR_FIELD, UiTags.TRAILER_GAWR_FIELD,
            UiTags.TRAILER_AXLE_COUNT_FIELD, UiTags.TRAILER_AXLE_COUNT_HELP, UiTags.TRAILER_UVW_FIELD,
            UiTags.TRAILER_NEXT_BUTTON,
        )
    }

    @Test
    fun scaleTicketEntry() {
        composeRule.setContent {
            ScaleTicketEntryScreen(
                scale = ScaleTicket(),
                onScaleChange = {},
                onContinue = {},
                scanNotice = noticeFor(EntryModule.SCALE),
            )
        }

        assertShown(
            UiTags.SCALE_TITLE, UiTags.SCALE_STEP_BAR, UiTags.SCAN_NOTICE, UiTags.SCALE_INSTRUCTIONS,
            UiTags.SCALE_REFERENCE_IMAGE, UiTags.SCALE_LEGEND, UiTags.SCALE_LOCATION, UiTags.SCALE_STEER_FIELD,
            UiTags.SCALE_DRIVE_FIELD, UiTags.SCALE_TRAILER_FIELD, UiTags.SCALE_GROSS_FIELD,
            UiTags.SCALE_CHECK_BUTTON,
        )
    }

    @Test
    fun disclaimer() {
        composeRule.setContent { DisclaimerScreen(onAcknowledge = {}) }

        assertShown(
            UiTags.DISCLAIMER_ICON, UiTags.DISCLAIMER_TITLE, UiTags.DISCLAIMER_BODY_1, UiTags.DISCLAIMER_BODY_2,
            UiTags.DISCLAIMER_ACCEPT_BUTTON,
        )
    }

    private fun row(label: String, estimated: Boolean = false, note: String? = null) = BreakdownItem(
        label = label, tone = Tone.WARNING, actual = 14_720.0, limit = 14_000.0, margin = -720.0, pct = 105,
        note = note, estimated = estimated,
    )

    private fun setResults(
        breakdown: List<BreakdownItem>,
        garageNotice: GarageNotice? = null,
        historyNotice: String? = null,
    ) {
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose and Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
                garageNotice = garageNotice,
                historyNotice = historyNotice,
                onGetPro = {},
            )
        }
    }

    @Test
    fun results() {
        setResults(listOf(row("Tow Vehicle Total (GVWR)", note = "Over by 720 lb.")))
        composeRule.onNodeWithTag(UiTags.RESULTS_ROW).performClick()

        assertShown(
            UiTags.RESULTS_RIG_NAME, UiTags.RESULTS_DATE, UiTags.RESULTS_VERDICT, UiTags.RESULTS_BREAKDOWN_CARD,
            UiTags.RESULTS_ROW, UiTags.RESULTS_ROW_ICON, UiTags.RESULTS_ROW_LABEL, UiTags.RESULTS_ROW_VALUES,
            UiTags.RESULTS_ROW_PCT, UiTags.RESULTS_ROW_BAR, UiTags.RESULTS_ROW_NOTE, UiTags.RESULTS_FOOTER_NOTE,
            UiTags.RESULTS_START_ANOTHER_BUTTON,
        )
    }

    @Test
    fun resultsWithEstimatedFigures() {
        setResults(listOf(row("Trailer Axle", estimated = true)))

        assertShown(UiTags.RESULTS_ESTIMATED_NOTICE)
    }

    @Test
    fun resultsWithAFullGarageAndAHistoryThatDidNotSave() {
        setResults(
            listOf(row("Tow Vehicle Total (GVWR)")),
            garageNotice = GarageNotice("Your Garage is full, so it wasn't saved.", offerPro = true),
            historyNotice = "We couldn't save this check to your History.",
        )

        assertShown(UiTags.GARAGE_NOTICE, UiTags.GARAGE_NOTICE_GET_PRO, UiTags.HISTORY_NOTICE)
    }

    @Test
    fun historyWithEntries() {
        val entries = listOf(HistoryEntry("1", "2026-10-20T10:00:00Z", "Goose and Addie", VerdictStatus.PASS))
        composeRule.setContent {
            HistoryScreen(entries = entries, limitNotice = "The Free plan keeps your last 5 checks.", onUpgrade = {})
        }

        assertShown(
            UiTags.HISTORY_TITLE, UiTags.HISTORY_SUBTITLE, UiTags.HISTORY_LIMIT_NOTICE, UiTags.HISTORY_UPGRADE,
            UiTags.HISTORY_ENTRY, UiTags.HISTORY_ENTRY_RIG, UiTags.HISTORY_ENTRY_DATE, UiTags.HISTORY_ENTRY_VERDICT,
        )
    }

    @Test
    fun historyWithNoChecksYet() {
        composeRule.setContent { HistoryScreen(entries = emptyList()) }

        assertShown(UiTags.HISTORY_EMPTY)
    }

    private val proPackage = fakePackage("pkg-a", PackageType.LIFETIME, "Pro (lifetime)", "\$14.99", "Yours to keep")
    private val smallPack = fakePackage("pkg-b", PackageType.CUSTOM, "10 scans", "\$2.99")

    private fun setPaywall(
        isPro: Boolean?,
        isBeta: Boolean = false,
        onPurchase: (Package, (Boolean, String?) -> Unit) -> Unit = { _, _ -> },
        loadPackages: suspend () -> List<Package>,
    ) {
        composeRule.setContent {
            PaywallScreen(
                creditBalance = 5,
                onPurchase = onPurchase,
                onRestore = {},
                onDone = {},
                accountLabel = "alice@example.com",
                onSignOut = {},
                isPro = isPro,
                loadPackages = loadPackages,
                isBeta = isBeta,
            )
        }
    }

    @Test
    fun paywallOfferingProToAFreeAccountInTheBeta() {
        setPaywall(isPro = false, isBeta = true) { listOf(proPackage) }

        assertShown(
            UiTags.PAYWALL_BACK, UiTags.PAYWALL_TITLE, UiTags.PAYWALL_ACCOUNT_LABEL, UiTags.PAYWALL_SIGN_OUT_BUTTON,
            UiTags.PAYWALL_PLAN_LABEL, UiTags.PAYWALL_EXPLAINER, UiTags.PAYWALL_BETA_LABEL,
            UiTags.PAYWALL_OFFER_CARD, UiTags.PAYWALL_OFFER_TITLE, UiTags.PAYWALL_OFFER_DESCRIPTION,
            UiTags.PAYWALL_BUY_BUTTON, UiTags.PAYWALL_RESTORE_BUTTON,
        )
    }

    @Test
    fun paywallWhileTheOffersLoad() {
        setPaywall(isPro = false) { awaitCancellation() }

        assertShown(UiTags.PAYWALL_LOADING)
    }

    @Test
    fun paywallWhenTheOffersCouldNotLoad() {
        setPaywall(isPro = false) { error("offline") }

        assertShown(UiTags.PAYWALL_LOAD_ERROR)
    }

    @Test
    fun paywallWhenThePlanIsNotKnownYet() {
        setPaywall(isPro = null) { listOf(proPackage) }

        assertShown(UiTags.PAYWALL_PLAN_UNKNOWN, UiTags.PAYWALL_RETRY_BUTTON)
    }

    @Test
    fun paywallForAProAccountWithNoPacks() {
        setPaywall(isPro = true) { emptyList() }

        assertShown(UiTags.PAYWALL_NO_PACKS)
    }

    @Test
    fun paywallForAFreeAccountWithNoProToBuy() {
        setPaywall(isPro = false) { listOf(smallPack) }

        assertShown(UiTags.PAYWALL_NO_PRO)
    }

    @Test
    fun paywallAfterBuyingProWhileThePlanCatchesUp() {
        setPaywall(isPro = false, onPurchase = { _, report -> report(true, null) }) { listOf(proPackage) }
        composeRule.waitUntil(timeoutMillis = 5_000) { composeRule.nodesWithTag(UiTags.PAYWALL_BUY_BUTTON) > 0 }

        composeRule.onNodeWithTag(UiTags.PAYWALL_BUY_BUTTON).performClick()

        assertShown(UiTags.PAYWALL_PRO_BOUGHT, UiTags.PAYWALL_RETRY_BUTTON)
    }

    private fun setAccount() {
        composeRule.setContent {
            AccountScreen(
                reason = "Sign in to buy scans.",
                showApple = true,
                onSignIn = { _, _, report -> report(AccountResult.Failure("Invalid login credentials")) },
                onSignUp = { _, _, _ -> },
                onGoogle = {},
                onApple = {},
                onForgotPassword = { _, report -> report(AccountResult.Success) },
                onNotNow = {},
            )
        }
    }

    @Test
    fun accountSignIn() {
        setAccount()

        assertShown(
            UiTags.ACCOUNT_TITLE, UiTags.ACCOUNT_REASON, UiTags.ACCOUNT_EMAIL_FIELD, UiTags.ACCOUNT_PASSWORD_FIELD,
            UiTags.ACCOUNT_SUBMIT, UiTags.ACCOUNT_TOGGLE_MODE, UiTags.ACCOUNT_FORGOT_PASSWORD,
            UiTags.ACCOUNT_DIVIDER, UiTags.ACCOUNT_GOOGLE_BUTTON, UiTags.ACCOUNT_APPLE_BUTTON,
            UiTags.ACCOUNT_NOT_NOW_BUTTON, UiTags.ACCOUNT_FEEDBACK_LINK,
        )
    }

    @Test
    fun accountAfterAFailedSignIn() {
        setAccount()
        composeRule.onNodeWithTag(UiTags.ACCOUNT_EMAIL_FIELD).performTextInput("alice@example.com")
        composeRule.onNodeWithTag(UiTags.ACCOUNT_PASSWORD_FIELD).performTextInput("a-long-password")

        composeRule.onNodeWithTag(UiTags.ACCOUNT_SUBMIT).performClick()

        assertShown(UiTags.ACCOUNT_ERROR)
    }

    @Test
    fun accountAfterAskingForAPasswordReset() {
        setAccount()
        composeRule.onNodeWithTag(UiTags.ACCOUNT_EMAIL_FIELD).performTextInput("alice@example.com")

        composeRule.onNodeWithTag(UiTags.ACCOUNT_FORGOT_PASSWORD).performClick()

        assertShown(UiTags.ACCOUNT_INFO)
    }

    @Test
    fun scanErrorDialogWithEveryNextStep() {
        composeRule.setContent {
            ScanErrorDialog(
                error = ScanUiState.Error("Something went wrong.", ScanNextStep.entries),
                onDismiss = {},
                onNextStep = {},
            )
        }

        assertShown(
            UiTags.SCAN_ERROR_TITLE, UiTags.SCAN_ERROR_MESSAGE, UiTags.SCAN_ERROR_NEXT_STEP_BUTTON,
            UiTags.SCAN_ERROR_NEXT_SIGN_IN, UiTags.SCAN_ERROR_NEXT_BUY_SCANS, UiTags.SCAN_ERROR_NEXT_TRY_AGAIN,
            UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO, UiTags.SCAN_ERROR_NEXT_TYPE_IT_IN, UiTags.SCAN_ERROR_OK_BUTTON,
        )
    }

    @Test
    fun lateScanDialog() {
        composeRule.setContent { LateScanDialog(message = ScanMessages.RESULT_NOT_USED, onDismiss = {}) }

        assertShown(UiTags.LATE_SCAN_TITLE, UiTags.LATE_SCAN_MESSAGE, UiTags.LATE_SCAN_OK_BUTTON)
    }

    @Test
    fun crashReportQuestion() {
        val store = CrashReportStore(crashFolder).also { it.save("the report") }
        composeRule.setContent { CrashReportPrompt(store, startActivity = {}) }

        assertShown(
            UiTags.CRASH_PROMPT_QUESTION, UiTags.CRASH_PROMPT_DETAILS, UiTags.CRASH_PROMPT_SEND,
            UiTags.CRASH_PROMPT_DISMISS,
        )
    }

    @Test
    fun crashReportQuestionOnAPhoneWithNoMailApp() {
        val store = CrashReportStore(crashFolder).also { it.save("the report") }
        composeRule.setContent {
            CrashReportPrompt(store, startActivity = { throw ActivityNotFoundException("no mail app") })
        }

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_SEND).performClick()

        assertShown(UiTags.CRASH_PROMPT_NO_MAIL_APP)
    }
}
