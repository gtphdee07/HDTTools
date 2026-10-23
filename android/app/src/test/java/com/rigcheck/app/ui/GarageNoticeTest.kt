package com.rigcheck.app.ui

import com.rigcheck.app.data.SaveRigOutcome
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

// What the user is told when a check's Rig does not reach the Garage. The wording matches Web's, and a Free
// account with a full Garage is the only one offered Pro: a Pro account cannot buy it again, and one whose
// plan is unknown must not be told it is Free.
class GarageNoticeTest {

    @Test
    fun `a saved Rig says nothing`() {
        assertNull(garageNoticeFor("Goose", SaveRigOutcome.Saved, isPro = false))
    }

    @Test
    fun `a full Free Garage names the Free cap and offers Pro`() {
        val notice = garageNoticeFor("Goose", SaveRigOutcome.Full(cap = 5), isPro = false)!!

        assertEquals(
            "Your Garage is full (the Free plan holds 5 Rigs), so \"Goose\" wasn't saved to it. Your check is not affected.",
            notice.message,
        )
        assertEquals(true, notice.offerPro)
    }

    @Test
    fun `a full Pro Garage names the Pro cap and offers nothing`() {
        val notice = garageNoticeFor("Goose", SaveRigOutcome.Full(cap = 25), isPro = true)!!

        assertEquals(
            "Your Garage is full (Pro holds 25 Rigs), so \"Goose\" wasn't saved to it. Your check is not affected.",
            notice.message,
        )
        assertEquals(false, notice.offerPro)
    }

    @Test
    fun `a full Garage whose plan is unknown says the limit may be the Free one and offers nothing`() {
        val notice = garageNoticeFor("Goose", SaveRigOutcome.Full(cap = 5), isPro = null)!!

        assertEquals(
            "Your Garage is full (5 Rigs, which may be the Free limit because we couldn't check your plan), " +
                "so \"Goose\" wasn't saved to it. Your check is not affected.",
            notice.message,
        )
        assertEquals(false, notice.offerPro)
    }

    @Test
    fun `a full Garage whose cap is not known just says it is full`() {
        assertEquals(
            "Your Garage is full, so \"Goose\" wasn't saved to it. Your check is not affected.",
            garageNoticeFor("Goose", SaveRigOutcome.Full(cap = null), isPro = false)!!.message,
        )
    }

    @Test
    fun `one Rig is not pluralised`() {
        assertEquals(
            "Your Garage is full (the Free plan holds 1 Rig), so \"Goose\" wasn't saved to it. Your check is not affected.",
            garageNoticeFor("Goose", SaveRigOutcome.Full(cap = 1), isPro = false)!!.message,
        )
    }

    @Test
    fun `a save that failed says so and offers nothing`() {
        val notice = garageNoticeFor("Goose", SaveRigOutcome.Failed, isPro = false)!!

        assertEquals("We couldn't save \"Goose\" to your Garage. Your check is not affected.", notice.message)
        assertEquals(false, notice.offerPro)
    }
}
