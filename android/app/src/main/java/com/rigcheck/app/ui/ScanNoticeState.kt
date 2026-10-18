package com.rigcheck.app.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

// Holds the notice for the entry screen reached after a delivered Scan (#120)
// and says when it is dropped. The rule: a notice belongs to the Scan that made
// it, so it lasts until the user leaves that screen, enters the document by
// hand, starts another Scan or starts a rig. Each of those is a named event
// here, so the rule is tested without a Scan and the callers say which event
// they are.
class ScanNoticeState {
    var notice by mutableStateOf<ScanNotice?>(null)
        private set

    // A Scan was delivered: its notice, or null when it read every field.
    fun scanDelivered(notice: ScanNotice?) {
        this.notice = notice
    }

    fun scanStarted() = clear()

    fun enteredManually() = clear()

    fun leftEntryScreen() = clear()

    fun rigStarted() = clear()

    private fun clear() {
        notice = null
    }
}
