package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.setRigCheckContent
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Text field" and "Reference card": the orange numbered badge, 22 dp in front of a label (24 dp on the
// photo and in the legend), an ink digit.
@RunWith(AndroidJUnit4::class)
class RigCheckNumberBadgeTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun theBadgeShowsItsNumberAt22DpAndTheSizeItIsGiven() {
        composeRule.setRigCheckContent {
            RigCheckNumberBadge(3, modifier = Modifier.testTag("small"))
            RigCheckNumberBadge(5, size = 24.dp, modifier = Modifier.testTag("large"))
        }

        composeRule.onNodeWithText("3").assertIsDisplayed()
        composeRule.onNodeWithText("5").assertIsDisplayed()
        composeRule.onNodeWithTag("small").assertWidthIsEqualTo(22.dp).assertHeightIsEqualTo(22.dp)
        composeRule.onNodeWithTag("large").assertWidthIsEqualTo(24.dp).assertHeightIsEqualTo(24.dp)
    }

    @Test
    fun theDigitMeetsAaOnTheOrange() {
        assertAa("the badge digit", RigCheckNumberBadgeColors.digit, RigCheckNumberBadgeColors.fill)
    }
}
