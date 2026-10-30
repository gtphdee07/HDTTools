package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.Pine
import com.rigcheck.app.ui.theme.Purple
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Verdict band": Safe (pine), Not Safe (danger), Partially Checked and Not Enough Information (purple).
@RunWith(AndroidJUnit4::class)
class RigCheckVerdictBandTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun verdict(status: VerdictStatus, tone: Tone, headline: String) =
        VerdictInfo(headline = headline, subline = "Subline for $headline", tone = tone, status = status)

    private fun showAndAssert(info: VerdictInfo, expectedFill: Color) {
        composeRule.setRigCheckContent { RigCheckVerdictBand(info) }
        composeRule.onNodeWithText(info.headline).assertIsDisplayed()
        composeRule.onNodeWithText(info.subline).assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
        val look = rigCheckVerdictLook(info.status)
        assertEquals(expectedFill, look.fill)
        // The headline is 30 sp bold (large text); the subline is 15 sp and must meet 4.5:1 on the same fill.
        assertAa("${info.headline} headline", look.text, look.fill, largeText = true)
        assertAa("${info.headline} subline", look.text, look.fill)
    }

    @Test
    fun safeToTowIsPine() = showAndAssert(verdict(VerdictStatus.PASS, Tone.SUCCESS, "Safe to Tow"), Pine)

    @Test
    fun notSafeToTowIsDanger() = showAndAssert(verdict(VerdictStatus.FAIL, Tone.WARNING, "Not Safe to Tow"), DangerRed)

    @Test
    fun partiallyCheckedIsPurple() = showAndAssert(verdict(VerdictStatus.PARTIAL, Tone.INSUFFICIENT, "Partially Checked"), Purple)

    @Test
    fun notEnoughInformationIsPurple() =
        showAndAssert(verdict(VerdictStatus.INSUFFICIENT, Tone.INSUFFICIENT, "Not Enough Information"), Purple)

    // The map's `results.verdict_icon` is the 64 dp circle, not the 36 dp glyph in it.
    @Test
    fun theIconModifierLandsOnTheSixtyFourDpCircle() {
        val info = verdict(VerdictStatus.PASS, Tone.SUCCESS, "Safe to Tow")
        composeRule.setRigCheckContent { RigCheckVerdictBand(info, iconModifier = Modifier.testTag("circle")) }
        composeRule.onNodeWithTag("circle", useUnmergedTree = true).assertWidthIsEqualTo(64.dp).assertHeightIsEqualTo(64.dp)
    }

    @Test
    fun theThreeKindsOfOutcomeDifferInIconAsWellAsColour() {
        val pass = rigCheckVerdictLook(VerdictStatus.PASS)
        val fail = rigCheckVerdictLook(VerdictStatus.FAIL)
        val unsure = rigCheckVerdictLook(VerdictStatus.PARTIAL)
        assertNotEquals(pass.icon, fail.icon)
        assertNotEquals(pass.icon, unsure.icon)
        assertNotEquals(fail.icon, unsure.icon)
    }
}
