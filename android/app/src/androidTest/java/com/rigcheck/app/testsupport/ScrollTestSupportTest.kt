package com.rigcheck.app.testsupport

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// `scrollToIfScrollable()` has to work for a node inside a scrolling column
// (it scrolls to it) and for one with no scrolling container above it, where
// the plain `performScrollTo()` it replaces throws.
@RunWith(AndroidJUnit4::class)
class ScrollTestSupportTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun scrollsANodeBelowTheWindowIntoViewWhenTheContentOverflows() {
        composeRule.setContent {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                Box(Modifier.height(5000.dp))
                Box(Modifier.size(40.dp).testTag("far_below"))
            }
        }

        composeRule.onNodeWithTag("far_below").scrollToIfScrollable().assertIsDisplayed()
    }

    @Test
    fun leavesANodeWhereItIsWhenNothingAboveItScrolls() {
        composeRule.setContent { Box(Modifier.size(40.dp).testTag("not_in_a_scroll")) }

        composeRule.onNodeWithTag("not_in_a_scroll").scrollToIfScrollable().assertIsDisplayed()
    }
}
