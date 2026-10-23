package com.rigcheck.app.ui

import com.rigcheck.app.data.HistoryCaps
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictStatus
import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

// What the History screen says: the badge for each verdict, the day of a check, what a Free account whose History
// is full is told, and what a check that was not saved to the History says.
class HistoryDisplayTest {

    @Test
    fun `each verdict has Web's badge, and a partial or insufficient check is not called over the limit`() {
        assertEquals(VerdictBadge(Tone.SUCCESS, "Safe to Tow"), verdictBadgeFor(VerdictStatus.PASS))
        assertEquals(VerdictBadge(Tone.WARNING, "Over Limit"), verdictBadgeFor(VerdictStatus.FAIL))
        assertEquals(VerdictBadge(Tone.INSUFFICIENT, "Partially Checked"), verdictBadgeFor(VerdictStatus.PARTIAL))
        assertEquals(VerdictBadge(Tone.INSUFFICIENT, "Not Enough Info"), verdictBadgeFor(VerdictStatus.INSUFFICIENT))
    }

    @Test
    fun `a check is dated by the day it was on the phone's clock`() {
        // 02:30 UTC on the 23rd is still the evening of the 22nd in Chicago.
        assertEquals("Oct 22, 2026", historyDateText("2026-10-23T02:30:00Z", ZoneId.of("America/Chicago")))
        assertEquals("Oct 23, 2026", historyDateText("2026-10-23T02:30:00Z", ZoneId.of("UTC")))
        assertEquals("Oct 5, 2026", historyDateText("2026-10-05T12:00:00Z", ZoneId.of("UTC")))
    }

    @Test
    fun `an instant that cannot be read is shown as it came`() {
        assertEquals("sometime", historyDateText("sometime"))
    }

    private val caps = HistoryCaps(free = 10, pro = 50)

    @Test
    fun `a Free account whose History is full is told what each plan keeps`() {
        assertEquals(
            "The Free plan keeps your last 10 checks, and the oldest drops off as you add more. Pro keeps your last 50.",
            historyLimitNotice(count = 10, caps = caps, isPro = false),
        )
    }

    @Test
    fun `a Free account with room left is told nothing`() {
        assertNull(historyLimitNotice(count = 9, caps = caps, isPro = false))
    }

    @Test
    fun `a Pro account, an unknown plan, or unread caps are told nothing`() {
        assertNull(historyLimitNotice(count = 50, caps = caps, isPro = true))
        assertNull(historyLimitNotice(count = 10, caps = caps, isPro = null))
        assertNull(historyLimitNotice(count = 10, caps = null, isPro = false))
    }

    @Test
    fun `a check that was not saved says so and says the check is not affected`() {
        assertEquals(
            "We couldn't save this check to your History. Your check is not affected.",
            historyNoticeFor(saved = false),
        )
        assertNull(historyNoticeFor(saved = true))
    }
}
