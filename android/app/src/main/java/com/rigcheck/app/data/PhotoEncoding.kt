package com.rigcheck.app.data

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import java.io.ByteArrayOutputStream

// Same rationale/parameters as the reference-image resize done for Phase 3
// (android/app/src/main/res/drawable/ref_*.jpg): NEXT_STEPS.md's
// $0.01-0.03/scan cost baseline assumes "standard resolution" (~1,600
// image tokens); an un-downscaled modern phone photo is well above that.
private const val MAX_LONG_EDGE_PX = 1600
private const val JPEG_QUALITY = 85

// Downscales and JPEG-encodes a captured photo, returning it as a base64
// string ready for ScanApiClient's image_base64 field.
fun encodePhotoForScan(contentResolver: ContentResolver, uri: Uri): String {
    val original = contentResolver.openInputStream(uri).use { input ->
        BitmapFactory.decodeStream(input)
    } ?: error("Could not decode the captured photo.")

    val longEdge = maxOf(original.width, original.height)
    val resized = if (longEdge > MAX_LONG_EDGE_PX) {
        val scale = MAX_LONG_EDGE_PX.toFloat() / longEdge
        Bitmap.createScaledBitmap(
            original,
            (original.width * scale).toInt(),
            (original.height * scale).toInt(),
            true,
        )
    } else {
        original
    }

    val outputStream = ByteArrayOutputStream()
    resized.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, outputStream)
    return Base64.encodeToString(outputStream.toByteArray(), Base64.NO_WRAP)
}
