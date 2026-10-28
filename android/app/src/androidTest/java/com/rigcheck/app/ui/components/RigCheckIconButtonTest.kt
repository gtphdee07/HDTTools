package com.rigcheck.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertContentDescriptionEquals
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Icon button (48)": a 48 dp circle over the teal bar or on the page, with a content description, a
// pressed ripple and a disabled state at 38%.
@RunWith(AndroidJUnit4::class)
class RigCheckIconButtonTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun show(onTeal: Boolean, enabled: Boolean = true, onClick: () -> Unit = {}) =
        composeRule.setRigCheckContent {
            RigCheckIconButton(Icons.AutoMirrored.Filled.ArrowBack, "Back", onClick, Modifier.testTag("icon"), enabled, onTeal)
        }

    @Test
    fun overTheTealBarIsA48dpTappableCircleWithItsDescription() {
        var clicks = 0
        show(onTeal = true, onClick = { clicks++ })
        composeRule.onNodeWithTag("icon").assertContentDescriptionEquals("Back").assertIsEnabled()
            .assertWidthIsEqualTo(48.dp).assertHeightIsEqualTo(48.dp).performClick()
        assertEquals(1, clicks)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        val colors = rigCheckIconButtonColors(onTeal = true)
        assertAa("glyph on the wash over teal", colors.icon, colors.container, behind = colors.behind)
    }

    @Test
    fun onThePageIsA48dpTappableCircleWithItsDescription() {
        var clicks = 0
        show(onTeal = false, onClick = { clicks++ })
        composeRule.onNodeWithTag("icon").assertContentDescriptionEquals("Back")
            .assertWidthIsEqualTo(48.dp).assertHeightIsEqualTo(48.dp).performClick()
        assertEquals(1, clicks)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        val colors = rigCheckIconButtonColors(onTeal = false)
        assertAa("glyph on the page", colors.icon, colors.behind)
    }

    @Test
    fun disabledIgnoresTapsAndKeepsItsSize() {
        var clicks = 0
        show(onTeal = true, enabled = false, onClick = { clicks++ })
        composeRule.onNodeWithTag("icon").assertIsNotEnabled().assertWidthIsEqualTo(48.dp).performClick()
        assertEquals(0, clicks)
    }
}
