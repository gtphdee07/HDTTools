package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

// One Scan at a time per check, and an answer for a check that has ended is
// handed to onGone, never onCurrent (#118). The Scan client is faked and
// delayed: every Scan waits on a CompletableDeferred the test completes, so a
// test decides what happens while the Scan is in flight. No network is used.
class ScanSessionTest {
    private val delivered = ScanResult.Success(JsonObject(emptyMap()))
    private val failed = ScanResult.Failure("network_error", "m")
    private val truckChooser = ScanScreen.Chooser(EntryModule.TRUCK)

    private class Harness {
        val events = mutableListOf<String>()
        val sent = mutableListOf<String>()
        val session = ScanSession(onLiveScanGone = { events += "cleared" })

        // Starts a Scan that waits for `answer`, running up to its first suspension
        // so the in-flight guard has been checked by the time this returns.
        fun TestScope.scan(
            name: String,
            screen: ScanScreen,
            answer: CompletableDeferred<ScanResult>,
        ): Deferred<Boolean> = async(start = CoroutineStart.UNDISPATCHED) {
            session.run(
                screen,
                onStarted = { events += "started $name" },
                send = {
                    sent += name
                    answer.await()
                },
                onCurrent = { events += "current $name" },
                onGone = { events += "gone $name" },
            )
        }
    }

    @Test
    fun `a second Scan while one is in flight does nothing and sends nothing`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val firstRun = scan("first", truckChooser, first)

            val second = scan("second", truckChooser, CompletableDeferred())

            assertFalse(second.await())
            assertEquals(listOf("first"), sent)
            assertEquals(listOf("started first"), events)
            first.complete(delivered)
            firstRun.await()
        }
    }

    @Test
    fun `an answer for the check the Scan started in is the current one and frees the lock`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("first", truckChooser, first)
            first.complete(delivered)
            assertTrue(started.await())

            val next = CompletableDeferred<ScanResult>().also { it.complete(failed) }
            assertTrue(scan("next", truckChooser, next).await())

            assertEquals(listOf("started first", "current first", "started next", "current next"), events)
        }
    }

    @Test
    fun `starting a rig while a Scan is in flight sends its answer to gone, not current`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("first", truckChooser, first)

            session.rigStarted()
            first.complete(delivered)
            started.await()

            assertEquals(listOf("started first", "cleared", "gone first"), events)
        }
    }

    @Test
    fun `leaving the screen the Scan started on sends its answer to gone`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("first", truckChooser, first)

            session.screenShown(ScanScreen.Elsewhere)
            first.complete(delivered)
            started.await()

            assertEquals(listOf("started first", "cleared", "gone first"), events)
        }
    }

    @Test
    fun `moving on to the next screen of the same rig is leaving the screen`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("first", truckChooser, first)

            session.screenShown(ScanScreen.TruckTagEntry)
            first.complete(delivered)
            started.await()

            assertEquals(listOf("started first", "cleared", "gone first"), events)
        }
    }

    @Test
    fun `seeing the same screen again, as after turning the device, does not end the Scan`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("first", truckChooser, first)

            session.screenShown(truckChooser)
            session.screenShown(truckChooser)
            first.complete(delivered)
            started.await()

            assertEquals(listOf("started first", "current first"), events)
        }
    }

    @Test
    fun `another document's Chooser is another screen`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("first", truckChooser, first)

            session.screenShown(ScanScreen.Chooser(EntryModule.TRAILER))
            first.complete(delivered)
            started.await()

            assertEquals(listOf("started first", "cleared", "gone first"), events)
        }
    }

    @Test
    fun `the next check can scan while the old Scan is still running, and the old answer does not touch it`() = runTest {
        val h = Harness()
        val old = CompletableDeferred<ScanResult>()
        val new = CompletableDeferred<ScanResult>()
        with(h) {
            val oldRun = scan("old", truckChooser, old)
            session.rigStarted()

            val newRun = scan("new", truckChooser, new)
            old.complete(delivered)
            oldRun.await()

            // The old answer is gone and did not free the new Scan's lock.
            assertEquals(listOf("started old", "cleared", "started new", "gone old"), events)
            assertFalse(scan("third", truckChooser, CompletableDeferred()).await())

            new.complete(delivered)
            newRun.await()
            assertEquals("current new", events.last())
            assertEquals(listOf("old", "new"), sent)
        }
    }

    @Test
    fun `a late answer is handed over as it came, whether delivered or failed`() = runTest {
        for (answer in listOf(delivered, failed)) {
            val received = mutableListOf<ScanResult>()
            val session = ScanSession()
            val deferred = CompletableDeferred<ScanResult>()
            val run = async(start = CoroutineStart.UNDISPATCHED) {
                session.run(
                    truckChooser,
                    onStarted = {},
                    send = { deferred.await() },
                    onCurrent = { error("not the current check") },
                    onGone = { received += it },
                )
            }
            session.rigStarted()
            deferred.complete(answer)
            run.await()

            assertEquals(listOf(answer), received)
        }
    }

    @Test
    fun `the stand-alone ticket Scan follows the same rules on its own screen`() = runTest {
        val h = Harness()
        val first = CompletableDeferred<ScanResult>()
        with(h) {
            val started = scan("ticket", ScanScreen.TruckTagEntry, first)
            assertFalse(scan("again", ScanScreen.TruckTagEntry, CompletableDeferred()).await())

            session.screenShown(ScanScreen.Chooser(EntryModule.TRAILER))
            first.complete(delivered)
            started.await()

            assertEquals(listOf("started ticket", "cleared", "gone ticket"), events)
        }
    }

    @Test
    fun `nothing is cleared when no Scan is in flight`() = runTest {
        val h = Harness()
        h.session.rigStarted()
        h.session.screenShown(ScanScreen.Elsewhere)

        assertEquals(emptyList<String>(), h.events)
    }

    @Test
    fun `a Scan whose client throws frees the lock`() = runTest {
        val session = ScanSession()
        val thrown = async(start = CoroutineStart.UNDISPATCHED) {
            runCatching {
                session.run(truckChooser, onStarted = {}, send = { error("boom") }, onCurrent = {}, onGone = {})
            }
        }
        assertTrue(thrown.await().isFailure)

        val ran = session.run(truckChooser, onStarted = {}, send = { delivered }, onCurrent = {}, onGone = {})

        assertTrue(ran)
    }
}
