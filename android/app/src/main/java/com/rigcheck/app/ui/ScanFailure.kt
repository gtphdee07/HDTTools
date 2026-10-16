package com.rigcheck.app.ui

import com.rigcheck.app.data.ScanResult

// What the error dialog offers beside OK, so a failed Scan never leaves the
// user at a dead end: signing in (again) when the account is the problem,
// buying scans when there are none left, nothing when only waiting or another
// photo helps.
enum class ScanNextStep { NONE, SIGN_IN, BUY_SCANS }

// The app's own result when there is no account token to send.
internal val NOT_SIGNED_IN = ScanResult.Failure("not_signed_in", "Sign in to scan.")

// The wording for the codes whose Worker message is not written for the user
// (mirrors Web's api.ts). Any other code shows the message it came with.
private const val EXPIRED_SIGN_IN = "Your sign-in has expired. Sign in again to scan."
private const val AUTH_UNAVAILABLE =
    "We couldn't verify your account just now, so nothing was scanned and you were not charged. " +
        "Try again in a moment."
private const val OUT_OF_SCANS = "You're out of scans."

fun scanErrorFor(failure: ScanResult.Failure): ScanUiState.Error = when (failure.code) {
    "unauthorized" -> ScanUiState.Error(EXPIRED_SIGN_IN, ScanNextStep.SIGN_IN)
    "not_signed_in" -> ScanUiState.Error(failure.message, ScanNextStep.SIGN_IN)
    "auth_unavailable" -> ScanUiState.Error(AUTH_UNAVAILABLE)
    "insufficient_credits" -> ScanUiState.Error(OUT_OF_SCANS, ScanNextStep.BUY_SCANS)
    else -> ScanUiState.Error(failure.message)
}

// Shows a failed Scan and reads the balance again, since it may have been
// charged and refunded (or not) - except after insufficient_credits, where
// nothing was spent. The view model's two Scan entry points both end here.
fun reportScanFailure(
    failure: ScanResult.Failure,
    show: (ScanUiState.Error) -> Unit,
    refreshBalance: () -> Unit,
) {
    show(scanErrorFor(failure))
    if (failure.code != "insufficient_credits") refreshBalance()
}

// The one rule for starting a Scan from any button: with a balance above zero
// the photo source is offered, otherwise the user goes to the paywall, which
// asks a signed-out user to sign in first (the balance is only known for a
// signed-in account).
fun canStartScan(creditBalance: Int?): Boolean = (creditBalance ?: 0) > 0
