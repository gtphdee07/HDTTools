package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.down
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.assertReadableWhenDisabled
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.Surface
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Button": primary / secondary / ghost / destructive, in the states default, pressed and disabled, at
// the sizes regular (56), compact (48) and dialog (52).
@RunWith(AndroidJUnit4::class)
class RigCheckButtonTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun show(
        kind: RigCheckButtonKind,
        size: RigCheckButtonSize = RigCheckButtonSize.Regular,
        enabled: Boolean = true,
        onClick: () -> Unit = {},
    ) = composeRule.setRigCheckContent {
        RigCheckButton("Check weights", onClick, Modifier.testTag("button"), kind = kind, size = size, enabled = enabled)
    }

    @Test
    fun defaultStateOfEveryKindIsReadable() {
        for (kind in RigCheckButtonKind.entries) {
            val colors = rigCheckButtonColors(kind, RigCheckButtonState.Default)
            // A ghost button has no fill of its own: its text sits on the page.
            assertAa("$kind default", colors.content, if (colors.container.alpha == 0f) Surface else colors.container)
        }
    }

    @Test
    fun primaryIsTappableAndAtLeast56dpHigh() {
        var clicks = 0
        show(RigCheckButtonKind.Primary, onClick = { clicks++ })
        composeRule.onNodeWithTag("button").assertIsDisplayed().assertIsEnabled().assertHeightIsAtLeast(56.dp).performClick()
        assertEquals(1, clicks)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun secondaryIsTappableAndAtLeast56dpHigh() {
        show(RigCheckButtonKind.Secondary)
        composeRule.onNodeWithTag("button").assertHeightIsAtLeast(56.dp)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun ghostIsTappableAndAtLeast56dpHigh() {
        show(RigCheckButtonKind.Ghost)
        composeRule.onNodeWithTag("button").assertHeightIsAtLeast(56.dp)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun destructiveIsTappableAndAtLeast56dpHigh() {
        show(RigCheckButtonKind.Destructive)
        composeRule.onNodeWithTag("button").assertHeightIsAtLeast(56.dp)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun pressedStateOfEveryKindIsReadable() {
        for (kind in RigCheckButtonKind.entries) {
            val colors = rigCheckButtonColors(kind, RigCheckButtonState.Pressed)
            assertAa("$kind pressed", colors.content, colors.container)
        }
    }

    @Test
    fun aPressedButtonStaysShownAndTappableSize() {
        show(RigCheckButtonKind.Primary)
        composeRule.onNodeWithTag("button").performTouchInput { down(center) }
        composeRule.onNodeWithTag("button").assertIsDisplayed().assertHeightIsAtLeast(56.dp)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun pressedPrimaryChangesTheFillAndTheTextColour() {
        val default = rigCheckButtonColors(RigCheckButtonKind.Primary, RigCheckButtonState.Default)
        val pressed = rigCheckButtonColors(RigCheckButtonKind.Primary, RigCheckButtonState.Pressed)
        assertTrue(default.container != pressed.container && default.content != pressed.content)
    }

    @Test
    fun disabledButtonsIgnoreTapsAndStayReadable() {
        for (kind in RigCheckButtonKind.entries) {
            val colors = rigCheckButtonColors(kind, RigCheckButtonState.Disabled)
            assertReadableWhenDisabled("$kind", colors.content, colors.container)
            assertEquals("a disabled $kind button has no border", null, colors.border)
        }
        var clicks = 0
        show(RigCheckButtonKind.Primary, enabled = false, onClick = { clicks++ })
        composeRule.onNodeWithTag("button").assertIsNotEnabled().performClick()
        assertEquals(0, clicks)
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun compactButtonIs48dpHighAndHugsItsLabel() {
        show(RigCheckButtonKind.Ghost, size = RigCheckButtonSize.Compact)
        val node = composeRule.onNodeWithTag("button")
        node.assertHeightIsAtLeast(48.dp)
        val width = node.fetchSemanticsNode().size.width
        val page = composeRule.onRoot().fetchSemanticsNode().size.width
        assertTrue("a compact button must not fill the page ($width of $page px)", width < page / 2)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }

    @Test
    fun dialogButtonIs52dpHigh() {
        show(RigCheckButtonKind.Primary, size = RigCheckButtonSize.Dialog)
        composeRule.onNodeWithTag("button").assertHeightIsAtLeast(52.dp)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
    }
}
