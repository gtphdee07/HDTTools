package com.rigcheck.app.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.time.Instant

// #184: what a saved crash report holds, what it must not, how many are kept, and that recording a crash
// never stops the app from crashing as before. All on the JVM: a real exception, a temp directory, no device.
class CrashReportTest {

    @get:Rule
    val tmp = TemporaryFolder()

    private val env = CrashEnvironment(
        versionName = "1.0-beta",
        versionCode = 12,
        androidRelease = "14",
        apiLevel = 34,
        deviceModel = "Google Pixel 7",
    )
    private val at = Instant.parse("2026-10-27T12:00:00Z")

    // A crash whose messages carry what must never be saved: an email, a token, a password and a typed value.
    private fun crashCarryingSecrets(): Throwable = IllegalStateException(
        "sign-in failed for tester@example.com token=eyJSECRETTOKEN password=hunter2",
        NumberFormatException("For input string: \"98765-my-truck-weight\""),
    )

    @Test
    fun reportHoldsTheTraceTheVersionTheAndroidVersionTheModelAndTheTime() {
        val report = buildCrashReport(crashCarryingSecrets(), env, at)

        assertTrue(report.contains("java.lang.IllegalStateException"))
        assertTrue("the cause chain is kept", report.contains("Caused by: java.lang.NumberFormatException"))
        assertTrue("frames name the code", report.contains("\tat com.rigcheck.app.data.CrashReportTest.crashCarryingSecrets"))
        assertTrue(report.contains("App version: 1.0-beta (12)"))
        assertTrue(report.contains("Android: 14 (API 34)"))
        assertTrue(report.contains("Device: Google Pixel 7"))
        assertTrue(report.contains("Time: 2026-10-27T12:00:00Z"))
    }

    // The rule chosen: messages are not recorded at all. A pattern scrub would catch an email and miss the
    // next shape of secret; the class names and frames say where the app broke without any of it.
    @Test
    fun exceptionMessagesAreNotRecordedSoNoEmailTokenPasswordOrTypedValueIsSaved() {
        val report = buildCrashReport(crashCarryingSecrets(), env, at)

        assertFalse(report.contains("tester@example.com"))
        assertFalse(report.contains("eyJSECRETTOKEN"))
        assertFalse(report.contains("hunter2"))
        assertFalse("a typed value quoted by a cause", report.contains("98765"))
    }

    @Test
    fun aHugeStackAndALongCauseChainAreCapped() {
        val deep = RuntimeException("deep")
        deep.stackTrace = Array(5000) { StackTraceElement("com.rigcheck.app.Loop", "again", "Loop.kt", it) }
        var chained: Throwable = deep
        repeat(20) { chained = RuntimeException("wrapper $it", chained) }

        val report = buildCrashReport(chained, env, at)

        assertTrue("a few thousand frames would make an unsendable email", report.lines().size < 500)
        assertEquals("at most 5 exceptions in the chain", 4, Regex("Caused by:").findAll(report).count())
        assertFalse(report.contains("wrapper"))
    }

    @Test
    fun aFrameCutByTheCapSaysHowManyWereLeftOut() {
        val big = RuntimeException()
        big.stackTrace = Array(100) { StackTraceElement("com.rigcheck.app.Loop", "again", "Loop.kt", it) }

        assertTrue(buildCrashReport(big, env, at).contains("\t... 60 more"))
    }

    @Test
    fun nothingWaitsUntilACrashIsSaved() {
        assertNull(CrashReportStore(tmp.newFolder("empty")).pending())
    }

    @Test
    fun aSavedReportIsWaitingUntilItIsCleared() {
        val store = CrashReportStore(tmp.root.resolve("not-created-yet"))

        store.save("report one")

        assertEquals("report one", store.pending())
        assertEquals("a read does not remove it", "report one", store.pending())
        store.clear()
        assertNull(store.pending())
    }

    @Test
    fun clearingWhenNothingWaitsIsHarmless() {
        CrashReportStore(tmp.newFolder("none")).clear()
    }

    @Test
    fun aNewerCrashReplacesTheOlderReportSoReportsDoNotPileUp() {
        val dir = tmp.newFolder("reports")
        val store = CrashReportStore(dir)

        store.save("first crash")
        store.save("second crash")

        assertEquals("second crash", store.pending())
        assertEquals(1, dir.listFiles()!!.size)
    }

    @Test
    fun theHandlerRecordsTheCrashAndThenThePreviousHandlerRunsWithTheSameThreadAndError() {
        val calls = mutableListOf<String>()
        val error = IllegalStateException("boom")
        val thread = Thread.currentThread()
        var previousSaw: Pair<Thread, Throwable>? = null
        val previous = Thread.UncaughtExceptionHandler { t, e ->
            calls += "previous"
            previousSaw = t to e
        }

        crashRecordingHandler(previous) { calls += "record:${it.message}" }.uncaughtException(thread, error)

        assertEquals(listOf("record:boom", "previous"), calls)
        assertSame(thread, previousSaw!!.first)
        assertSame(error, previousSaw!!.second)
    }

    @Test
    fun theCrashStillGoesOnWhenRecordingItFails() {
        var previousRan = false

        crashRecordingHandler({ _, _ -> previousRan = true }) { throw java.io.IOException("disk full") }
            .uncaughtException(Thread.currentThread(), RuntimeException())

        assertTrue(previousRan)
    }

    @Test
    fun aHandlerWithNothingBeforeItStillRecords() {
        var recorded = false

        crashRecordingHandler(null) { recorded = true }.uncaughtException(Thread.currentThread(), RuntimeException())

        assertTrue(recorded)
    }
}
