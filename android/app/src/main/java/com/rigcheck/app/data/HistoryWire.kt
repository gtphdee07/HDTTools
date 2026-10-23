package com.rigcheck.app.data

import com.rigcheck.app.domain.VerdictStatus

// How a check is stored in the account's History (the `history_entries` table, supabase/migrations/
// 20261022000000_history_entries.sql). Web writes the verdict as the Core status word; Android's
// VerdictStatus is the same four values under its own names.

internal fun verdictToWire(verdict: VerdictStatus): String = when (verdict) {
    VerdictStatus.PASS -> "pass"
    VerdictStatus.FAIL -> "fail"
    VerdictStatus.PARTIAL -> "partial"
    VerdictStatus.INSUFFICIENT -> "insufficient"
}

// A word this app does not know is null: showing a verdict it cannot read as some other one would tell a
// user something about their rig that nobody checked.
internal fun verdictFromWire(word: String): VerdictStatus? = when (word) {
    "pass" -> VerdictStatus.PASS
    "fail" -> VerdictStatus.FAIL
    "partial" -> VerdictStatus.PARTIAL
    "insufficient" -> VerdictStatus.INSUFFICIENT
    else -> null
}

internal fun historyEntryFromRow(id: String, rigNickname: String, verdict: String, checkedAt: String): HistoryEntry? =
    verdictFromWire(verdict)?.let { HistoryEntry(id, asInstant(checkedAt), rigNickname.trim(), it) }
