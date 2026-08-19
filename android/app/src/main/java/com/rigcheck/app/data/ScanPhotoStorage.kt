package com.rigcheck.app.data

import android.content.Context
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File

// Matches res/xml/file_paths.xml's <cache-path name="scan_photos" ...> and
// the manifest's ${applicationId}.fileprovider authority - the camera app
// writes the captured photo directly to this file via the returned Uri.
fun createScanPhotoUri(context: Context): Uri {
    val dir = File(context.cacheDir, "scan_photos").apply { mkdirs() }
    val file = File(dir, "scan_${System.currentTimeMillis()}.jpg")
    return FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
}
