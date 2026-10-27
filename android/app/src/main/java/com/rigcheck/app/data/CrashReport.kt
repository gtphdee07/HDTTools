package com.rigcheck.app.data

import java.io.File
import java.time.Instant

// Crash capture (#184): a crash is written to the phone, and the next launch asks the tester whether to send
// it. Nothing leaves the phone from here; the rules below are the pure part, so they run on the JVM.

// What the report says about the phone and the build. The caller reads these from BuildConfig and Build.
data class CrashEnvironment(
    val versionName: String,
    val versionCode: Int,
    val androidRelease: String,
    val apiLevel: Int,
    val deviceModel: String,
)

private const val MAX_FRAMES = 40
private const val MAX_CAUSES = 5

// The report is the email body, so it is plain text and small. The privacy rule is that exception MESSAGES
// are never recorded, only each exception's class name and its stack frames (code names and line numbers).
// A message is where a typed value or an account detail would leak (NumberFormatException quotes the
// input, a failed request can quote a URL or a header), and a pattern scrub would miss the next shape of
// secret; a stack trace without messages still says where the app broke. The cause chain is kept, depth
// and frames capped so a StackOverflowError does not make a huge email.
fun buildCrashReport(error: Throwable, env: CrashEnvironment, at: Instant): String = buildString {
    appendLine("RigCheck crash report")
    appendLine("Time: $at")
    appendLine("App version: ${env.versionName} (${env.versionCode})")
    appendLine("Android: ${env.androidRelease} (API ${env.apiLevel})")
    appendLine("Device: ${env.deviceModel}")
    generateSequence(error) { it.cause }.take(MAX_CAUSES).forEachIndexed { index, throwable ->
        appendLine()
        appendLine(if (index == 0) throwable.javaClass.name else "Caused by: ${throwable.javaClass.name}")
        val frames = throwable.stackTrace
        frames.take(MAX_FRAMES).forEach { appendLine("\tat $it") }
        if (frames.size > MAX_FRAMES) appendLine("\t... ${frames.size - MAX_FRAMES} more")
    }
}

// The one report waiting on the phone. A newer crash replaces an older unanswered one, so reports never pile up.
class CrashReportStore(private val directory: File) {
    private val file get() = File(directory, "crash-report.txt")

    fun save(report: String) {
        directory.mkdirs()
        file.writeText(report)
    }

    fun pending(): String? = file.takeIf { it.isFile }?.readText()?.takeIf { it.isNotBlank() }

    fun clear() {
        file.delete()
    }
}

// Records the crash, then hands it to the handler that was installed before (on Android, the one that shows
// "App has stopped" and ends the process), so the app crashes exactly as it did. Recording must never get
// in the way of that: if it fails, the crash still goes on.
fun crashRecordingHandler(
    previous: Thread.UncaughtExceptionHandler?,
    record: (Throwable) -> Unit,
): Thread.UncaughtExceptionHandler = Thread.UncaughtExceptionHandler { thread, error ->
    try {
        record(error)
    } catch (_: Throwable) {
        // A failed write (disk full, no directory) is not worth losing the original crash for.
    }
    previous?.uncaughtException(thread, error)
}
