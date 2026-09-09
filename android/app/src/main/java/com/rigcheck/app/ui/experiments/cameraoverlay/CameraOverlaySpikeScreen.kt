package com.rigcheck.app.ui.experiments.cameraoverlay

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import android.util.Log
import android.view.Surface
import android.view.View
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.exifinterface.media.ExifInterface
import com.rigcheck.app.data.createScanPhotoUri
import com.rigcheck.app.data.encodePhotoForScan
import com.rigcheck.app.ui.theme.SunsetOrange
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.File

private const val TAG = "CameraOverlaySpike"

// Approximates a compliance-tag/data-plate's real proportions using the
// app's own reference photo (ref_truck_tag.jpg is 1600x721px, ~2.22:1) -
// see ClaudePlans/2026-08-27-android-camera-overlay-spike.md.
private const val GUIDE_ASPECT_RATIO = 1600f / 721f
private const val GUIDE_FRACTION = 0.85f
private val guideCornerRadius = 14.dp
private val guideStrokeWidth = 4.dp

@Composable
fun CameraOverlaySpikeScreen() {
    val context = LocalContext.current
    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED,
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> hasPermission = granted }

    LaunchedEffect(Unit) {
        if (!hasPermission) permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    if (hasPermission) {
        CameraPreviewWithOverlay()
    } else {
        PermissionRationale(onRequest = { permissionLauncher.launch(Manifest.permission.CAMERA) })
    }
}

@Composable
private fun PermissionRationale(onRequest: () -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(24.dp),
        ) {
            Text(
                "Camera permission is needed for this spike screen.",
                style = MaterialTheme.typography.bodyLarge,
            )
            Button(onClick = onRequest, modifier = Modifier.padding(top = 16.dp)) {
                Text("Grant Camera Permission")
            }
        }
    }
}

@Composable
private fun CameraPreviewWithOverlay() {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val previewView = remember {
        PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER }
    }
    val imageCapture = remember { ImageCapture.Builder().build() }
    var statusText by remember { mutableStateOf("Starting camera...") }
    var lastCapturedUri by remember { mutableStateOf<Uri?>(null) }

    LaunchedEffect(Unit) {
        try {
            // Real gotcha found while spiking this: binding Preview before
            // previewView is attached to a window leaves its target rotation
            // stuck at the value captured at construction time, so the
            // sensor image can come out rotated relative to the UI after an
            // orientation change even though the Activity (and this whole
            // Composable) is freshly recreated. Waiting for attachment
            // first, like CameraX's own PreviewView, guarantees a real
            // display/rotation is available before Preview.Builder() runs.
            awaitViewAttached(previewView)
            val cameraProvider = awaitCameraProvider(context)
            val rotation = previewView.display?.rotation ?: Surface.ROTATION_0
            val preview = Preview.Builder()
                .setTargetRotation(rotation)
                .build()
                .also { it.surfaceProvider = previewView.surfaceProvider }
            imageCapture.targetRotation = rotation
            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(
                lifecycleOwner,
                CameraSelector.DEFAULT_BACK_CAMERA,
                preview,
                imageCapture,
            )
            statusText = "Preview live"
            Log.d(TAG, "Camera bound successfully (targetRotation=$rotation)")
        } catch (e: Exception) {
            statusText = "Camera bind failed: ${e.message}"
            Log.e(TAG, "Camera bind failed", e)
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

        Canvas(modifier = Modifier.fillMaxSize()) {
            val maxWidth = size.width * GUIDE_FRACTION
            val maxHeight = size.height * GUIDE_FRACTION
            val widthIfBoundByWidth = maxWidth
            val heightIfBoundByWidth = maxWidth / GUIDE_ASPECT_RATIO
            val (guideWidth, guideHeight) = if (heightIfBoundByWidth <= maxHeight) {
                widthIfBoundByWidth to heightIfBoundByWidth
            } else {
                (maxHeight * GUIDE_ASPECT_RATIO) to maxHeight
            }
            val left = (size.width - guideWidth) / 2f
            val top = (size.height - guideHeight) / 2f
            drawRoundRect(
                color = SunsetOrange,
                topLeft = Offset(left, top),
                size = Size(guideWidth, guideHeight),
                cornerRadius = CornerRadius(guideCornerRadius.toPx(), guideCornerRadius.toPx()),
                style = Stroke(width = guideStrokeWidth.toPx()),
            )
        }

        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                statusText,
                color = Color.White,
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(
                onClick = {
                    capturePhoto(context, imageCapture) { result ->
                        result.onSuccess { uri ->
                            lastCapturedUri = uri
                            statusText = describeCapturedFile(context, uri)
                            Log.d(TAG, "Capture succeeded: $uri")
                        }.onFailure { error ->
                            statusText = "Capture failed: ${error.message}"
                            Log.e(TAG, "Capture failed", error)
                        }
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = SunsetOrange),
            ) {
                Text("Capture")
            }
            if (lastCapturedUri != null) {
                Button(
                    onClick = {
                        statusText = runPipelineCheck(context, lastCapturedUri!!)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = SunsetOrange),
                ) {
                    Text("Verify via encodePhotoForScan")
                }
            }
        }
    }
}

