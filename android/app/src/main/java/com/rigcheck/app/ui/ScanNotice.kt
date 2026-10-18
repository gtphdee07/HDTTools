package com.rigcheck.app.ui

import com.rigcheck.app.data.SCALE_SCAN_FIELDS
import com.rigcheck.app.data.ScanField
import com.rigcheck.app.data.TRAILER_SCAN_FIELDS
import com.rigcheck.app.data.TRUCK_SCAN_FIELDS
import com.rigcheck.app.data.mergeScanFields
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.serialization.json.JsonObject

// What the entry screen says after a Scan was delivered but did not read every
// field (#120). The Scan was charged whatever it read, and an all-blank answer
// leaves the screen as it was, so without this nothing tells the user a Scan
// was used. A notice, not a failure: no Try again (the same photo would
// probably read the same, as another paid Scan).
//
// It remembers which of the screen's fields the Scan did not read, and which of
// those were still blank once the Scan's values were merged in. It is shown for
// as long as any field that was blank is still blank; typing the missing
// numbers in makes it go away on its own.
data class ScanNotice(
    val module: EntryModule,
    val unreadKeys: Set<String>,
    val blankAtScanKeys: Set<String>,
) {
    fun textFor(truck: TruckTag): String? = text(EntryModule.TRUCK, TRUCK_SCAN_FIELDS, truck)

    fun textFor(trailer: TrailerTag): String? = text(EntryModule.TRAILER, TRAILER_SCAN_FIELDS, trailer)

    fun textFor(scale: ScaleTicket): String? = text(EntryModule.SCALE, SCALE_SCAN_FIELDS, scale)

    private fun <T> text(forModule: EntryModule, fields: List<ScanField<T>>, current: T): String? {
        if (module != forModule) return null
        val unread = fields.filter { it.key in unreadKeys }
        val blankNow = unread.filter { it.isBlankIn(current) }
        // Every field that was blank has been filled in.
        if (blankAtScanKeys.isNotEmpty() && blankNow.isEmpty()) return null
        // Nothing read, and nothing typed since: the whole-Scan wording.
        if (unread.size == fields.size && blankNow.size >= blankAtScanKeys.size) return ScanMessages.NOTHING_READ
        return ScanMessages.someNotRead((blankNow.ifEmpty { unread }).map { it.label })
    }
}

// The three documents after a Scan, and the notice for the one that was scanned.
data class ScanApplied(
    val truck: TruckTag,
    val trailer: TrailerTag,
    val scale: ScaleTicket,
    val notice: ScanNotice?,
)

// Merges a delivered Scan onto the scanned document (only the fields it read;
// see mergeScanFields) and says which fields it did not read, or null when it
// read them all.
fun applyScan(
    module: EntryModule,
    fields: JsonObject,
    truck: TruckTag,
    trailer: TrailerTag,
    scale: ScaleTicket,
): ScanApplied = when (module) {
    EntryModule.TRUCK -> truck.mergeScanFields(fields).let {
        ScanApplied(it, trailer, scale, noticeFor(module, fields, TRUCK_SCAN_FIELDS, it))
    }
    EntryModule.TRAILER -> trailer.mergeScanFields(fields).let {
        ScanApplied(truck, it, scale, noticeFor(module, fields, TRAILER_SCAN_FIELDS, it))
    }
    EntryModule.SCALE -> scale.mergeScanFields(fields).let {
        ScanApplied(truck, trailer, it, noticeFor(module, fields, SCALE_SCAN_FIELDS, it))
    }
}

private fun <T> noticeFor(module: EntryModule, scanned: JsonObject, fields: List<ScanField<T>>, merged: T): ScanNotice? {
    val unread = fields.filterNot { it.wasReadIn(scanned) }
    if (unread.isEmpty()) return null
    return ScanNotice(
        module,
        unreadKeys = unread.map { it.key }.toSet(),
        blankAtScanKeys = unread.filter { it.isBlankIn(merged) }.map { it.key }.toSet(),
    )
}

// A delivered Scan: shows what it filled in and what it did not, and brings the
// balance on screen up to date. The Worker has already taken one Scan Credit, so
// the balance is read again whatever the Scan read. The view model's main-path
// Scan ends here, as reportScanFailure is where its failures end.
fun reportScanDelivered(
    module: EntryModule,
    fields: JsonObject,
    truck: TruckTag,
    trailer: TrailerTag,
    scale: ScaleTicket,
    show: (ScanApplied) -> Unit,
    refreshBalance: () -> Unit,
) {
    show(applyScan(module, fields, truck, trailer, scale))
    refreshBalance()
}
