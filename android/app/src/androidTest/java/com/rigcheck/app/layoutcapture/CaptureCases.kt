package com.rigcheck.app.layoutcapture

import android.content.ActivityNotFoundException
import android.content.ContextWrapper
import android.content.Intent
import android.os.Bundle
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.performTouchInput
import androidx.test.platform.app.InstrumentationRegistry
import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PackageType
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.data.CrashReportStore
import com.rigcheck.app.data.HistoryEntry
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.COMBINED_RIG_WEIGHT_LABEL
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.domain.verdictFor
import com.rigcheck.app.testsupport.fakePackage
import com.rigcheck.app.testsupport.nodesWithTag
import com.rigcheck.app.ui.GarageNotice
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.applyScan
import com.rigcheck.app.ui.components.CrashReportPrompt
import com.rigcheck.app.ui.components.LateScanDialog
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
import kotlinx.serialization.json.JsonPrimitive

// One screen state of docs/android-redesign/ui-inventory.json to capture (#189): `screen` is the inventory's screen id,
// `state` names the state (the file is `<screen>__<state>`), `content` puts the real screen on show inside the app's
// root (theme, background and safe-area padding), and `setUp` taps or types its way into the state. The fixtures are
// the ones UiTagsDisplayedTest and the screen tests use: RevenueCat is faked as the Offering's packages, no Scan is
// sent, nothing calls the network.
class CaptureCase(
    val screen: String,
    val state: String,
    val setUp: CaptureScope.() -> Unit = {},
    val content: @Composable () -> Unit,
) {
    val id: String get() = "${screen}__$state"
}

private fun rig(nickname: String, secondsAgo: Long = 3_600) = RecentRig(
    nickname = nickname,
    truck = TruckTag(description = "Ford F-450"),
    trailer = TrailerTag(description = "Brinkley RV"),
    lastUsedAt = Instant.parse("2026-10-20T10:00:00Z").minusSeconds(secondsAgo).toString(),
)

private val oneRig = listOf(rig("Goose and Addie"))
private val sixRigs = (1..6).map { rig("Rig number $it", secondsAgo = it * 86_400L) }

private fun picker(
    rigs: List<RecentRig> = oneRig,
    balance: Int? = 3,
    onDeleteRig: (suspend (RecentRig) -> Boolean)? = { true },
): @Composable () -> Unit = {
    RigPickerScreen(
        recentRigs = rigs,
        creditBalance = balance,
        onSelectRecentRig = {},
        onStartNewRig = {},
        onOpenPaywall = {},
        onOpenHistory = {},
        onDeleteRig = onDeleteRig,
    )
}

private fun chooser(
    module: EntryModule = EntryModule.TRUCK,
    balance: Int? = 5,
    scanState: ScanUiState = ScanUiState.Idle,
): @Composable () -> Unit = {
    ChooserScreen(
        module = module,
        creditBalance = balance,
        scanState = scanState,
        onChooseManual = {},
        onPhotoScanned = {},
        onNeedCredits = {},
        onOpenPaywall = {},
        onDismissScanError = {},
        onScanErrorNextStep = {},
    )
}

private fun noticeFor(module: EntryModule, fields: JsonObject = JsonObject(emptyMap())) =
    applyScan(module, fields, TruckTag(), TrailerTag(), ScaleTicket()).notice

private val filledTruck = TruckTag(
    description = "Ford F-450", name = "Goose", gvwrLb = 14_000.0, frontGawrLb = 6_000.0, rearGawrLb = 9_750.0,
    gcwrLb = 28_000.0, standaloneWeightLb = null,
)

private fun truck(
    truck: TruckTag = TruckTag(),
    scanState: ScanUiState = ScanUiState.Idle,
    notice: ScanNotice? = null,
): @Composable () -> Unit = {
    TruckTagEntryScreen(
        truck = truck,
        onTruckChange = {},
        onContinue = {},
        scanState = scanState,
        creditBalance = 5,
        scanNotice = notice,
    )
}

private fun trailer(trailer: TrailerTag = TrailerTag(), notice: ScanNotice? = null): @Composable () -> Unit = {
    TrailerTagEntryScreen(trailer = trailer, onTrailerChange = {}, onContinue = {}, scanNotice = notice)
}

