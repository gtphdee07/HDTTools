package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.ui.navigation.EntryModule

// The screen a Scan was started on, the unit of "leaving the check" the Scan is
// tied to (a Check, in android/CONTEXT.md). Elsewhere is every other screen.
sealed interface ScanScreen {
    data class Chooser(val module: EntryModule) : ScanScreen
    data object TruckTagEntry : ScanScreen
    data object Elsewhere : ScanScreen
}

// Decides which answers a Scan may change the app with (#118). One Scan runs at
// a time; a Scan belongs to the Check and the screen it started on, and its
// answer is the current one only while both still stand. Picking or starting
// another rig, or the user showing up on another screen, ends the Scan's check:
// its answer is handed to onGone, which only reports it, never onCurrent, which
// is the one place a Scan's fields are merged and the app moves on. The Scan
// itself is not cancelled (the Worker has taken a Scan Credit for it); ending
// the check frees the lock at once, so the next check can scan while the old
// request is still out.
class ScanSession(private val onLiveScanGone: () -> Unit = {}) {
    private class Live(val screen: ScanScreen)

    private var live: Live? = null

    // Returns false, having done nothing, when a Scan of this check is already in
    // flight. onStarted runs before anything is sent.
    suspend fun run(
        screen: ScanScreen,
        onStarted: () -> Unit,
        send: suspend () -> ScanResult,
        onCurrent: (ScanResult) -> Unit,
        onGone: (ScanResult) -> Unit,
    ): Boolean {
        if (live != null) return false
        val mine = Live(screen)
        live = mine
        onStarted()
        val result = try {
            send()
        } catch (e: Throwable) {
            if (live === mine) live = null
            throw e
        }
        if (live === mine) {
            live = null
            onCurrent(result)
        } else {
            onGone(result)
        }
        return true
    }

    // Another rig was picked or started.
    fun rigStarted() = endLive()

    // The screen on show changed, or was shown again (as after turning the
    // device, which is not leaving). A Scan started on any other screen ends.
    fun screenShown(screen: ScanScreen) {
        if (live?.screen != screen) endLive()
    }

    private fun endLive() {
        if (live == null) return
        live = null
        onLiveScanGone()
    }
}

// A Scan answered after its check ended: what the user is told, and the balance
// brought up to date (the Worker may have taken a Scan Credit whatever the
// answer was). This is given no way to change the rig, so a late answer cannot
// merge into the current one. A delivered Scan says its result was not used; a
// failure shows its own message, which already says whether a Scan Credit was
// used or refunded, with no next steps, since the photo and the document it
// would act on belong to a check the user has left.
fun reportLateScan(
    result: ScanResult,
    show: (String) -> Unit,
    refreshBalance: () -> Unit,
    setBalance: (Int) -> Unit,
) {
    when (result) {
        is ScanResult.Success -> {
            show(ScanMessages.RESULT_NOT_USED)
            refreshBalance()
        }
        is ScanResult.Failure -> reportScanFailure(
            result,
            show = { show(it.message) },
            refreshBalance = refreshBalance,
            setBalance = setBalance,
        )
    }
}
