package com.rigcheck.app.ui.screens

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.GCWR_UNCHECKED_CAVEAT
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.computeBreakdown
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.domain.verdictFor
import com.rigcheck.app.ui.GarageNotice
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.testsupport.onNodeWithTagText

@RunWith(AndroidJUnit4::class)
class ResultsScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun item(label: String, tone: Tone, pct: Int, note: String? = null, estimated: Boolean = false) =
        BreakdownItem(
            label = label, tone = tone, actual = 1.0, limit = 1.0, margin = 0.0, pct = pct, note = note,
            estimated = estimated,
        )

    @Test
    fun allPassingRendersSafeToTowVerdict() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Tow Vehicle Total (GVWR)").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_PCT, "85%").assertIsDisplayed()
    }

    @Test
    fun anyFailureRendersNotSafeToTowVerdict() {
        val breakdown = listOf(
            item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85),
            item("Combined Rig Weight", Tone.WARNING, 108),
        )
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Not Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Combined Rig Weight").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_PCT, "108%").assertIsDisplayed()
    }

    // #47: the Combined Rig Weight row exists only when the truck has a GCWR, so these
    // render the real breakdown for a rig rather than a hand-built item list.

    private val gcwrTruck = TruckTag(gvwrLb = 14_000.0, frontGawrLb = 6_000.0, rearGawrLb = 9_500.0)
    private val gcwrTrailer = TrailerTag(gvwrLb = 12_500.0, gawrPerAxleLb = 6_000.0)
    private val gcwrScale = ScaleTicket(
        steerAxleLb = 5_000.0, driveAxleLb = 8_000.0, trailerAxleLb = 9_000.0, grossWeightLb = 22_000.0,
    )

    private fun showResultsFor(truck: TruckTag) {
        val breakdown = computeBreakdown(truck, gcwrTrailer, gcwrScale)
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }
    }

    @Test
    fun combinedRigWeightRowIsHiddenWhenNoGcwrWasEntered() {
        showResultsFor(gcwrTruck)

        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Tow Vehicle Total (GVWR)").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Combined Rig Weight").assertDoesNotExist()
    }

    @Test
    fun combinedRigWeightRowShowsWhenAGcwrWasEntered() {
        showResultsFor(gcwrTruck.copy(gcwrLb = 26_000.0))

        // The sixth row sits below the fold of the card's own list, which composes lazily.
        composeRule.onNode(hasScrollAction()).performScrollToNode(hasTestTag(UiTags.RESULTS_ROW) and hasText("Combined Rig Weight"))
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Combined Rig Weight").assertIsDisplayed()
    }

    // #168: the Verdict's subline sits under the headline. Without a GCWR the Safe to Tow
    // subline carries the caveat, and a user who never sees it is never told the Combined
    // weight went unchecked.

    @Test
    fun safeToTowSublineCarriesGcwrCaveatWhenNoGcwrWasEntered() {
        showResultsFor(gcwrTruck)

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, GCWR_UNCHECKED_CAVEAT, substring = true).assertIsDisplayed()
    }

    @Test
    fun safeToTowSublineHasNoGcwrCaveatWhenAGcwrWasChecked() {
        showResultsFor(gcwrTruck.copy(gcwrLb = 26_000.0))

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Every axle checks out under its rated limit.").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, GCWR_UNCHECKED_CAVEAT, substring = true).assertDoesNotExist()
    }

    @Test
    fun notSafeToTowSublineIsDisplayed() {
        val failing = listOf(item("Combined Rig Weight", Tone.WARNING, 108))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = failing,
                verdict = verdictFor(failing),
                onStartAnother = {},
            )
        }
        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, verdictFor(failing).subline).assertIsDisplayed()
    }

    @Test
    fun allInsufficientRendersNotEnoughInformationVerdict() {
        val breakdown = listOf(item("Front Axle (Steer)", Tone.INSUFFICIENT, 0))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Not Enough Information").assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.RESULTS_ROW_LABEL, "Front Axle (Steer)").assertIsDisplayed()
    }

    @Test
    fun mixedInsufficientAndPassingRendersPartiallyCheckedVerdict() {
        val breakdown = listOf(
            item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85),
            item("Trailer Total (GVWR)", Tone.INSUFFICIENT, 0),
        )
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Partially Checked").assertIsDisplayed()
    }

    @Test
    fun estimatedFiguresNoticeShowsWhenAnyRowIsEstimated() {
        val breakdown = listOf(
            item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85, estimated = true),
        )
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_ESTIMATED_NOTICE, "⚠️ Estimated Figures — Confirm Before You Buy").assertIsDisplayed()
    }

    @Test
    fun estimatedFiguresNoticeHiddenWhenNoRowIsEstimated() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_ESTIMATED_NOTICE, "⚠️ Estimated Figures — Confirm Before You Buy").assertDoesNotExist()
    }

    @Test
    fun rigNicknameIsDisplayed() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
            )
        }

        composeRule.onNodeWithTagText(UiTags.RESULTS_RIG_NAME, "Goose + Addie").assertIsDisplayed()
    }

    @Test
    fun startAnotherCheckButtonInvokesOnStartAnother() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        var started = false
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = { started = true },
            )
        }

        composeRule.onNodeWithTag(UiTags.RESULTS_START_ANOTHER_BUTTON).performClick()

        assert(started) { "onStartAnother should have fired when the button was tapped" }
    }

    // #31: the check went ahead; only its Rig did not reach the Garage.
    private fun showResultsWith(notice: GarageNotice?, onGetPro: () -> Unit = {}) {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
                garageNotice = notice,
                onGetPro = onGetPro,
            )
        }
    }

    @Test
    fun noGarageNoticeIsShownWhenTheRigWasSaved() {
        showResultsWith(notice = null)

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onAllNodesWithTag(UiTags.GARAGE_NOTICE).assertCountEquals(0)
    }

    @Test
    fun aFullGarageNoticeShowsBesideTheVerdictAndOffersProToAFreeAccount() {
        var proOffered = false
        showResultsWith(
            notice = GarageNotice("Your Garage is full (the Free plan holds 5 Rigs), so \"Goose\" wasn't saved to it.", offerPro = true),
            onGetPro = { proOffered = true },
        )

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.GARAGE_NOTICE).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.GARAGE_NOTICE_GET_PRO).performClick()
        assert(proOffered) { "Get Pro should have fired onGetPro" }
    }

    @Test
    fun aGarageNoticeOffersNothingWhenProWouldNotHelp() {
        showResultsWith(notice = GarageNotice("We couldn't save \"Goose\" to your Garage.", offerPro = false))

        composeRule.onNodeWithTag(UiTags.GARAGE_NOTICE).assertIsDisplayed()
        composeRule.onAllNodesWithTag(UiTags.GARAGE_NOTICE_GET_PRO).assertCountEquals(0)
    }

    // #32: the check went ahead; only its History entry did not reach the account.
    @Test
    fun aHistoryNoticeShowsBesideTheVerdictOnlyWhenTheCheckWasNotSaved() {
        val breakdown = listOf(item("Tow Vehicle Total (GVWR)", Tone.SUCCESS, 85))
        var notice by mutableStateOf<String?>(null)
        composeRule.setContent {
            ResultsScreen(
                rigNickname = "Goose + Addie",
                breakdown = breakdown,
                verdict = verdictFor(breakdown),
                onStartAnother = {},
                historyNotice = notice,
            )
        }

        composeRule.onAllNodesWithTag(UiTags.HISTORY_NOTICE).assertCountEquals(0)

        notice = "We couldn't save this check to your History. Your check is not affected."

        composeRule.onNodeWithTagText(UiTags.RESULTS_VERDICT, "Safe to Tow").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.HISTORY_NOTICE).assertIsDisplayed()
    }
}