private fun scale(scale: ScaleTicket = ScaleTicket(), notice: ScanNotice? = null): @Composable () -> Unit = {
    ScaleTicketEntryScreen(scale = scale, onScaleChange = {}, onContinue = {}, scanNotice = notice)
}

private fun CaptureScope.holdOn(tag: String) {
    node(tag).performTouchInput {
        down(center)
        advanceEventTime(700)
        moveTo(center + Offset(10f, 10f))
    }
    rule.waitForIdle()
}

private fun row(label: String, tone: Tone, pct: Int, note: String? = null, estimated: Boolean = false) = BreakdownItem(
    label = label, tone = tone, actual = pct * 140.0, limit = 14_000.0, margin = 14_000.0 - pct * 140.0, pct = pct,
    note = note, estimated = estimated,
)

private val passRows = listOf(
    row("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 82),
    row("Tow Vehicle Front Axle", Tone.SUCCESS, 71),
    row("Tow Vehicle Rear Axle", Tone.SUCCESS, 90),
    row("Trailer Axle(s)", Tone.SUCCESS, 64),
    row("Trailer Total (GVWR)", Tone.SUCCESS, 77),
    row(COMBINED_RIG_WEIGHT_LABEL, Tone.SUCCESS, 88),
)
private val failRows = listOf(
    row("Tow Vehicle Total (GVWR)", Tone.WARNING, 105, note = "Over by 720 lb."),
    row("Tow Vehicle Front Axle", Tone.SUCCESS, 71),
    row("Tow Vehicle Rear Axle", Tone.WARNING, 112, note = "Over by 1,680 lb."),
    row("Trailer Axle(s)", Tone.INSUFFICIENT, 0, note = "Add the trailer's weight rating to check this."),
    row(COMBINED_RIG_WEIGHT_LABEL, Tone.INSUFFICIENT, 0),
)

private fun results(
    rows: List<BreakdownItem>,
    garageNotice: GarageNotice? = null,
    historyNotice: String? = null,
): @Composable () -> Unit = {
    ResultsScreen(
        rigNickname = "Goose and Addie",
        breakdown = rows,
        verdict = verdictFor(rows),
        onStartAnother = {},
        garageNotice = garageNotice,
        historyNotice = historyNotice,
        onGetPro = {},
    )
}

private fun entries(count: Int) = (1..count).map {
    HistoryEntry(
        "$it", "2026-10-${(28 - it % 27).toString().padStart(2, '0')}T10:00:00Z", "Rig number $it",
        VerdictStatus.entries[it % VerdictStatus.entries.size],
    )
}

private val proPackage = fakePackage("pkg-pro", PackageType.LIFETIME, "Pro (lifetime)", "\$14.99", "Yours to keep")
private val smallPack = fakePackage("pkg-10", PackageType.CUSTOM, "10 scans", "\$2.99")
private val bigPack = fakePackage("pkg-50", PackageType.CUSTOM, "50 scans", "\$9.99")

private fun paywall(
    isPro: Boolean?,
    balance: Int? = 5,
    isBeta: Boolean = false,
    onPurchase: (Package, (Boolean, String?) -> Unit) -> Unit = { _, _ -> },
    loadPackages: suspend () -> List<Package>,
): @Composable () -> Unit = {
    PaywallScreen(
        creditBalance = balance,
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

private fun account(
    showApple: Boolean = false,
    onSignIn: (String, String, (AccountResult) -> Unit) -> Unit = { _, _, report ->
        report(AccountResult.Failure("Invalid login credentials"))
    },
    onSignUp: (String, String, (AccountResult) -> Unit) -> Unit = { _, _, _ -> },
    onForgotPassword: (String, (AccountResult) -> Unit) -> Unit = { _, report -> report(AccountResult.Success) },
): @Composable () -> Unit = {
    AccountScreen(
        reason = "Sign in to buy scans.",
        showApple = showApple,
        onSignIn = onSignIn,
        onSignUp = onSignUp,
        onGoogle = {},
        onApple = {},
        onForgotPassword = onForgotPassword,
        onNotNow = {},
    )
}

private fun CaptureScope.fillSignIn() {
    type(UiTags.ACCOUNT_EMAIL_FIELD, "alice@example.com")
    type(UiTags.ACCOUNT_PASSWORD_FIELD, "a-long-password")
    hideKeyboard()
}

private fun crashStore(): CrashReportStore {
    val folder = File(
        InstrumentationRegistry.getInstrumentation().targetContext.cacheDir,
        "layout-capture-crash",
    ).also { it.deleteRecursively() }
    return CrashReportStore(folder).also { it.save("the report") }
}

// The screen on a phone with no email app: "Send feedback" starts its mail intent with the screen's Context, which
// here throws ActivityNotFoundException, so the screen shows the line that says so instead of opening a mail app.
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

private val longMessage = "Something went wrong while we were reading the photo. ".repeat(6).trim()

val captureCases: List<CaptureCase> = listOf(
    // rig_picker
    CaptureCase("rig_picker", "no_saved_rigs", content = picker(rigs = emptyList())),
    CaptureCase("rig_picker", "one_saved_rig_signed_in", content = picker()),
    CaptureCase("rig_picker", "one_saved_rig_signed_out", content = picker(onDeleteRig = null)),
    CaptureCase("rig_picker", "six_saved_rigs", content = picker(rigs = sixRigs)),
    CaptureCase("rig_picker", "balance_not_loaded", content = picker(balance = null)),
    CaptureCase("rig_picker", "balance_zero", content = picker(balance = 0)),
    CaptureCase("rig_picker", "balance_one", content = picker(balance = 1)),
    CaptureCase("rig_picker", "balance_many", content = picker(balance = 120)),
    CaptureCase(
        "rig_picker", "new_rig_input_filled",
        setUp = {
            type(UiTags.PICKER_NEW_RIG_INPUT, "Weekend rig")
            hideKeyboard()
        },
        content = picker(),
    ),

    CaptureCase(
        "rig_picker", "feedback_no_mail_app",
        setUp = { tap(UiTags.PICKER_FEEDBACK_LINK) },
        content = withNoMailApp(picker()),
    ),

    // delete_rig_dialog
    CaptureCase(
        "delete_rig_dialog", "question",
        setUp = { tap(UiTags.PICKER_RIG_DELETE) },
        content = picker(),
    ),
    CaptureCase(
        "delete_rig_dialog", "deleting",
        setUp = {
            tap(UiTags.PICKER_RIG_DELETE)
            tap(UiTags.DELETE_RIG_CONFIRM)
        },
        content = picker(onDeleteRig = { awaitCancellation() }),
    ),
    CaptureCase(
        "delete_rig_dialog", "delete_failed",
        setUp = {
            tap(UiTags.PICKER_RIG_DELETE)
            tap(UiTags.DELETE_RIG_CONFIRM)
            rule.waitUntil(timeoutMillis = 5_000) { rule.nodesWithTag(UiTags.DELETE_RIG_ERROR) > 0 }
        },
        content = picker(onDeleteRig = { false }),
    ),

    // chooser
    CaptureCase("chooser", "truck_module", content = chooser(EntryModule.TRUCK)),
    CaptureCase("chooser", "trailer_module", content = chooser(EntryModule.TRAILER)),
    CaptureCase("chooser", "scale_module", content = chooser(EntryModule.SCALE)),
    CaptureCase("chooser", "scan_in_flight", content = chooser(scanState = ScanUiState.Loading)),
    CaptureCase(
        "chooser", "scan_error_on_top",
        content = chooser(scanState = ScanUiState.Error("Something went wrong.", listOf(ScanNextStep.TRY_AGAIN))),
    ),
    CaptureCase("chooser", "balance_zero", content = chooser(balance = 0)),
    CaptureCase("chooser", "balance_not_loaded", content = chooser(balance = null)),

    // photo_source_dialog
    CaptureCase(
        "photo_source_dialog", "default",
        setUp = { tap(UiTags.CHOOSER_SCAN_CARD) },
        content = chooser(),
    ),

    // scan_error_dialog, over the Chooser
    CaptureCase(
        "scan_error_dialog", "message_only_ok",
        content = chooser(scanState = ScanUiState.Error("Something went wrong.")),
    ),
    CaptureCase(
        "scan_error_dialog", "one_next_step",
        content = chooser(scanState = ScanUiState.Error("Sign in to scan.", listOf(ScanNextStep.SIGN_IN))),
    ),
    CaptureCase(
        "scan_error_dialog", "two_next_steps",
        content = chooser(
            scanState = ScanUiState.Error(
                "We couldn't read that photo.",
                listOf(ScanNextStep.TRY_AGAIN, ScanNextStep.TYPE_IT_IN),
            ),
        ),
    ),
    CaptureCase(
        "scan_error_dialog", "five_next_steps",
        content = chooser(scanState = ScanUiState.Error("Something went wrong.", ScanNextStep.entries)),
    ),
    CaptureCase(
        "scan_error_dialog", "long_message",
        content = chooser(scanState = ScanUiState.Error(longMessage, listOf(ScanNextStep.TRY_AGAIN))),
    ),

    // truck_tag_entry
    CaptureCase("truck_tag_entry", "blank", content = truck()),
    CaptureCase("truck_tag_entry", "filled", content = truck(filledTruck)),
    CaptureCase("truck_tag_entry", "scan_notice_nothing_read", content = truck(notice = noticeFor(EntryModule.TRUCK))),
    CaptureCase(
        "truck_tag_entry", "scan_notice_some_read",
        content = truck(
            TruckTag(description = "Ford F-450", gvwrLb = 14_000.0),
            notice = noticeFor(
                EntryModule.TRUCK,
                JsonObject(mapOf("manufacturer" to JsonPrimitive("Ford F-450"), "gvwr_lb" to JsonPrimitive(14_000))),
            ),
        ),
    ),
    CaptureCase(
        "truck_tag_entry", "gcwr_below_gvwr_warning",
        content = truck(TruckTag(gvwrLb = 14_000.0, gcwrLb = 13_000.0)),
    ),
    CaptureCase(
        "truck_tag_entry", "standalone_info_expanded",
        setUp = { tap(UiTags.TRUCK_STANDALONE_INFO) },
        content = truck(),
    ),
    CaptureCase(
        "truck_tag_entry", "standalone_filled",
        content = truck(TruckTag(standaloneWeightLb = 9_500.0)),
    ),
    CaptureCase(
        "truck_tag_entry", "standalone_scan_in_flight",
        content = truck(scanState = ScanUiState.Loading),
    ),
    CaptureCase(
        "truck_tag_entry", "scan_error_on_top",
        content = truck(scanState = ScanUiState.Error("Something went wrong.", listOf(ScanNextStep.TRY_AGAIN))),
    ),
    CaptureCase(
        "truck_tag_entry", "keyboard_open",
        setUp = {
            tap(UiTags.TRUCK_GVWR_FIELD)
            awaitKeyboardShown()
        },
        content = truck(),
    ),
    CaptureCase(
        "truck_tag_entry", "image_zoom_active",
        setUp = { holdOn(UiTags.TRUCK_REFERENCE_IMAGE) },
        content = truck(),
    ),

    // trailer_tag_entry
    CaptureCase("trailer_tag_entry", "blank", content = trailer()),
    CaptureCase(
        "trailer_tag_entry", "filled",
        content = trailer(
            TrailerTag(
                description = "Brinkley RV", name = "Addie", gvwrLb = 11_000.0, gawrPerAxleLb = 5_200.0, axleCount = 2,
                uvwLb = 8_400.0,
            ),
        ),
    ),
    CaptureCase("trailer_tag_entry", "scan_notice_nothing_read", content = trailer(notice = noticeFor(EntryModule.TRAILER))),
    CaptureCase(
        "trailer_tag_entry", "axle_count_filled",
        content = trailer(TrailerTag(axleCount = 3)),
    ),
    CaptureCase(
        "trailer_tag_entry", "keyboard_open",
        setUp = {
            tap(UiTags.TRAILER_GVWR_FIELD)
            awaitKeyboardShown()
        },
        content = trailer(),
    ),
    CaptureCase(
        "trailer_tag_entry", "image_zoom_active",
        setUp = { holdOn(UiTags.TRAILER_REFERENCE_IMAGE) },
        content = trailer(),
    ),

    // scale_ticket_entry
    CaptureCase("scale_ticket_entry", "blank", content = scale()),
    CaptureCase(
        "scale_ticket_entry", "filled",
        content = scale(
            ScaleTicket(
                locationName = "CAT Scale, Exit 14", steerAxleLb = 5_400.0, driveAxleLb = 9_100.0,
                trailerAxleLb = 8_800.0, grossWeightLb = 23_300.0,
            ),
        ),
    ),
    CaptureCase("scale_ticket_entry", "scan_notice_nothing_read", content = scale(notice = noticeFor(EntryModule.SCALE))),
    CaptureCase(
        "scale_ticket_entry", "keyboard_open",
        setUp = {
            tap(UiTags.SCALE_STEER_FIELD)
            awaitKeyboardShown()
        },
        content = scale(),
    ),

    // disclaimer
    CaptureCase("disclaimer", "default") { DisclaimerScreen(onAcknowledge = {}) },

    // results
    CaptureCase("results", "safe_to_tow", content = results(passRows)),
    CaptureCase("results", "safe_to_tow_without_combined_row", content = results(passRows.dropLast(1))),
    CaptureCase("results", "not_safe_to_tow", content = results(failRows)),
    CaptureCase(
        "results", "partially_checked",
        content = results(passRows.take(3) + failRows[3]),
    ),
    CaptureCase(
        "results", "not_enough_information",
        content = results(failRows.map { it.copy(tone = Tone.INSUFFICIENT, pct = 0, note = null) }),
    ),
    CaptureCase(
        "results", "estimated_figures_notice",
        content = results(passRows.map { it.copy(estimated = true) }),
    ),
    CaptureCase(
        "results", "garage_notice_free_with_get_pro",
        content = results(passRows, garageNotice = GarageNotice("Your Garage is full, so it wasn't saved.", offerPro = true)),
    ),
    CaptureCase(
        "results", "garage_notice_without_get_pro",
        content = results(passRows, garageNotice = GarageNotice("We couldn't save it to your Garage.", offerPro = false)),
    ),
    CaptureCase(
        "results", "history_notice",
        content = results(passRows, historyNotice = "We couldn't save this check to your History."),
    ),
    CaptureCase(
        "results", "row_note_expanded",
        setUp = { tap(UiTags.RESULTS_ROW) },
        content = results(failRows),
    ),

    // history
    CaptureCase("history", "empty", content = { HistoryScreen(entries = emptyList()) }),
    CaptureCase("history", "a_few_entries", content = { HistoryScreen(entries = entries(3)) }),
    CaptureCase("history", "many_entries", content = { HistoryScreen(entries = entries(25)) }),
    CaptureCase(
        "history", "limit_notice",
        content = { HistoryScreen(entries = entries(5), limitNotice = "The Free plan keeps your last 5 checks.", onUpgrade = {}) },
    ),
    CaptureCase("history", "all_four_verdict_labels", content = { HistoryScreen(entries = entries(4)) }),

    // paywall
    CaptureCase("paywall", "offers_loading", content = paywall(isPro = false) { awaitCancellation() }),
    CaptureCase("paywall", "offers_load_error", content = paywall(isPro = false) { error("offline") }),
    CaptureCase("paywall", "plan_unknown", content = paywall(isPro = null) { listOf(proPackage) }),
    CaptureCase("paywall", "free_one_pro_card", content = paywall(isPro = false) { listOf(proPackage) }),
    CaptureCase("paywall", "free_one_pro_card_beta", content = paywall(isPro = false, isBeta = true) { listOf(proPackage) }),
    CaptureCase(
        "paywall", "free_after_buying_pro",
        setUp = {
            rule.waitUntil(timeoutMillis = 5_000) { rule.nodesWithTag(UiTags.PAYWALL_BUY_BUTTON) > 0 }
            tap(UiTags.PAYWALL_BUY_BUTTON)
        },
        content = paywall(isPro = false, onPurchase = { _, report -> report(true, null) }) { listOf(proPackage) },
    ),
    CaptureCase("paywall", "pro_several_scan_packs", content = paywall(isPro = true) { listOf(smallPack, bigPack) }),
    CaptureCase("paywall", "pro_no_packs", content = paywall(isPro = true) { emptyList() }),
    CaptureCase("paywall", "free_no_pro_package", content = paywall(isPro = false) { listOf(smallPack) }),
    CaptureCase(
        "paywall", "busy",
        setUp = {
            rule.waitUntil(timeoutMillis = 5_000) { rule.nodesWithTag(UiTags.PAYWALL_BUY_BUTTON) > 0 }
            tap(UiTags.PAYWALL_BUY_BUTTON)
        },
        content = paywall(isPro = false) { listOf(proPackage) },
    ),
    CaptureCase("paywall", "balance_zero", content = paywall(isPro = false, balance = 0) { listOf(proPackage) }),
    CaptureCase("paywall", "balance_one", content = paywall(isPro = false, balance = 1) { listOf(proPackage) }),
    CaptureCase("paywall", "balance_many", content = paywall(isPro = false, balance = 120) { listOf(proPackage) }),

    // account
    CaptureCase("account", "sign_in", content = account()),
    CaptureCase(
        "account", "create_account",
        setUp = { tap(UiTags.ACCOUNT_TOGGLE_MODE) },
        content = account(),
    ),
    CaptureCase(
        "account", "busy",
        setUp = {
            fillSignIn()
            tap(UiTags.ACCOUNT_SUBMIT)
        },
        content = account(onSignIn = { _, _, _ -> }),
    ),
    CaptureCase(
        "account", "error",
        setUp = {
            fillSignIn()
            tap(UiTags.ACCOUNT_SUBMIT)
        },
        content = account(),
    ),
    CaptureCase(
        "account", "info_reset_sent",
        setUp = {
            type(UiTags.ACCOUNT_EMAIL_FIELD, "alice@example.com")
            hideKeyboard()
            tap(UiTags.ACCOUNT_FORGOT_PASSWORD)
        },
        content = account(),
    ),
    CaptureCase(
        "account", "info_confirm_email",
        setUp = {
            tap(UiTags.ACCOUNT_TOGGLE_MODE)
            fillSignIn()
            tap(UiTags.ACCOUNT_SUBMIT)
        },
        content = account(onSignUp = { _, _, report -> report(AccountResult.NeedsConfirmation) }),
    ),
    CaptureCase("account", "apple_button_shown", content = account(showApple = true)),
    CaptureCase(
        "account", "keyboard_open",
        setUp = {
            tap(UiTags.ACCOUNT_EMAIL_FIELD)
            awaitKeyboardShown()
        },
        content = account(),
    ),

    CaptureCase(
        "account", "feedback_no_mail_app",
        setUp = { tap(UiTags.ACCOUNT_FEEDBACK_LINK) },
        content = withNoMailApp(account()),
    ),

    // late_scan_dialog and crash_report_dialog, over the Rig picker
    CaptureCase(
        "late_scan_dialog", "credit_used",
        content = {
            picker()()
            LateScanDialog(message = ScanMessages.RESULT_NOT_USED, onDismiss = {})
        },
    ),
    CaptureCase(
        "late_scan_dialog", "no_credit_used",
        content = {
            picker()()
            LateScanDialog(message = ScanMessages.EXPIRED_SIGN_IN, onDismiss = {})
        },
    ),
    CaptureCase(
        "crash_report_dialog", "question",
        content = {
            picker()()
            CrashReportPrompt(remember { crashStore() }, startActivity = {})
        },
    ),
    CaptureCase(
        "crash_report_dialog", "no_email_app",
        setUp = { tap(UiTags.CRASH_PROMPT_SEND) },
        content = {
            picker()()
            CrashReportPrompt(
                remember { crashStore() },
                startActivity = { throw ActivityNotFoundException("no mail app") },
            )
        },
    ),
)

// The screens that are also captured at font scale 2.0 (the others only at 1.0).
val largeFontScreens = setOf("disclaimer", "results")
