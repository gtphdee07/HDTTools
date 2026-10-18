package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanResult

// What the error dialog offers beside OK, so a failed Scan never leaves the
// user at a dead end. Which steps follow which failure is the retry rule of
// docs/research/scan-failure-handling.md (R3): Try again only where a retry is
// free or correctly priced, a different photo where the same photo would fail
// again, signing in or buying Scans where the account is the problem. Typing the
// numbers in is offered wherever the photo is the problem (typing never needs a
// Scan), so the way out of a photo loop is a button, not a hint in the message.
enum class ScanNextStep { SIGN_IN, BUY_SCANS, TRY_AGAIN, CHOOSE_DIFFERENT_PHOTO, TYPE_IT_IN }

// The app's own results when the Scan never reached the Worker.
internal val NOT_SIGNED_IN = ScanResult.Failure("not_signed_in", "Sign in to scan.")
internal val PHOTO_UNSENDABLE = ScanResult.Failure("photo_unsendable", "Could not decode the captured photo.")

// A delivered stand-alone ticket with no weight in it. The Scan was charged and
// is not refunded, so it offers no Try again: the same photo through the same
// reader would probably come back the same, as another paid Scan.
internal val NO_WEIGHT_ERROR = ScanUiState.Error(
    ScanMessages.NO_WEIGHT,
    listOf(ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO),
)

private fun scanError(message: String, vararg steps: ScanNextStep) = ScanUiState.Error(message, steps.toList())

// The words and next steps for a failure, by its code. The Worker's own text is
// written for developers and never shown, so an unknown code gets a message that
// claims nothing about the charge.
fun scanErrorFor(failure: ScanResult.Failure): ScanUiState.Error = when (failure.code) {
    "insufficient_credits" -> scanError(ScanMessages.OUT_OF_SCANS, ScanNextStep.BUY_SCANS)
    "unauthorized" -> scanError(ScanMessages.EXPIRED_SIGN_IN, ScanNextStep.SIGN_IN)
    "not_signed_in" -> scanError(ScanMessages.NOT_SIGNED_IN, ScanNextStep.SIGN_IN)
    "auth_unavailable" -> scanError(ScanMessages.AUTH_UNAVAILABLE, ScanNextStep.TRY_AGAIN)
    "extraction_failed" -> scanError(ScanMessages.EXTRACTION_FAILED, ScanNextStep.TRY_AGAIN)
    "extraction_failed_no_refund" -> scanError(ScanMessages.EXTRACTION_FAILED_NO_REFUND, ScanNextStep.TRY_AGAIN)
    "billing_error" -> scanError(ScanMessages.BILLING_ERROR, ScanNextStep.TRY_AGAIN)
    "bad_request" -> scanError(ScanMessages.BAD_REQUEST, ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO)
    "photo_unsendable" -> scanError(ScanMessages.PHOTO_UNSENDABLE, ScanNextStep.TYPE_IT_IN, ScanNextStep.CHOOSE_DIFFERENT_PHOTO)
    "network_error" -> scanError(ScanMessages.NO_CONNECTION, ScanNextStep.TRY_AGAIN)
    "parse_error" -> scanError(ScanMessages.NO_ANSWER, ScanNextStep.TRY_AGAIN)
    "timeout" -> scanError(ScanMessages.TOO_SLOW, ScanNextStep.TRY_AGAIN)
    else -> scanError(ScanMessages.UNKNOWN)
}

// Shows a failed Scan and brings the balance on screen up to date. After
// insufficient_credits the Worker has just said there is nothing left, so the
// balance is set to 0 on the spot, with no read (the Scan was not charged, so
// there is nothing to refresh, and the chip must not keep a stale number).
// After anything else it may have been charged and refunded (or not), so it is
// read again. The view model's two Scan entry points both end here.
fun reportScanFailure(
    failure: ScanResult.Failure,
    show: (ScanUiState.Error) -> Unit,
    refreshBalance: () -> Unit,
    setBalance: (Int) -> Unit,
) {
    show(scanErrorFor(failure))
    if (failure.code == "insufficient_credits") setBalance(0) else refreshBalance()
}

// The one rule for starting a Scan from any button: with a balance above zero
// the photo source is offered, otherwise the user goes to the paywall, which
// asks a signed-out user to sign in first (the balance is only known for a
// signed-in account).
fun canStartScan(creditBalance: Int?): Boolean = (creditBalance ?: 0) > 0
