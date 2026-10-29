package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.outlined.Info
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.data.createScanPhotoUri
import com.rigcheck.app.domain.gcwrBelowGvwr
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.canStartScan
import com.rigcheck.app.ui.components.CreditBalanceChip
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.PhotoSourceDialog
import com.rigcheck.app.ui.components.PinnedReferenceCard
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckButtonKind
import com.rigcheck.app.ui.components.RigCheckButtonSize
import com.rigcheck.app.ui.components.RigCheckIconButton
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckSlider
import com.rigcheck.app.ui.components.ScanErrorDialog
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.OrangeDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.TealDeep
import com.rigcheck.app.ui.theme.TintOrange
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite
import kotlin.math.roundToInt

@Composable
fun TruckTagEntryScreen(
    truck: TruckTag,
    onTruckChange: (TruckTag) -> Unit,
    onContinue: () -> Unit,
    pinWeightPct: Int = 20,
    onPinWeightPctChange: (Int) -> Unit = {},
    scanState: ScanUiState = ScanUiState.Idle,
    onScanStandaloneTicket: (Uri) -> Unit = {},
    onDismissStandaloneScanError: () -> Unit = {},
    creditBalance: Int? = null,
    // Whether the account is signed out: then the balance chip says "0 scans", not "…".
    signedOut: Boolean = false,
    onNeedCredits: () -> Unit = {},
    onOpenPaywall: () -> Unit = {},
    onScanErrorNextStep: (ScanNextStep) -> Unit = {},
    scanNotice: ScanNotice? = null,
    // The top bar's Back. It is disabled while the stand-alone Scan is out.
    onBack: () -> Unit = {},
) {
    var showStandaloneInfo by remember { mutableStateOf(false) }
    var showStandaloneSourceDialog by remember { mutableStateOf(false) }
    val context = LocalContext.current
    var pendingPhotoUri by remember { mutableStateOf<Uri?>(null) }

    // Same system-camera-intent / Android Photo Picker pattern as
    // ChooserScreen - this entry point isn't reached through the normal
    // Chooser flow (the truck tag itself may have been entered manually),
    // so it needs its own launchers rather than reusing ChooserScreen's.
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { captured ->
        val uri = pendingPhotoUri
        if (captured && uri != null) onScanStandaloneTicket(uri)
    }
    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) onScanStandaloneTicket(uri)
    }

    EntryScreenFrame(
        title = "Truck Tag",
        step = 1,
        onBack = onBack,
        backEnabled = scanState !is ScanUiState.Loading,
        titleModifier = Modifier.testTag(UiTags.TRUCK_TITLE),
        backModifier = Modifier.testTag(UiTags.TRUCK_BACK),
        stepModifier = Modifier.testTag(UiTags.TRUCK_STEP_BAR),
        chip = { modifier ->
            CreditBalanceChip(
                balance = creditBalance,
                signedOut = signedOut,
                modifier = modifier.testTag(UiTags.TRUCK_CREDIT_CHIP),
                onClick = onOpenPaywall,
            )
        },
        reference = { compact ->
            PinnedReferenceCard(
                imageRes = R.drawable.ref_truck_tag,
                imageDescription = "Truck compliance label",
                hint = "Tap a field to see its spot on the tag",
                compact = compact,
                hintModifier = Modifier.testTag(UiTags.TRUCK_REFERENCE_HINT),
                imageModifier = Modifier.testTag(UiTags.TRUCK_REFERENCE_IMAGE),
            )
        },
        footer = {
            RigCheckButton(
                text = "Next: Trailer Tag",
                onClick = onContinue,
                icon = Icons.AutoMirrored.Filled.ArrowForward,
                modifier = Modifier.testTag(UiTags.TRUCK_NEXT_BUTTON),
            )
        },
    ) {
        scanNotice?.textFor(truck)?.let { text ->
            RigCheckNoticeCard(text = text, tone = RigCheckNoticeTone.Scan, modifier = Modifier.testTag(UiTags.SCAN_NOTICE))
        }

        Text(
            "Find these values on your truck's compliance label (usually inside the driver door jamb).",
            style = RigCheckStyles.body,
            color = InkMuted,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.TRUCK_INSTRUCTIONS),
        )

        LabeledTextField(
            label = "Description",
            value = truck.description ?: "",
            onValueChange = { onTruckChange(truck.copy(description = it.ifBlank { null })) },
            placeholder = "e.g. Ford F-450",
            modifier = Modifier.testTag(UiTags.TRUCK_DESCRIPTION),
        )
        LabeledTextField(
            label = "Name",
            value = truck.name ?: "",
            onValueChange = { onTruckChange(truck.copy(name = it.ifBlank { null })) },
            modifier = Modifier.testTag(UiTags.TRUCK_NAME_FIELD),
        )
        LabeledNumberField(
            label = "GVWR, lb",
            value = truck.gvwrLb,
            onValueChange = { onTruckChange(truck.copy(gvwrLb = it)) },
            unit = "lb",
            modifier = Modifier.testTag(UiTags.TRUCK_GVWR_FIELD),
        )
        LabeledNumberField(
            label = "Front GAWR, lb",
            value = truck.frontGawrLb,
            onValueChange = { onTruckChange(truck.copy(frontGawrLb = it)) },
            unit = "lb",
            modifier = Modifier.testTag(UiTags.TRUCK_FRONT_GAWR_FIELD),
        )
        LabeledNumberField(
            label = "Rear GAWR, lb",
            value = truck.rearGawrLb,
            onValueChange = { onTruckChange(truck.copy(rearGawrLb = it)) },
            unit = "lb",
            modifier = Modifier.testTag(UiTags.TRUCK_REAR_GAWR_FIELD),
        )
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            LabeledNumberField(
                label = "GCWR, lb",
                value = truck.gcwrLb,
                onValueChange = { onTruckChange(truck.copy(gcwrLb = it)) },
                optionalHint = "optional",
                unit = "lb",
                help = "From your owner's manual. Leave blank if you can't find it.",
                helpModifier = Modifier.testTag(UiTags.TRUCK_GCWR_HELP),
                modifier = Modifier.testTag(UiTags.TRUCK_GCWR),
            )
            if (gcwrBelowGvwr(truck)) {
                // A warning, not a block: the value is kept. In words and in orange-deep, so not colour alone.
                Text(
                    "This is lower than your GVWR. Check it against your owner's manual. " +
                        "We'll still use it.",
                    style = RigCheckStyles.caption.copy(fontWeight = FontWeight.Medium),
                    color = OrangeDeep,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.TRUCK_GCWR_WARNING),
                )
            }
        }

        Column(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier
                .testTag(UiTags.TRUCK_STANDALONE_PANEL)
                .fillMaxWidth()
                .background(TintOrange, RoundedCornerShape(Radii.Panel))
                .padding(16.dp),
        ) {
            Text(
                "Don't know your tow vehicle's stand-alone weight?",
                style = RigCheckStyles.title,
                color = OrangeDeep,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.TRUCK_STANDALONE_PANEL_TITLE),
            )
            Text(
                "Scan a CAT Scale ticket weighing just your tow vehicle (no trailer attached) " +
                    "and we'll fill in the field above for you.",
                style = RigCheckStyles.bodySm,
                color = InkMuted,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.TRUCK_STANDALONE_PANEL_BODY),
            )
            RigCheckButton(
                text = if (scanState is ScanUiState.Loading) "Reading…" else "Scan tow-vehicle-only ticket",
                // Same gate as the main Scan Photo button: no balance above
                // zero (signed out, or none left) goes to the paywall, which
                // asks for sign-in first - before any photo is taken.
                onClick = { if (canStartScan(creditBalance)) showStandaloneSourceDialog = true else onNeedCredits() },
                kind = RigCheckButtonKind.Secondary,
                size = RigCheckButtonSize.Dialog,
                icon = Icons.Filled.CameraAlt,
                // Off while it reads (#118): a second tap would send a second Scan.
                enabled = scanState !is ScanUiState.Loading,
                modifier = Modifier.testTag(UiTags.SCAN_STANDALONE_TICKET),
            )

            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Stand-alone weight, lb — optional",
                        style = RigCheckStyles.label,
                        color = Ink,
                        modifier = Modifier.weight(1f).testTag(UiTags.TRUCK_STANDALONE_LABEL),
                    )
                    // The 48 dp target the design asks for (it was a 24 dp icon).
                    RigCheckIconButton(
                        icon = Icons.Outlined.Info,
                        contentDescription = "What is stand-alone weight?",
                        onClick = { showStandaloneInfo = !showStandaloneInfo },
                        glyphTint = TealDeep,
                        modifier = Modifier.testTag(UiTags.TRUCK_STANDALONE_INFO),
                    )
                }
                if (showStandaloneInfo) {
                    Text(
                        "If left blank, we'll assume the trailer axle reading is 80% of the " +
                            "trailer's total weight. Fill this in for a more accurate pin-weight " +
                            "estimate.",
                        style = RigCheckStyles.caption,
                        color = Ink,
                        modifier = Modifier
                            .testTag(UiTags.TRUCK_STANDALONE_INFO_TEXT)
                            .fillMaxWidth()
                            .background(SurfaceWhite, RoundedCornerShape(Radii.Input))
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                    )
                }
                LabeledNumberField(
                    label = null,
                    value = truck.standaloneWeightLb,
                    onValueChange = { onTruckChange(truck.copy(standaloneWeightLb = it)) },
                    unit = "lb",
                    modifier = Modifier.testTag(UiTags.TRUCK_STANDALONE_FIELD),
                )
            }

            if (truck.standaloneWeightLb == null) {
                Text(
                    "No ticket? Estimate pin/hitch weight as $pinWeightPct% of the trailer's weight",
                    style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Medium),
                    color = Ink,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.TRUCK_PIN_WEIGHT_LABEL),
                )
                RigCheckSlider(
                    value = pinWeightPct.toFloat(),
                    onValueChange = { onPinWeightPctChange(it.roundToInt()) },
                    valueRange = 15f..25f,
                    steps = 9,
                    contentDescription = "Pin weight, percent of trailer weight",
                    modifier = Modifier.testTag(UiTags.PIN_WEIGHT_PCT_SLIDER),
                )
                Text(
                    "Industry recommendations are typically 15-25% — we default to 20%.",
                    style = RigCheckStyles.micro,
                    color = InkMuted,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.TRUCK_PIN_WEIGHT_CAPTION),
                )
            }
        }
    }

    if (showStandaloneSourceDialog) {
        PhotoSourceDialog(
            onDismiss = { showStandaloneSourceDialog = false },
            onTakePhoto = {
                val uri = createScanPhotoUri(context)
                pendingPhotoUri = uri
                cameraLauncher.launch(uri)
            },
            onChooseFromGallery = {
                galleryLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            },
        )
    }

    if (scanState is ScanUiState.Error) {
        ScanErrorDialog(
            scanState,
            onDismiss = onDismissStandaloneScanError,
            // A different photo is picked here, on this screen, behind the same
            // gate as the Scan button (the answer just charged a Scan, so the
            // balance may be 0 now); typing the weight in is the field above,
            // so closing the error leaves the user at it.
            onNextStep = { step ->
                when (step) {
                    ScanNextStep.CHOOSE_DIFFERENT_PHOTO -> {
                        onDismissStandaloneScanError()
                        if (canStartScan(creditBalance)) showStandaloneSourceDialog = true else onNeedCredits()
                    }
                    ScanNextStep.TYPE_IT_IN -> onDismissStandaloneScanError()
                    else -> onScanErrorNextStep(step)
                }
            },
        )
    }
}
