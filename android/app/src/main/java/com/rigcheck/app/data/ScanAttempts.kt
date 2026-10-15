package com.rigcheck.app.data

import com.rigcheck.app.ui.navigation.EntryModule
import java.util.UUID

// The Worker's answers that leave it unknown whether a Scan was charged: no
// connection or a timed-out read, a reply that is not the Worker's, and the two
// codes where it charged and could not (or did not) refund. Mirrors Web's
// ScanError.lostResponse.
private val LOST_ANSWER_CODES = setOf(
    "network_error",
    "parse_error",
    "billing_error",
    "extraction_failed_no_refund",
)

// Gives each Scan of a photo the client_request_id the Worker dedupes charges
// on. The id stays the same for as long as the answer to a photo's last request
// is lost, so the retry is the same logical Scan and is charged once. Any other
// answer settles the attempt, and the next Scan of that photo, or of another,
// starts a fresh id. Mirrors Web's ScanAttempts (web/src/scanAttempts.ts).
//
// A photo is told apart by its Uri string and the document it is scanned for.
// A gallery photo picked again has the same Uri, so it is a retry; a retaken
// camera photo is written to a new file, so it is a different photo.
class ScanAttempts {
    private data class Open(val module: EntryModule, val photo: String, val id: String)

    private var open: Open? = null

    suspend fun run(
        module: EntryModule,
        photo: String,
        scan: suspend (clientRequestId: String) -> ScanResult,
    ): ScanResult {
        val id = open?.takeIf { it.module == module && it.photo == photo }?.id ?: UUID.randomUUID().toString()
        open = Open(module, photo, id)
        val result = scan(id)
        if (!(result is ScanResult.Failure && result.code in LOST_ANSWER_CODES)) open = null
        return result
    }
}
