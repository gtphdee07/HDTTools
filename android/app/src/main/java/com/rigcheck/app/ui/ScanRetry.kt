package com.rigcheck.app.ui

import com.rigcheck.app.ui.navigation.EntryModule

// Remembers the Scan the user last started, so the error dialog's "Try again"
// can send the same photo again through the same entry point: a document's Scan
// or the stand-alone ticket's. The request id is not kept here; ScanAttempts
// keeps it for the same photo while the answer was lost, so a retry is the same
// logical Scan and is charged once.
class ScanRetry<P> {
    private sealed interface Started<P> {
        data class Document<P>(val module: EntryModule, val photo: P) : Started<P>
        data class StandaloneTicket<P>(val photo: P) : Started<P>
    }

    private var last: Started<P>? = null

    fun started(module: EntryModule, photo: P) {
        last = Started.Document(module, photo)
    }

    fun startedStandalone(photo: P) {
        last = Started.StandaloneTicket(photo)
    }

    // Runs the entry point of the last Scan with its photo; null when no Scan has
    // been started, which sends nothing.
    fun <R> again(main: (EntryModule, P) -> R, standalone: (P) -> R): R? = when (val started = last) {
        is Started.Document -> main(started.module, started.photo)
        is Started.StandaloneTicket -> standalone(started.photo)
        null -> null
    }
}
