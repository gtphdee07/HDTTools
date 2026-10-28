package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.UiTags
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #118: the dialog for a Scan that answered after the user left its check.
@RunWith(AndroidJUnit4::class)
class LateScanDialogTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun showsTheMessageAndOnlyOk() {
        composeRule.setContent { LateScanDialog(message = ScanMessages.RESULT_NOT_USED, onDismiss = {}) }

        composeRule.onNodeWithTagText(
            UiTags.LATE_SCAN_MESSAGE,
            "A Scan finished after you left that check, so its result wasn't used. It used a Scan Credit.",
        ).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.LATE_SCAN_OK_BUTTON).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_TRY_AGAIN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_SIGN_IN).assertDoesNotExist()
        composeRule.onNodeWithTag(UiTags.SCAN_ERROR_NEXT_CHOOSE_PHOTO).assertDoesNotExist()
    }

    @Test
    fun okDismisses() {
        var dismissed = 0
        composeRule.setContent { LateScanDialog(message = "m", onDismiss = { dismissed++ }) }

        composeRule.onNodeWithTag(UiTags.LATE_SCAN_OK_BUTTON).performClick()

        assertEquals(1, dismissed)
    }
}
