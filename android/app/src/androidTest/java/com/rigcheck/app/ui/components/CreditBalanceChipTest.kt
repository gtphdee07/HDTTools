package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertContentDescriptionEquals
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.testsupport.setRigCheckContent
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
    fun aSignedInAccountWhoseBalanceIsLoadingShowsThePlaceholder() {
        composeRule.setRigCheckContent { CreditBalanceChip(balance = null, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "…").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).assertContentDescriptionEquals("Scan balance: loading. Opens the Paywall")
    }

    @Test
    fun signedOutShowsZeroScansNotThePlaceholder() {
        composeRule.setRigCheckContent { CreditBalanceChip(balance = null, signedOut = true, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "0 scans").assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).assertContentDescriptionEquals("Scan balance: 0 scans. Opens the Paywall")
    }

    @Test
    fun zeroBalanceUsesPluralWording() {
        composeRule.setRigCheckContent { CreditBalanceChip(balance = 0, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "0 scans").assertIsDisplayed()
    }

    @Test
    fun oneBalanceUsesSingularWording() {
        composeRule.setRigCheckContent { CreditBalanceChip(balance = 1, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "1 scan").assertIsDisplayed()
    }

    @Test
    fun multipleBalanceUsesPluralWording() {
        composeRule.setRigCheckContent { CreditBalanceChip(balance = 5, modifier = chip) }
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "5 scans").assertIsDisplayed()
    }

    @Test
    fun onClickFiresWhenProvided() {
        var clicked = false
        composeRule.setRigCheckContent { CreditBalanceChip(balance = 5, modifier = chip, onClick = { clicked = true }) }

        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).performClick()

        assert(clicked) { "onClick should have fired" }
    }

    @Test
    fun theChipIsAtLeast48dpHighAndItsTouchTargetIsAtLeast48dpSquare() {
        // The owner's phone feedback of 2026-10-27: the chip was too small to hit.
        composeRule.setRigCheckContent { CreditBalanceChip(balance = 5, modifier = chip, onClick = {}) }
        composeRule.onNodeWithTag(UiTags.PICKER_CREDIT_CHIP).assertHeightIsAtLeast(48.dp)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        assertAa("balance text on the chip", CreditChipColors.content, CreditChipColors.fill)
    }

    @Test
    fun aChipWithNoClickHandlerIsNotTappable() {
        composeRule.setRigCheckContent { CreditBalanceChip(balance = 5, modifier = chip) }
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 0)
        composeRule.onNodeWithTagText(UiTags.PICKER_CREDIT_CHIP, "5 scans").assertIsDisplayed()
    }
}
