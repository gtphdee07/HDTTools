package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CreditBalanceChipTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun nullBalanceShowsNotYetLoadedPlaceholder() {
        composeRule.setContent { CreditBalanceChip(balance = null) }
        composeRule.onNodeWithText("…").assertIsDisplayed()
    }

    @Test
    fun zeroBalanceUsesPluralWording() {
        composeRule.setContent { CreditBalanceChip(balance = 0) }
        composeRule.onNodeWithText("0 scans").assertIsDisplayed()
    }

    @Test
    fun oneBalanceUsesSingularWording() {
        composeRule.setContent { CreditBalanceChip(balance = 1) }
        composeRule.onNodeWithText("1 scan").assertIsDisplayed()
    }

    @Test
    fun multipleBalanceUsesPluralWording() {
        composeRule.setContent { CreditBalanceChip(balance = 5) }
        composeRule.onNodeWithText("5 scans").assertIsDisplayed()
    }

    @Test
    fun onClickFiresWhenProvided() {
        var clicked = false
        composeRule.setContent { CreditBalanceChip(balance = 5, onClick = { clicked = true }) }

        composeRule.onNodeWithText("5 scans").performClick()

        assert(clicked) { "onClick should have fired" }
    }
}
