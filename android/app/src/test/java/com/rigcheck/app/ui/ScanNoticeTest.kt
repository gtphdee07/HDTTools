package com.rigcheck.app.ui

import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

// What the entry screen says after a Scan was delivered (#120). The Scan was
// charged whatever it read, so a Scan that read nothing, or only some fields,
// must not look like nothing happened. The notice is built from the Worker's
// `fields` object, as the view model receives it, and read back through the
// entry screen's own text function with the screen's current values. Every
// message is asserted as the words the user reads.
class ScanNoticeTest {
    private fun fields(json: String): JsonObject = Json.parseToJsonElement(json) as JsonObject

    private val everyTruckField = fields(
        """{"manufacturer":"Ford","gvwr_lb":10000,"front_gawr_lb":5000,"rear_gawr_lb":6000}""",
    )
    private val everyTrailerField = fields(
        """{"manufacturer":"Brinkley","gvwr_lb":14000,"gawr_per_axle_lb":7000,"uvw_lb":11000}""",
    )
    private val everyScaleField = fields(
        """{"location_name":"Flying J","steer_axle_lb":12000,"drive_axle_lb":30000,""" +
            """"trailer_axle_lb":25000,"gross_weight_lb":67000}""",
    )

    private fun apply(module: EntryModule, fields: JsonObject, truck: TruckTag = TruckTag(), trailer: TrailerTag = TrailerTag(), scale: ScaleTicket = ScaleTicket()) =
        applyScan(module, fields, truck, trailer, scale)

    // --- the three outcomes, per document ---

    @Test
    fun `a Truck Tag Scan that read nothing says a Scan was used and nothing could be read`() {
        val applied = apply(EntryModule.TRUCK, fields("{}"))
        assertEquals(ScanMessages.NOTHING_READ, applied.notice!!.textFor(applied.truck))
        assertEquals(
            "A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo.",
            ScanMessages.NOTHING_READ,
        )
    }

    @Test
    fun `null fields count as not read`() {
        val applied = apply(
            EntryModule.TRUCK,
            fields("""{"manufacturer":null,"gvwr_lb":null,"front_gawr_lb":null,"rear_gawr_lb":null}"""),
        )
        assertEquals(ScanMessages.NOTHING_READ, applied.notice!!.textFor(applied.truck))
    }

    @Test
    fun `a Truck Tag Scan that read some fields names the ones it did not read`() {
        val applied = apply(EntryModule.TRUCK, fields("""{"manufacturer":"Ford","gvwr_lb":10000}"""))
        assertEquals(
            "A Scan was used, but we couldn't read: Front GAWR and Rear GAWR. " +
                "Type them in, or go back and choose a different photo.",
            applied.notice!!.textFor(applied.truck),
        )
    }

    @Test
    fun `a single unread field is named alone`() {
        val applied = apply(EntryModule.TRUCK, fields("""{"manufacturer":"Ford","gvwr_lb":10000,"front_gawr_lb":5000}"""))
        assertEquals(
            "A Scan was used, but we couldn't read: Rear GAWR. Type it in, or go back and choose a different photo.",
            applied.notice!!.textFor(applied.truck),
        )
    }

    @Test
    fun `three or more unread fields are listed with commas and an and`() {
        val applied = apply(EntryModule.TRUCK, fields("""{"manufacturer":"Ford"}"""))
        assertEquals(
            "A Scan was used, but we couldn't read: GVWR, Front GAWR and Rear GAWR. " +
                "Type them in, or go back and choose a different photo.",
            applied.notice!!.textFor(applied.truck),
        )
    }

    @Test
    fun `a Scan that read every field shows no notice on any document`() {
        assertNull(apply(EntryModule.TRUCK, everyTruckField).notice)
        assertNull(apply(EntryModule.TRAILER, everyTrailerField).notice)
        assertNull(apply(EntryModule.SCALE, everyScaleField).notice)
    }

    @Test
    fun `a Trailer Tag Scan names its unread fields by the labels on the screen`() {
        val applied = apply(EntryModule.TRAILER, fields("""{"manufacturer":"Brinkley","gvwr_lb":14000}"""))
        assertEquals(
            "A Scan was used, but we couldn't read: GAWR per axle and Unloaded weight (UVW). " +
                "Type them in, or go back and choose a different photo.",
            applied.notice!!.textFor(applied.trailer),
        )
    }

    @Test
    fun `a Scale Ticket Scan that read nothing says so, and one that read some names the rest`() {
        val none = apply(EntryModule.SCALE, fields("{}"))
        assertEquals(ScanMessages.NOTHING_READ, none.notice!!.textFor(none.scale))

        val some = apply(
            EntryModule.SCALE,
            fields("""{"location_name":"Flying J","steer_axle_lb":12000,"drive_axle_lb":30000,"gross_weight_lb":67000}"""),
        )
        assertEquals(
            "A Scan was used, but we couldn't read: Trailer axle(s). Type it in, or go back and choose a different photo.",
            some.notice!!.textFor(some.scale),
        )
    }

    // --- the Scan still fills what it read ---

