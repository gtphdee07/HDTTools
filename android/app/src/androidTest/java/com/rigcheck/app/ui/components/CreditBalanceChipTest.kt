package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.ui.UiTags
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CreditBalanceChipTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val chip = Modifier.testTag(UiTags.PICKER_CREDIT_CHIP)

    @Test
    fun nullBalanceShowsNotYetLoadedPlaceholder() {
        composeRule.setContent { CreditBalanceChip(balance = null, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "…").assertIsDisplayed()
    }

    @Test
    fun zeroBalanceUsesPluralWording() {
        composeRule.setContent { CreditBalanceChip(balance = 0, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "0 scans").assertIsDisplayed()
    }

    @Test
    fun oneBalanceUsesSingularWording() {
        composeRule.setContent { CreditBalanceChip(balance = 1, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "1 scan").assertIsDisplayed()
    }

    @Test
    fun multipleBalanceUsesPluralWording() {
        composeRule.setContent { CreditBalanceChip(balance = 5, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "5 scans").assertIsDisplayed()
    }

    @Test
    fun onClickFiresWhenProvided() {
        var clicked = false
        composeRule.setContent { CreditBalanceChip(balance = 5, modifier = chip, onClick = { clicked = true }) }

        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).performClick()

        assert(clicked) { "onClick should have fired" }
    }
}
