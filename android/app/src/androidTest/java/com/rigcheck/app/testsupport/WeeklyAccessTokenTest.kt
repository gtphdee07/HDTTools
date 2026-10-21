package com.rigcheck.app.testsupport

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

// Function tests for how the External suite learns who it is (#75):
// test-weekly.ps1 signs in the funded Supabase test user, writes the account
// id into the device marker file and passes the access token as an
// instrumentation argument. These cover reading both back, with the lookup
// injected, so nothing here touches the device's arguments or the network.
@RunWith(AndroidJUnit4::class)
class WeeklyAccessTokenTest {

    @Test
    fun theTokenIsTheValueOfTheWeeklyAccessTokenArgument() {
        val args = mapOf("weeklyAccessToken" to "header.payload.signature")

        assertEquals("header.payload.signature", requireWeeklyArg(WEEKLY_ACCESS_TOKEN_ARG) { args[it] })
    }

    @Test
    fun aMissingArgumentFailsNamingTheArgument() {
        val failure = assertThrows(IllegalStateException::class.java) {
            requireWeeklyArg(WEEKLY_ACCESS_TOKEN_ARG) { null }
        }

        assertTrue(failure.message!!.contains("weeklyAccessToken"))
    }

    @Test
    fun aBlankArgumentIsTreatedAsMissing() {
        val failure = assertThrows(IllegalStateException::class.java) {
            requireWeeklyArg(WEEKLY_ACCESS_TOKEN_ARG) { "   " }
        }

        assertTrue(failure.message!!.contains("weeklyAccessToken"))
    }

    @Test
    fun theAccountIdIsTheMarkerFilesTextWithoutItsLineEnding() {
        assertEquals(
            "11111111-2222-3333-4444-555555555555",
            weeklyAccountIdFromMarker("11111111-2222-3333-4444-555555555555\r\n"),
        )
    }

    @Test
    fun anEmptyMarkerFailsBecauseTheSuiteWouldBuyAgainstTheWrongCustomer() {
        val failure = assertThrows(IllegalStateException::class.java) { weeklyAccountIdFromMarker("\n") }

        assertTrue(failure.message!!.contains("test-weekly.ps1"))
    }
}
