package com.rigcheck.app.ui.experiments.cameraoverlay

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.FileOutputStream

// Major/instrumented regression test for the real EXIF-orientation bug
// found while spiking item #18 (ClaudePlans/2026-08-27-android-camera-overlay-
// spike-results.md, finding #2): CameraX's ImageCapture signals rotation
// only via EXIF, but production's encodePhotoForScan (PhotoEncoding.kt)
// decodes with plain BitmapFactory, which ignores EXIF entirely - an
// unrotated capture would have been saved sideways. normalizeExifOrientation()
// fixes this by baking the rotation into the pixels right after capture.
// This needs real android.graphics/ExifInterface behavior (no Robolectric
// in this project), so it runs on the emulator, not as a Minor/JVM test -
// no live camera or physical device involved, just a synthesized JPEG with
// a known EXIF tag.
@RunWith(AndroidJUnit4::class)
class CameraOverlaySpikeExifTest {

    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    @Test
    fun rotate90ExifOrientation_bakesRotationIntoPixelsAndClearsTheTag() {
        // 20x10 (width != height, so a 90-degree rotation is unambiguously
        // detectable by dimension swap alone) - left half red, right half
        // blue, so a content-level rotation check would also be possible
        // if ever needed, though dimension swap is the primary assertion.
        val file = writeTestJpeg(width = 20, height = 10, orientation = ExifInterface.ORIENTATION_ROTATE_90)
        val uri = Uri.fromFile(file)

        normalizeExifOrientation(context, uri)

        val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.absolutePath, options)
        assertEquals("width after a baked-in 90-degree rotation", 10, options.outWidth)
        assertEquals("height after a baked-in 90-degree rotation", 20, options.outHeight)

        // Bitmap.compress() writes a fresh JPEG with no orientation tag
        // (real result, confirmed by running this: reads back as
        // ORIENTATION_UNDEFINED=0, not ORIENTATION_NORMAL=1 as originally
        // assumed here) - both mean "apply no further rotation," which is
        // the actual property that matters: a second EXIF-aware decoder
        // downstream must not double-rotate this file.
        val exifAfter = ExifInterface(file.absolutePath)
            .getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        val nonRotatingValues = setOf(ExifInterface.ORIENTATION_NORMAL, ExifInterface.ORIENTATION_UNDEFINED)
        assertTrue(
            "EXIF orientation must not indicate further rotation is needed after normalization " +
                "(was $exifAfter) - otherwise a second EXIF-aware decoder downstream would double-rotate it",
            exifAfter in nonRotatingValues,
        )
    }

    @Test
    fun normalOrientation_isLeftUntouched() {
        val file = writeTestJpeg(width = 20, height = 10, orientation = ExifInterface.ORIENTATION_NORMAL)
        val uri = Uri.fromFile(file)

        normalizeExifOrientation(context, uri)

        val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.absolutePath, options)
        assertEquals("width must be unchanged when no rotation was needed", 20, options.outWidth)
        assertEquals("height must be unchanged when no rotation was needed", 10, options.outHeight)
    }

    private fun writeTestJpeg(width: Int, height: Int, orientation: Int): File {
        val dir = File(context.cacheDir, "exif_test").apply { mkdirs() }
        val file = File(dir, "exif_test_${System.nanoTime()}.jpg")

        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        for (x in 0 until width) {
            for (y in 0 until height) {
                bitmap.setPixel(x, y, if (x < width / 2) Color.RED else Color.BLUE)
            }
        }
        FileOutputStream(file).use { out -> bitmap.compress(Bitmap.CompressFormat.JPEG, 95, out) }

        if (orientation != ExifInterface.ORIENTATION_NORMAL) {
            val exif = ExifInterface(file.absolutePath)
            exif.setAttribute(ExifInterface.TAG_ORIENTATION, orientation.toString())
            exif.saveAttributes()
        }
        return file
    }
}
