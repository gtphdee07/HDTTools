package com.rigcheck.app.ui.components

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.Teal
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Account status row" and "Bottom sheet": the Rig picker's header row says who is signed in (or that
// nobody is) and the sheet it opens offers Sign out.
@RunWith(AndroidJUnit4::class)
class RigCheckAccountStatusTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun aSignedInRowShowsTheEmailAndItsInitialAndOpensTheMenu() {
        var opened = 0
        composeRule.setRigCheckContent {
            RigCheckAccountStatus(RigCheckAccount.SignedIn("dana.rivera@example.com"), onClick = { opened++ })
        }

        composeRule.onNodeWithText("Signed in as").assertIsDisplayed()
        composeRule.onNodeWithText("dana.rivera@example.com").assertIsDisplayed()
        composeRule.onNodeWithText("D").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Account: signed in as dana.rivera@example.com. Opens account menu").performClick()

        assertEquals(1, opened)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun aSignedOutRowSaysSoAndOffersSignIn() {
        var opened = 0
        composeRule.setRigCheckContent { RigCheckAccountStatus(RigCheckAccount.SignedOut, onClick = { opened++ }) }

        composeRule.onNodeWithText("Not signed in").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Not signed in. Sign in").performClick()

        assertEquals(1, opened)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun theTextOnTheWashAndTheAvatarInitialMeetAA() {
        // The wash is 72% white over the teal bar, so the contrast is worked out over teal.
        assertAa("the row's text", RigCheckAccountStatusColors.text, RigCheckAccountStatusColors.fill, behind = Teal)
        assertAa("the Sign in label", RigCheckAccountStatusColors.signInLabel, RigCheckAccountStatusColors.fill, behind = Teal)
        assertAa("the initial on the avatar", RigCheckAccountStatusColors.avatarInitial, RigCheckAccountStatusColors.avatarFill)
    }

    @Test
    fun theInitialIsTheFirstLetterOfTheAccountInCapitals() {
        assertEquals("D", accountInitial("dana.rivera@example.com"))
        assertEquals("A", accountInitial("  anna@example.com"))
        assertEquals("", accountInitial(""))
    }

    @Test
    fun theSheetShowsTheAccountAndSignsOutOrCancels() {
        var signedOut = 0
        var dismissed = 0
        composeRule.setRigCheckContent {
            RigCheckAccountSheet(
                account = RigCheckAccount.SignedIn("dana.rivera@example.com"),
                onSignOut = { signedOut++ },
                onDismiss = { dismissed++ },
            )
        }
        composeRule.waitForIdle()

        composeRule.onNodeWithText("dana.rivera@example.com").assertIsDisplayed()
        composeRule.onNodeWithText("Sign out").performClick()
        assertEquals(1 to 0, signedOut to dismissed)
        composeRule.onNodeWithText("Cancel").performClick()
        assertEquals(1 to 1, signedOut to dismissed)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 2)
    }
}
