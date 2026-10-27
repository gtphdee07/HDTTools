package com.rigcheck.app.ui.util

import android.content.Context
import android.os.Build
import com.rigcheck.app.BuildConfig
import com.rigcheck.app.data.CrashEnvironment
import com.rigcheck.app.data.CrashReportStore
import com.rigcheck.app.data.buildCrashReport
import com.rigcheck.app.data.crashRecordingHandler
import java.io.File
import java.time.Instant

// App-private storage: no other app can read the report, and it is removed with the app.
fun crashReportStore(context: Context): CrashReportStore = CrashReportStore(File(context.filesDir, "crash-reports"))

// Called first in Application.onCreate so a crash while the app starts up is caught too. Wraps the handler
// that is already installed, so the app crashes as before.
fun installCrashCapture(context: Context) {
    val store = crashReportStore(context)
    val environment = CrashEnvironment(
        versionName = BuildConfig.VERSION_NAME,
        versionCode = BuildConfig.VERSION_CODE,
        androidRelease = Build.VERSION.RELEASE,
        apiLevel = Build.VERSION.SDK_INT,
        deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}",
    )
    Thread.setDefaultUncaughtExceptionHandler(
        crashRecordingHandler(Thread.getDefaultUncaughtExceptionHandler()) { error ->
            store.save(buildCrashReport(error, environment, Instant.now()))
        },
    )
}
