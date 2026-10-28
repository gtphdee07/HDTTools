package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Progress bar": 10 dp, pass / fail / not checked, and a fill over 100% stops at the bar's end.
@RunWith(AndroidJUnit4::class)
class RigCheckProgressBarTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun valueShown(fraction: Float, tone: RigCheckProgressTone): Float {
        composeRule.setRigCheckContent { RigCheckProgressBar(fraction, tone, Modifier.testTag("bar")) }
        composeRule.onNodeWithTag("bar").assertHeightIsEqualTo(10.dp)
        composeRule.assertEveryClickableIsAtLeast48dp()
        assertAa("$tone fill on the track", rigCheckProgressFill(tone), ProgressTrack, largeText = true)
        return composeRule.onNodeWithTag("bar").fetchSemanticsNode().config[SemanticsProperties.ProgressBarRangeInfo].current
    }

    @Test
    fun passBar() = assertEquals(0.87f, valueShown(0.87f, RigCheckProgressTone.Pass), 0.001f)

    @Test
    fun failBarOverTheLimitStopsAtTheEnd() = assertEquals(1f, valueShown(1.12f, RigCheckProgressTone.Fail), 0.001f)

    @Test
    fun notCheckedBarIsEmpty() = assertEquals(0f, valueShown(0f, RigCheckProgressTone.NotChecked), 0.001f)

    @Test
    fun aNegativeFractionIsTreatedAsEmpty() = assertEquals(0f, valueShown(-0.2f, RigCheckProgressTone.Pass), 0.001f)
}
