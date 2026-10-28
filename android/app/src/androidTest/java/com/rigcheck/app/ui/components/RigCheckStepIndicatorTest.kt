package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Step indicator": Truck, Trailer, Scale; the caption "Step n of 3"; done, current and upcoming.
@RunWith(AndroidJUnit4::class)
class RigCheckStepIndicatorTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun assertEveryStatusReadable() {
        for (status in RigCheckStepStatus.entries) {
            val colors = rigCheckStepColors(status)
            assertAa("$status step", colors.content, colors.fill)
        }
    }

    @Test
    fun stepOneMarksTruckCurrent() {
        composeRule.setRigCheckContent { RigCheckStepIndicator(step = 1) }
        composeRule.onNodeWithText("Step 1 of 3").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Step 1 of 3: Truck").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
        assertEveryStatusReadable()
    }

    @Test
    fun stepTwoMarksTruckDoneAndTrailerCurrent() {
        composeRule.setRigCheckContent { RigCheckStepIndicator(step = 2) }
        composeRule.onNodeWithContentDescription("Step 2 of 3: Trailer").assertIsDisplayed()
        composeRule.onNodeWithText("Trailer").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun stepThreeMarksScaleCurrent() {
        composeRule.setRigCheckContent { RigCheckStepIndicator(step = 3) }
        composeRule.onNodeWithContentDescription("Step 3 of 3: Scale").assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun theIndicatorCountsOnlyTheThreeDocuments() {
        assertEquals(listOf("Truck", "Trailer", "Scale"), StepLabels)
    }

    @Test
    fun anUpcomingStepIsToldFromADoneOneByFillAndBorder() {
        val done = rigCheckStepColors(RigCheckStepStatus.Done)
        val upcoming = rigCheckStepColors(RigCheckStepStatus.Upcoming)
        assertEquals(null, done.border)
        assertEquals(upcoming.content, upcoming.border)
    }
}
