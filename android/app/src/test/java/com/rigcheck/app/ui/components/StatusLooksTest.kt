package com.rigcheck.app.ui.components

import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictStatus
import org.junit.Assert.assertEquals
import org.junit.Test

// #194: a failing row and a failing verdict are told from a passing one by more than colour (the ticket's second
// criterion). Each outcome has its own icon (the shape) and its own words; the colour comes on top. On the JVM, with no
// device: the looks are plain data. ResultsScreenTest shows the same words on the screen.
class StatusLooksTest {

    @Test
    fun theThreeRowTonesHaveThreeShapesAndThreeSetsOfWords() {
        val looks = listOf(Tone.SUCCESS, Tone.WARNING, Tone.INSUFFICIENT).map(::rigCheckRowLook)

        assertEquals(3, looks.map { it.icon }.toSet().size)
        assertEquals(listOf("Within limit", "Over limit", "Not checked"), looks.map { it.badgeText })
        assertEquals(3, looks.map { it.badgeKind }.toSet().size)
    }

    @Test
    fun theVerdictOutcomesDifferInShapeAsWellAsFill() {
        val pass = rigCheckVerdictLook(VerdictStatus.PASS)
        val fail = rigCheckVerdictLook(VerdictStatus.FAIL)
        val partial = rigCheckVerdictLook(VerdictStatus.PARTIAL)

        assertEquals(3, listOf(pass.icon, fail.icon, partial.icon).toSet().size)
        assertEquals("the two unsure outcomes share a look", partial, rigCheckVerdictLook(VerdictStatus.INSUFFICIENT))
    }
}