    @Test
    fun `the fields a Scan read are still merged onto the document`() {
        val applied = apply(
            EntryModule.TRUCK,
            fields("""{"manufacturer":"Ford","gvwr_lb":10000}"""),
            truck = TruckTag(name = "Big Blue", rearGawrLb = 6100.0),
        )
        assertEquals(TruckTag(description = "Ford", name = "Big Blue", gvwrLb = 10000.0, rearGawrLb = 6100.0), applied.truck)
    }

    @Test
    fun `scanning one document leaves the other two untouched`() {
        val trailer = TrailerTag(description = "kept")
        val scale = ScaleTicket(grossWeightLb = 1.0)
        val applied = apply(EntryModule.TRUCK, everyTruckField, trailer = trailer, scale = scale)
        assertEquals(trailer, applied.trailer)
        assertEquals(scale, applied.scale)
    }

    // --- the notice goes away when the missing fields are filled in ---

    @Test
    fun `typing into some of the unread fields drops them from the notice`() {
        val applied = apply(EntryModule.TRUCK, fields("""{"manufacturer":"Ford"}"""))
        val typed = applied.truck.copy(gvwrLb = 10000.0)
        assertEquals(
            "A Scan was used, but we couldn't read: Front GAWR and Rear GAWR. " +
                "Type them in, or go back and choose a different photo.",
            applied.notice!!.textFor(typed),
        )
    }

    @Test
    fun `filling in every unread field removes the notice`() {
        val applied = apply(EntryModule.TRUCK, fields("""{"manufacturer":"Ford","gvwr_lb":10000}"""))
        val typed = applied.truck.copy(frontGawrLb = 5000.0, rearGawrLb = 6000.0)
        assertNull(applied.notice!!.textFor(typed))
    }

    @Test
    fun `filling in a text field counts, and a cleared one brings the notice back`() {
        val applied = apply(EntryModule.TRUCK, fields("""{"gvwr_lb":10000,"front_gawr_lb":5000,"rear_gawr_lb":6000}"""))
        val typed = applied.truck.copy(description = "Ford F-450")
        assertNull(applied.notice!!.textFor(typed))
        assertNotNull(applied.notice!!.textFor(typed.copy(description = null)))
    }

    @Test
    fun `after a Scan that read nothing, typing one field switches to naming the rest`() {
        val applied = apply(EntryModule.TRUCK, fields("{}"))
        val typed = applied.truck.copy(gvwrLb = 10000.0)
        assertEquals(
            "A Scan was used, but we couldn't read: Description, Front GAWR and Rear GAWR. " +
                "Type them in, or go back and choose a different photo.",
            applied.notice!!.textFor(typed),
        )
    }

    // --- a re-scan over values the user had already typed ---

    @Test
    fun `a Scan that read nothing still says so when every field already had a value`() {
        val full = TruckTag(description = "Ford", gvwrLb = 1.0, frontGawrLb = 2.0, rearGawrLb = 3.0)
        val applied = apply(EntryModule.TRUCK, fields("{}"), truck = full)
        assertEquals(full, applied.truck)
        assertEquals(ScanMessages.NOTHING_READ, applied.notice!!.textFor(applied.truck))
    }

    @Test
    fun `a Scan that read some fields names the unread ones even if they already had values`() {
        val full = TruckTag(description = "Ford", gvwrLb = 1.0, frontGawrLb = 2.0, rearGawrLb = 3.0)
        val applied = apply(EntryModule.TRUCK, fields("""{"manufacturer":"Ford"}"""), truck = full)
        assertEquals(
            "A Scan was used, but we couldn't read: GVWR, Front GAWR and Rear GAWR. " +
                "Type them in, or go back and choose a different photo.",
            applied.notice!!.textFor(applied.truck),
        )
    }

    // --- only the screen the Scan was for shows it ---

    @Test
    fun `a notice from one document is not shown on another document's screen`() {
        val applied = apply(EntryModule.TRUCK, fields("{}"))
        assertNull(applied.notice!!.textFor(applied.trailer))
        assertNull(applied.notice!!.textFor(applied.scale))
    }

    // --- the balance ---

    private class Reported {
        val shown = mutableListOf<ScanApplied>()
        var balanceReads = 0
    }

    @Test
    fun `a delivered Scan is shown and the balance is read again once, whatever it read`() {
        for (scanned in listOf(fields("{}"), fields("""{"manufacturer":"Ford"}"""), everyTruckField)) {
            val reported = Reported()
            reportScanDelivered(
                EntryModule.TRUCK,
                scanned,
                TruckTag(),
                TrailerTag(),
                ScaleTicket(),
                show = { reported.shown += it },
                refreshBalance = { reported.balanceReads++ },
            )
            assertEquals(scanned.toString(), 1, reported.shown.size)
            assertEquals(scanned.toString(), 1, reported.balanceReads)
        }
    }

    @Test
    fun `an all-blank Scan reports a notice and not an error`() {
        val reported = Reported()
        reportScanDelivered(
            EntryModule.TRAILER,
            fields("{}"),
            TruckTag(),
            TrailerTag(),
            ScaleTicket(),
            show = { reported.shown += it },
            refreshBalance = { reported.balanceReads++ },
        )
        assertNotNull(reported.shown.single().notice)
        assertEquals(1, reported.balanceReads)
    }
}
