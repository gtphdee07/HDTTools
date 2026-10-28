package com.rigcheck.app.ui.components

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsFocused
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.assertReadableWhenDisabled
import com.rigcheck.app.testsupport.setRigCheckContent
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Surface
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Text field (and number field with unit)": default, focused, error and disabled.
@RunWith(AndroidJUnit4::class)
class RigCheckTextFieldTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun show(
        initial: String = "",
        placeholder: String? = null,
        unit: String? = null,
        help: String? = null,
        error: String? = null,
        enabled: Boolean = true,
        numeric: Boolean = false,
    ): () -> String {
        var current = initial
        composeRule.setRigCheckContent {
            var value by remember { mutableStateOf(initial) }
            RigCheckTextField(
                label = "Axle weight",
                value = value,
                onValueChange = { value = it; current = it },
                inputModifier = Modifier.testTag("field"),
                placeholder = placeholder,
                unit = unit,
                help = help,
                error = error,
                enabled = enabled,
                numeric = numeric,
            )
        }
        return { current }
    }

    @Test
    fun defaultFieldShowsItsLabelAndPlaceholderAndTakesTyping() {
        val value = show(placeholder = "e.g. 5200")
        composeRule.onNodeWithText("Axle weight").assertIsDisplayed()
        composeRule.onNodeWithText("e.g. 5200").assertIsDisplayed()
        composeRule.onNodeWithTag("field").assertHeightIsAtLeast(56.dp).performTextInput("5200")
        assertEquals("5200", value())
        composeRule.assertEveryClickableIsAtLeast48dp()
        val colors = rigCheckFieldColors(RigCheckFieldState.Default)
        assertAa("value", colors.value, colors.container)
        assertAa("placeholder", colors.hint, colors.container)
        // The outline of an input must be visible against the page: 3:1 (WCAG 1.4.11).
        assertAa("outline", colors.border, Surface, largeText = true)
    }

    @Test
    fun tappingTheFieldFocusesItAndTheFocusedColoursApply() {
        show()
        composeRule.onNodeWithTag("field").performClick()
        composeRule.onNodeWithTag("field").assertIsFocused()
        val colors = rigCheckFieldColors(RigCheckFieldState.Focused)
        assertTrue("a focused field draws the 4 dp ring", colors.focusRing)
        assertAa("value (focused)", colors.value, colors.container)
        assertAa("focus border", colors.border, Surface, largeText = true)
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun errorFieldNamesTheProblemInWordsAndInDangerText() {
        show(initial = "12", error = "Enter a weight in pounds")
        composeRule.onNodeWithText("Enter a weight in pounds").assertIsDisplayed()
        val colors = rigCheckFieldColors(RigCheckFieldState.Error)
        assertAa("error message", DangerText, colors.container)
        assertAa("error border", colors.border, Surface, largeText = true)
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun disabledFieldCannotBeEditedAndStaysReadable() {
        show(initial = "5200", enabled = false)
        composeRule.onNodeWithTag("field").assertIsNotEnabled()
        val colors = rigCheckFieldColors(RigCheckFieldState.Disabled)
        assertReadableWhenDisabled("value", colors.value, colors.container)
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun numberFieldShowsItsUnitAndAHelpLine() {
        show(initial = "5200", unit = "lb", help = "From the scale ticket", numeric = true)
        composeRule.onNodeWithText("lb").assertIsDisplayed()
        composeRule.onNodeWithText("From the scale ticket").assertIsDisplayed()
        composeRule.onNodeWithTag("field").assertTextContains("5200")
        assertAa("help line", InkMuted, Surface)
        composeRule.assertEveryClickableIsAtLeast48dp()
    }

    @Test
    fun anErrorReplacesTheHelpLine() {
        show(help = "From the scale ticket", error = "Enter a weight in pounds")
        composeRule.onNodeWithText("Enter a weight in pounds").assertIsDisplayed()
        composeRule.onNodeWithText("From the scale ticket").assertDoesNotExist()
    }
}