// Real drop-in-compatibility check for plan step 4: runs the actual
// production encodePhotoForScan against the spike's captured file, then
// decodes the resulting base64 back to a bitmap and writes it next to the
// original so it can be pulled off-device and inspected visually (this is
// how a real EXIF-orientation mismatch between CameraX's sensor-native
// output and BitmapFactory's non-EXIF-aware decode would show up).
private fun runPipelineCheck(context: Context, uri: Uri): String = try {
    val base64 = encodePhotoForScan(context.contentResolver, uri)
    val decodedBytes = android.util.Base64.decode(base64, android.util.Base64.NO_WRAP)
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.size, options)
    val checkFile = File(File(context.cacheDir, "scan_photos"), "pipeline_check.jpg")
    checkFile.writeBytes(decodedBytes)
    Log.d(TAG, "Pipeline check wrote ${decodedBytes.size} bytes to $checkFile")
    "encodePhotoForScan OK: ${options.outWidth}x${options.outHeight}px, " +
        "${decodedBytes.size} b64-decoded bytes -> $checkFile"
} catch (e: Exception) {
    Log.e(TAG, "Pipeline check failed", e)
    "encodePhotoForScan FAILED: ${e.message}"
}

// Suspends until the given View is actually attached to a window - needed
// before reading View.display, which can otherwise be null (or stale)
// during the first composition pass.
private suspend fun awaitViewAttached(view: View) {
    if (view.isAttachedToWindow) return
    suspendCancellableCoroutine<Unit> { continuation ->
        val listener = object : View.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(v: View) {
                view.removeOnAttachStateChangeListener(this)
                continuation.resumeWith(Result.success(Unit))
            }

            override fun onViewDetachedFromWindow(v: View) = Unit
        }
        view.addOnAttachStateChangeListener(listener)
        continuation.invokeOnCancellation { view.removeOnAttachStateChangeListener(listener) }
    }
}

// Bridges CameraX's ListenableFuture-based API (no kotlinx-coroutines-guava
// dependency in this project) to a plain suspend call.
private suspend fun awaitCameraProvider(context: Context): ProcessCameraProvider =
    suspendCancellableCoroutine { continuation ->
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener(
            { continuation.resumeWith(Result.success(future.get())) },
            ContextCompat.getMainExecutor(context),
        )
    }

// Saves to the same kind of Uri/file ChooserScreen's system-camera-intent
// flow already produces (createScanPhotoUri), so downstream code
// (encodePhotoForScan, ScanApiClient) needs no changes.
private fun capturePhoto(
    context: Context,
    imageCapture: ImageCapture,
    onResult: (Result<Uri>) -> Unit,
) {
    val uri = createScanPhotoUri(context)
    val outputStream = context.contentResolver.openOutputStream(uri)
    if (outputStream == null) {
        onResult(Result.failure(IllegalStateException("Could not open output stream for $uri")))
        return
    }
    val outputOptions = ImageCapture.OutputFileOptions.Builder(outputStream).build()
    imageCapture.takePicture(
        outputOptions,
        ContextCompat.getMainExecutor(context),
        object : ImageCapture.OnImageSavedCallback {
            override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                try {
                    normalizeExifOrientation(context, uri)
                    onResult(Result.success(uri))
                } catch (e: Exception) {
                    onResult(Result.failure(e))
                }
            }

            override fun onError(exc: ImageCaptureException) {
                onResult(Result.failure(exc))
            }
        },
    )
}

// Real bug found while spiking this: CameraX's ImageCapture saves the
// sensor-native pixel buffer and signals the needed rotation only via the
// JPEG's EXIF orientation tag (e.g. 6 = rotate 90 for a portrait capture).
// The existing production encodePhotoForScan (PhotoEncoding.kt) decodes
// with plain BitmapFactory, which does not consult EXIF at all - so a
// portrait-held capture came out sideways after the real pipeline,
// confirmed visually via the "Verify via encodePhotoForScan" button below.
// Baking the rotation into the pixels immediately after capture (as the
// stock camera app effectively already does before handing off to
// ChooserScreen) makes this spike's output byte-for-byte compatible with
// the existing pipeline without touching any production file.
private fun normalizeExifOrientation(context: Context, uri: Uri) {
    val orientation = context.contentResolver.openInputStream(uri)?.use { input ->
        ExifInterface(input).getAttributeInt(
            ExifInterface.TAG_ORIENTATION,
            ExifInterface.ORIENTATION_NORMAL,
        )
    } ?: ExifInterface.ORIENTATION_NORMAL
    if (orientation == ExifInterface.ORIENTATION_NORMAL) return

    val rotationDegrees = when (orientation) {
        ExifInterface.ORIENTATION_ROTATE_90 -> 90f
        ExifInterface.ORIENTATION_ROTATE_180 -> 180f
        ExifInterface.ORIENTATION_ROTATE_270 -> 270f
        else -> 0f
    }
    if (rotationDegrees == 0f) return

    val original = context.contentResolver.openInputStream(uri)?.use { input ->
        BitmapFactory.decodeStream(input)
    } ?: return
    val rotated = Bitmap.createBitmap(
        original,
        0,
        0,
        original.width,
        original.height,
        Matrix().apply { postRotate(rotationDegrees) },
        true,
    )
    context.contentResolver.openOutputStream(uri, "wt")?.use { output ->
        rotated.compress(Bitmap.CompressFormat.JPEG, 95, output)
    }
    Log.d(TAG, "Normalized EXIF orientation $orientation ($rotationDegrees deg) for $uri")
}

// On-screen confirmation of decodable-JPEG + dimensions, so manual
// verification doesn't require pulling the file off-device via adb.
private fun describeCapturedFile(context: Context, uri: Uri): String {
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    context.contentResolver.openInputStream(uri).use { input ->
        BitmapFactory.decodeStream(input, null, options)
    }
    val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }?.size ?: -1
    return if (options.outWidth > 0) {
        "Captured: ${options.outWidth}x${options.outHeight}px, $bytes bytes, mime=${options.outMimeType}"
    } else {
        "Captured file did not decode as an image ($bytes bytes)"
    }
}
