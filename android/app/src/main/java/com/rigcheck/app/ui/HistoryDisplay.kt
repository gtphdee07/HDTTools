package com.rigcheck.app.ui

import com.rigcheck.app.data.HistoryCaps
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictStatus
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

// What the History screen and a check that did not reach the History say (mirrors web/src/verdictBadge.ts,
// web/src/screens/History.tsx and web/src/App.tsx historyNotice).

// A verdict as a compact badge. The labels are Web's, which shorten breakdown.py's verdict_for headlines: a
// partial or insufficient check is not an over-limit one and must not be labelled as such.
data class VerdictBadge(val tone: Tone, val label: String)

fun verdictBadgeFor(verdict: VerdictStatus): VerdictBadge = when (verdict) {
    VerdictStatus.PASS -> VerdictBadge(Tone.SUCCESS, "Safe to Tow")
    VerdictStatus.FAIL -> VerdictBadge(Tone.WARNING, "Over Limit")
    VerdictStatus.PARTIAL -> VerdictBadge(Tone.INSUFFICIENT, "Partially Checked")
    VerdictStatus.INSUFFICIENT -> VerdictBadge(Tone.INSUFFICIENT, "Not Enough Info")
}

private val HISTORY_DATE_FORMAT = DateTimeFormatter.ofPattern("MMM d, yyyy", Locale.US)

// The day of a check as the user's phone sees it, in the form the Results screen shows today's date. An
// instant that cannot be read is shown as it came.
fun historyDateText(checkedAt: String, zone: ZoneId = ZoneId.systemDefault()): String =
    runCatching { HISTORY_DATE_FORMAT.format(Instant.parse(checkedAt).atZone(zone)) }.getOrDefault(checkedAt)

// Told to a Free account whose History is full, with "Upgrade to Pro": what each plan keeps. Nothing for a
// Pro or unknown plan, a signed-out user, or caps that could not be read.
fun historyLimitNotice(count: Int, caps: HistoryCaps?, isPro: Boolean?): String? {
    if (isPro != false || caps == null || count < caps.free) return null
    return "The Free plan keeps your last ${caps.free} checks, and the oldest drops off as you add more. " +
        "Pro keeps your last ${caps.pro}."
}

// The check went ahead; only its History entry did not reach the account.
fun historyNoticeFor(saved: Boolean): String? =
    if (saved) null else "We couldn't save this check to your History. Your check is not affected."
