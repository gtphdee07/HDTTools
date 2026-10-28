package com.rigcheck.app.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class CreditChipLabelTest {

    @Test
    fun signedOutSaysZeroScansNotThePlaceholder() {
        assertEquals("0 scans", creditChipLabel(balance = null, signedOut = true))
    }

    @Test
    fun anAccountWhoseBalanceIsStillLoadingKeepsThePlaceholder() {
        assertEquals("…", creditChipLabel(balance = null, signedOut = false))
    }

    @Test
    fun aKnownBalanceUsesSingularForOneAndPluralOtherwise() {
        assertEquals("0 scans", creditChipLabel(0, signedOut = false))
        assertEquals("1 scan", creditChipLabel(1, signedOut = false))
        assertEquals("12 scans", creditChipLabel(12, signedOut = false))
    }

    @Test
    fun theSpokenDescriptionNamesTheBalanceAndWhereATapLeads() {
        assertEquals("Scan balance: 12 scans. Opens the Paywall", creditChipDescription(12, signedOut = false))
        assertEquals("Scan balance: 1 scan. Opens the Paywall", creditChipDescription(1, signedOut = false))
        assertEquals("Scan balance: 0 scans. Opens the Paywall", creditChipDescription(null, signedOut = true))
        // The placeholder dots are not read out as "dot dot dot".
        assertEquals("Scan balance: loading. Opens the Paywall", creditChipDescription(null, signedOut = false))
    }
}
