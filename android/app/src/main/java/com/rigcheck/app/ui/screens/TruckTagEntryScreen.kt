package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.data.createScanPhotoUri
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.ReferenceImageCard
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

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Truck Tag", style = MaterialTheme.typography.headlineMedium)
        Text("Step 1 of 3", style = MaterialTheme.typography.bodySmall)

        Text(
            "Find these values on your truck's compliance label (usually inside the driver door jamb).",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp),
        )

        ReferenceImageCard(
            imageRes = R.drawable.ref_truck_tag,
            contentDescription = "Truck compliance label",
        )

        Text(
            "Hover a field to zoom in on its spot on the tag",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(vertical = 8.dp),
        )

        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            LabeledTextField(
                label = "Description",
                value = truck.description ?: "",
                onValueChange = { onTruckChange(truck.copy(description = it.ifBlank { null })) },
                placeholder = "e.g. Ford F-450",
                modifier = Modifier.testTag("truck_description"),
            )
            LabeledTextField(
                label = "Name",
                value = truck.name ?: "",
                onValueChange = { onTruckChange(truck.copy(name = it.ifBlank { null })) },
            )
            LabeledNumberField(
                label = "GVWR, lb",
                value = truck.gvwrLb,
                onValueChange = { onTruckChange(truck.copy(gvwrLb = it)) },
            )
            LabeledNumberField(
                label = "Front GAWR, lb",
                value = truck.frontGawrLb,
                onValueChange = { onTruckChange(truck.copy(frontGawrLb = it)) },
            )
            LabeledNumberField(
                label = "Rear GAWR, lb",
                value = truck.rearGawrLb,
                onValueChange = { onTruckChange(truck.copy(rearGawrLb = it)) },
            )
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Stand-alone weight, lb — optional",
                        style = MaterialTheme.typography.labelLarge,
                    )
                    Icon(
                        Icons.Filled.Info,
                        contentDescription = "More info",
                        modifier = Modifier
                            .padding(start = 4.dp)
                            .clickable { showStandaloneInfo = !showStandaloneInfo },
                    )
                }
                if (showStandaloneInfo) {
                    Text(
                        "If left blank, we'll assume the trailer axle reading is 80% of the " +
                            "trailer's total weight. Fill this in for a more accurate tongue-weight " +
                            "estimate.",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
                LabeledNumberField(
                    label = "",
                    value = truck.standaloneWeightLb,
                    onValueChange = { onTruckChange(truck.copy(standaloneWeightLb = it)) },
                )
            }

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.shapes.medium)
                    .padding(16.dp),
            ) {
                Text(
                    "Don't know your tow vehicle's stand-alone weight?",
                    style = MaterialTheme.typography.labelLarge,
                )
                Text(
                    "Scan a CAT Scale ticket weighing just your tow vehicle (no trailer attached) " +
                        "and we'll fill in the field above for you.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
                )
                OutlinedButton(
                    onClick = { showStandaloneSourceDialog = true },
                    modifier = Modifier.testTag("scan_standalone_ticket"),
                ) {
                    Text(if (scanState is ScanUiState.Loading) "Reading…" else "Scan tow-vehicle-only ticket")
                }

                if (truck.standaloneWeightLb == null) {
                    Column(modifier = Modifier.padding(top = 16.dp)) {
                        Text(
                            "No ticket? Estimate pin/hitch weight as $pinWeightPct% of the trailer's weight",
                            style = MaterialTheme.typography.labelLarge,
                        )
                        Slider(
                            value = pinWeightPct.toFloat(),
                            onValueChange = { onPinWeightPctChange(it.roundToInt()) },
                            valueRange = 15f..25f,
                            steps = 9,
                            modifier = Modifier.testTag("pin_weight_pct_slider"),
                        )
                        Text(
                            "Industry recommendations are typically 15-25% — we default to 20%.",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
        ) { Text("Next: Trailer Tag") }
    }

    if (showStandaloneSourceDialog) {
        AlertDialog(
            onDismissRequest = { showStandaloneSourceDialog = false },
            title = { Text("Scan Photo") },
            text = { Text("Take a new photo, or choose one you already have?") },
            confirmButton = {
                TextButton(onClick = {
                    showStandaloneSourceDialog = false
                    galleryLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                }) { Text("Choose from Gallery") }
            },
            dismissButton = {
                TextButton(onClick = {
                    showStandaloneSourceDialog = false
                    val uri = createScanPhotoUri(context)
                    pendingPhotoUri = uri
                    cameraLauncher.launch(uri)
                }) { Text("Take Photo") }
            },
        )
    }

    if (scanState is ScanUiState.Error) {
        AlertDialog(
            onDismissRequest = onDismissStandaloneScanError,
            confirmButton = { TextButton(onClick = onDismissStandaloneScanError) { Text("OK") } },
            title = { Text("Scan failed") },
            text = { Text(scanState.message) },
        )
    }
}
