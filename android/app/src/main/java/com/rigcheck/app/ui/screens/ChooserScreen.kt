package com.rigcheck.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.rigcheck.app.data.createScanPhotoUri
import com.rigcheck.app.ui.ScanUiState
import com.rigcheck.app.ui.components.CreditBalanceChip
import com.rigcheck.app.ui.components.ScanOrManualChooser
import com.rigcheck.app.ui.navigation.EntryModule

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
    scanState: ScanUiState,
    onChooseManual: () -> Unit,
    onPhotoScanned: (Uri) -> Unit,
    onNeedCredits: () -> Unit,
    onOpenPaywall: () -> Unit,
    onDismissScanError: () -> Unit,
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
        Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
            Text(copy.title, style = MaterialTheme.typography.headlineMedium)
            CreditBalanceChip(
                balance = creditBalance,
                modifier = Modifier.padding(top = 12.dp),
                onClick = onOpenPaywall,
            )
            Text(
                copy.prompt,
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.padding(top = 16.dp, bottom = 16.dp),
            )
            ScanOrManualChooser(
                onScanPhoto = {
                    if ((creditBalance ?: 0) > 0) {
                        showSourceDialog = true
                    } else {
                        onNeedCredits()
                    }
                },
                onChooseManual = onChooseManual,
            )
            Text(
                "This same choice appears again before the trailer tag and scale ticket screens.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 16.dp),
            )
        }

        if (scanState is ScanUiState.Loading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.scrim.copy(alpha = 0.3f)),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator()
            }
        }
    }

    if (showSourceDialog) {
        AlertDialog(
            onDismissRequest = { showSourceDialog = false },
            title = { Text("Scan Photo") },
            text = { Text("Take a new photo, or choose one you already have?") },
            confirmButton = {
                TextButton(onClick = {
                    showSourceDialog = false
                    launchGallery()
                }) { Text("Choose from Gallery") }
            },
            dismissButton = {
                TextButton(onClick = {
                    showSourceDialog = false
                    launchCamera()
                }) { Text("Take Photo") }
            },
        )
    }

    if (scanState is ScanUiState.Error) {
        AlertDialog(
            onDismissRequest = onDismissScanError,
            confirmButton = { TextButton(onClick = onDismissScanError) { Text("OK") } },
            title = { Text("Scan failed") },
            text = { Text(scanState.message) },
        )
    }
}
