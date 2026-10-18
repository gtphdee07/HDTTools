package com.rigcheck.app.ui.screens

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.applyScan
import com.rigcheck.app.ui.navigation.EntryModule
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// The notice on the entry screen reached after a delivered Scan (#120). Each
// test hands the screen what the view model would after the Worker's `fields`
// came back (applyScan), with no Worker, no network and no money. Manual entry
// is the screen with no notice at all.
@RunWith(AndroidJUnit4::class)
class ScanNoticeScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun fields(json: String): JsonObject = Json.parseToJsonElement(json) as JsonObject

    private fun scanned(module: EntryModule, json: String) =
        applyScan(module, fields(json), TruckTag(), TrailerTag(), ScaleTicket())

    private fun showTruck(truck: TruckTag, notice: ScanNotice?) {
        composeRule.setContent {
            var current by remember { mutableStateOf(truck) }
            TruckTagEntryScreen(truck = current, onTruckChange = { current = it }, onContinue = {}, scanNotice = notice)
        }
    }

    @Test
    fun aTruckTagScanThatReadNothingShowsTheNoticeAndNoTryAgain() {
        val applied = scanned(EntryModule.TRUCK, "{}")
        showTruck(applied.truck, applied.notice)

        composeRule.onNodeWithTag("scan_notice").assertIsDisplayed()
        composeRule.onNodeWithText(ScanMessages.NOTHING_READ).assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    @Test
    fun aTruckTagScanThatReadSomeFieldsNamesTheUnreadOnes() {
        val applied = scanned(EntryModule.TRUCK, """{"manufacturer":"Ford","gvwr_lb":10000}""")
        showTruck(applied.truck, applied.notice)

        composeRule.onNodeWithText(ScanMessages.someNotRead(listOf("Front GAWR", "Rear GAWR"))).assertIsDisplayed()
    }

    @Test
    fun aTruckTagScanThatReadEveryFieldShowsNoNotice() {
        val applied = scanned(
            EntryModule.TRUCK,
            """{"manufacturer":"Ford","gvwr_lb":10000,"front_gawr_lb":5000,"rear_gawr_lb":6000}""",
        )
        showTruck(applied.truck, applied.notice)

        composeRule.onNodeWithTag("scan_notice").assertDoesNotExist()
    }

    @Test
    fun manualEntryShowsNoNotice() {
        showTruck(TruckTag(), notice = null)

        composeRule.onNodeWithTag("scan_notice").assertDoesNotExist()
    }

    @Test
    fun theNoticeGoesAwayOnceTheMissingFieldIsTypedIn() {
        val applied = scanned(EntryModule.TRUCK, """{"gvwr_lb":10000,"front_gawr_lb":5000,"rear_gawr_lb":6000}""")
        showTruck(applied.truck, applied.notice)
        composeRule.onNodeWithTag("scan_notice").assertIsDisplayed()

        composeRule.onNodeWithTag("truck_description").performScrollTo().performTextInput("Ford F-450")

        composeRule.onNodeWithTag("scan_notice").assertDoesNotExist()
    }

    @Test
    fun aTrailerTagScanThatReadNothingShowsTheNotice() {
        val applied = scanned(EntryModule.TRAILER, "{}")
        composeRule.setContent {
            TrailerTagEntryScreen(
                trailer = applied.trailer,
                onTrailerChange = {},
                onContinue = {},
                scanNotice = applied.notice,
            )
        }

        composeRule.onNodeWithText(ScanMessages.NOTHING_READ).assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    @Test
    fun aTrailerTagScanThatReadSomeFieldsNamesTheUnreadOnes() {
        val applied = scanned(EntryModule.TRAILER, """{"manufacturer":"Brinkley","gvwr_lb":14000}""")
        composeRule.setContent {
            TrailerTagEntryScreen(
                trailer = applied.trailer,
                onTrailerChange = {},
                onContinue = {},
                scanNotice = applied.notice,
            )
        }

        composeRule
            .onNodeWithText(ScanMessages.someNotRead(listOf("GAWR per axle", "Unloaded weight (UVW)")))
            .assertIsDisplayed()
    }

    @Test
    fun aTrailerTagScanThatReadEveryFieldShowsNoNotice() {
        val applied = scanned(
            EntryModule.TRAILER,
            """{"manufacturer":"Brinkley","gvwr_lb":14000,"gawr_per_axle_lb":7000,"uvw_lb":11000}""",
        )
        composeRule.setContent {
            TrailerTagEntryScreen(
                trailer = applied.trailer,
                onTrailerChange = {},
                onContinue = {},
                scanNotice = applied.notice,
            )
        }

        composeRule.onNodeWithTag("scan_notice").assertDoesNotExist()
    }

    @Test
    fun aScaleTicketScanThatReadNothingShowsTheNotice() {
        val applied = scanned(EntryModule.SCALE, "{}")
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = applied.scale, onScaleChange = {}, onContinue = {}, scanNotice = applied.notice)
        }

        composeRule.onNodeWithText(ScanMessages.NOTHING_READ).assertIsDisplayed()
        composeRule.onNodeWithText("Try again").assertDoesNotExist()
    }

    @Test
    fun aScaleTicketScanThatReadSomeFieldsNamesTheUnreadOnes() {
        val applied = scanned(
            EntryModule.SCALE,
            """{"location_name":"Flying J","steer_axle_lb":12000,"drive_axle_lb":30000,"gross_weight_lb":67000}""",
        )
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = applied.scale, onScaleChange = {}, onContinue = {}, scanNotice = applied.notice)
        }

        composeRule.onNodeWithText(ScanMessages.someNotRead(listOf("Trailer axle(s)"))).assertIsDisplayed()
    }

    @Test
    fun aScaleTicketScanThatReadEveryFieldShowsNoNotice() {
        val applied = scanned(
            EntryModule.SCALE,
            """{"location_name":"Flying J","steer_axle_lb":12000,"drive_axle_lb":30000,""" +
                """"trailer_axle_lb":25000,"gross_weight_lb":67000}""",
        )
        composeRule.setContent {
            ScaleTicketEntryScreen(scale = applied.scale, onScaleChange = {}, onContinue = {}, scanNotice = applied.notice)
        }

        composeRule.onNodeWithTag("scan_notice").assertDoesNotExist()
    }
}
