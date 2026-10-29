package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.data.createScanPhotoUri
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.canStartScan
import com.rigcheck.app.ui.components.CreditBalanceChip
import com.rigcheck.app.ui.components.PhotoSourceDialog
import com.rigcheck.app.ui.components.RigCheckBadge
import com.rigcheck.app.ui.components.RigCheckBadgeKind
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckOptionCard
import com.rigcheck.app.ui.components.RigCheckOptionKind
import com.rigcheck.app.ui.components.RigCheckStepIndicator
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.components.ScanErrorDialog
import com.rigcheck.app.ui.components.chipBelowTitle
import com.rigcheck.app.ui.navigation.EntryModule
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

private data class ChooserCopy(val title: String, val prompt: String)

private fun copyFor(module: EntryModule): ChooserCopy = when (module) {
    EntryModule.TRUCK -> ChooserCopy("Truck Tag", "How do you want to enter your truck's compliance-label values?")
    EntryModule.TRAILER -> ChooserCopy("Trailer Tag", "How do you want to enter your trailer's compliance-label values?")
    EntryModule.SCALE -> ChooserCopy("Scale Ticket", "How do you want to enter your CAT Scale ticket values?")
}

@Composable
fun ChooserScreen(
    module: EntryModule,
    creditBalance: Int?,
    // Whether the account is signed out: then the balance chip says "0 scans", not "…".
    signedOut: Boolean = false,
    scanState: ScanUiState,
    onChooseManual: () -> Unit,
    onPhotoScanned: (Uri) -> Unit,
    onNeedCredits: () -> Unit,
    onOpenPaywall: () -> Unit,
    onDismissScanError: () -> Unit,
    onScanErrorNextStep: (ScanNextStep) -> Unit,
    // The top bar's Back. It is disabled, and the overlay takes every tap, while a Scan is out.
    onBack: () -> Unit = {},
) {
    val copy = copyFor(module)
    val context = LocalContext.current
    var pendingPhotoUri by remember { mutableStateOf<Uri?>(null) }
    var showSourceDialog by remember { mutableStateOf(false) }

    // System camera intent, not a custom CameraX preview - see
    // ANDROID_DESIGN_BRIEF.md; no CAMERA permission needed since the stock
    // camera app owns the capture, we only receive the resulting file.
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { captured ->
        val uri = pendingPhotoUri
        if (captured && uri != null) onPhotoScanned(uri)
    }

    // The Android Photo Picker - no storage permission needed on any API
    // level. Most scans are of a document (a scale ticket especially)
    // photographed well before opening the app, so "choose an existing
    // photo" is the common case, not "take one right now".
    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) onPhotoScanned(uri)
    }

    fun launchCamera() {
        val uri = createScanPhotoUri(context)
        pendingPhotoUri = uri
        cameraLauncher.launch(uri)
    }

    fun launchGallery() {
        galleryLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            // At a large font the chip goes to a row of its own under the title (resize-rules.md).
            val chipBelow = chipBelowTitle()
            val chip: @Composable (Modifier) -> Unit = { modifier ->
                CreditBalanceChip(
                    balance = creditBalance,
                    signedOut = signedOut,
                    modifier = modifier.testTag(UiTags.CHOOSER_CREDIT_CHIP),
                    onClick = onOpenPaywall,
                )
            }
            RigCheckTopBar(
                title = copy.title,
                onBack = onBack,
                backEnabled = scanState !is ScanUiState.Loading,
                titleModifier = Modifier.testTag(UiTags.CHOOSER_TITLE),
                backModifier = Modifier.testTag(UiTags.CHOOSER_BACK),
                end = { if (!chipBelow) chip(Modifier) },
                below = {
                    if (chipBelow) chip(Modifier.align(Alignment.End))
                    RigCheckStepIndicator(step = module.ordinal + 1, modifier = Modifier.testTag(UiTags.CHOOSER_STEP_BAR))
                },
            )

            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 24.dp),
            ) {
                Text(
                    copy.prompt,
                    style = RigCheckStyles.titleLg,
                    color = Ink,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.CHOOSER_PROMPT),
                )
                RigCheckOptionCard(
                    kind = RigCheckOptionKind.Scan,
                    title = "Scan Photo",
                    description = "Photograph the label — Claude reads the fields for you.",
                    icon = Icons.Filled.CameraAlt,
                    onClick = {
                        if (canStartScan(creditBalance)) {
                            showSourceDialog = true
                        } else {
                            onNeedCredits()
                        }
                    },
                    modifier = Modifier.testTag(UiTags.CHOOSER_SCAN_CARD),
                    badge = {
                        RigCheckBadge("1 credit", RigCheckBadgeKind.Credit, modifier = Modifier.testTag(UiTags.CHOOSER_SCAN_BADGE))
                    },
                )
                RigCheckOptionCard(
                    kind = RigCheckOptionKind.Manual,
                    title = "Enter Manually",
                    description = "Type the values in yourself — free, no photo, works offline.",
                    icon = Icons.Filled.Keyboard,
                    onClick = onChooseManual,
                    modifier = Modifier.testTag(UiTags.CHOOSER_MANUAL_CARD),
                    badge = {
                        RigCheckBadge("Free", RigCheckBadgeKind.Free, modifier = Modifier.testTag(UiTags.CHOOSER_MANUAL_BADGE))
                    },
                )
                RigCheckNoticeCard(
                    text = "This same choice appears again before the trailer tag and scale ticket screens.",
                    tone = RigCheckNoticeTone.Info,
                    textModifier = Modifier.testTag(UiTags.CHOOSER_FOOTER_NOTE),
                )
            }
        }

        if (scanState is ScanUiState.Loading) {
            // Absorbs taps (#118): without a pointer handler a Box lets them through
            // to the buttons under it, so a second Scan, or manual entry with the
            // first still out, could be started behind the spinner. It covers the top bar
            // too, so Back and the balance chip are shut as well.
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterVertically),
                modifier = Modifier
                    .fillMaxSize()
                    .background(SurfaceWhite.copy(alpha = Opacity.ScanOverlayWash))
                    .pointerInput(Unit) { detectTapGestures { } }
                    .testTag(UiTags.CHOOSER_LOADING_OVERLAY),
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(48.dp),
                    color = TealDeep,
                    trackColor = Border,
                    strokeWidth = 4.dp,
                )
                Text(
                    "Reading…",
                    style = RigCheckStyles.titleLg.copy(fontSize = 20.sp, lineHeight = 24.sp),
                    color = Ink,
                    modifier = Modifier.testTag(UiTags.CHOOSER_LOADING_TEXT),
                )
            }
        }
    }

    if (showSourceDialog) {
        PhotoSourceDialog(
            onDismiss = { showSourceDialog = false },
            onTakePhoto = ::launchCamera,
            onChooseFromGallery = ::launchGallery,
        )
    }

    if (scanState is ScanUiState.Error) {
        ScanErrorDialog(
            scanState,
            onDismiss = onDismissScanError,
            // A different photo is picked here, on this screen: close the error
            // and start a Scan the way the Scan Photo button does (the photo
            // source choice, or the paywall with no balance left).
            // Typing the numbers in goes straight to manual entry for this
            // document, the same place the Enter Manually card goes.
            onNextStep = { step ->
                when (step) {
                    ScanNextStep.CHOOSE_DIFFERENT_PHOTO -> {
                        onDismissScanError()
                        if (canStartScan(creditBalance)) showSourceDialog = true else onNeedCredits()
                    }
                    ScanNextStep.TYPE_IT_IN -> {
                        onDismissScanError()
                        onChooseManual()
                    }
                    else -> onScanErrorNextStep(step)
                }
            },
        )
    }
}
