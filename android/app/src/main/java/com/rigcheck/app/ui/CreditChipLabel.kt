package com.rigcheck.app.ui

/**
 * The text of the scan balance chip (copy-changes.md, 2026-10-27 owner feedback). The balance is null while it is not
 * known: signed out there is no balance and the chip says "0 scans" (nothing can be scanned), and only an account
 * that is signed in, or still being looked up, shows "…" while its balance loads.
 */
fun creditChipLabel(balance: Int?, signedOut: Boolean): String = when {
    balance != null -> scansText(balance)
    signedOut -> scansText(0)
    else -> "…"
}

/** What a screen reader says for the chip: the same balance in words, and where a tap leads. */
fun creditChipDescription(balance: Int?, signedOut: Boolean): String {
    val figure = if (balance == null && !signedOut) "loading" else creditChipLabel(balance, signedOut)
    return "Scan balance: $figure. Opens the Paywall"
}

private fun scansText(count: Int) = "$count scan${if (count == 1) "" else "s"}"
