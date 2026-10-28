package com.rigcheck.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
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

// components.md, "Option card": Scan Photo (purple) and Enter Manually (teal), the same size.
@RunWith(AndroidJUnit4::class)
class RigCheckOptionCardTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun assertReadable(kind: RigCheckOptionKind) {
        val colors = rigCheckOptionColors(kind)
        assertAa("$kind title", colors.title, colors.container)
        assertAa("$kind description", colors.description, colors.container)
        assertAa("$kind icon on its circle", colors.icon, colors.iconCircle, largeText = true)
        assertAa("$kind border", colors.border, colors.container, largeText = true)
    }

    @Test
    fun scanCardShowsTitleDescriptionAndBadgeAndIsTappable() {
        var clicks = 0
        composeRule.setRigCheckContent {
            RigCheckOptionCard(
                kind = RigCheckOptionKind.Scan,
                title = "Scan Photo",
                description = "Read the tag from a photo — uses 1 scan.",
                icon = Icons.Filled.CameraAlt,
                onClick = { clicks++ },
                modifier = Modifier.testTag("card"),
                badge = { RigCheckBadge("1 scan", RigCheckBadgeKind.Credit) },
            )
        }
        composeRule.onNodeWithText("Scan Photo").assertIsDisplayed()
        composeRule.onNodeWithText("1 scan").assertIsDisplayed()
        composeRule.onNodeWithTag("card").assertHeightIsAtLeast(148.dp).performClick()
        assertEquals(1, clicks)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        assertReadable(RigCheckOptionKind.Scan)
    }

    @Test
    fun manualCardShowsTitleAndDescriptionAndIsTappable() {
        var clicks = 0
        composeRule.setRigCheckContent {
            RigCheckOptionCard(
                kind = RigCheckOptionKind.Manual,
                title = "Enter Manually",
                description = "Type the numbers in yourself — free.",
                icon = Icons.Filled.Keyboard,
                onClick = { clicks++ },
                modifier = Modifier.testTag("card"),
            )
        }
        composeRule.onNodeWithText("Enter Manually").assertIsDisplayed()
        composeRule.onNodeWithTag("card").assertHeightIsAtLeast(148.dp).performClick()
        assertEquals(1, clicks)
        composeRule.assertEveryClickableIsAtLeast48dp(expectAtLeast = 1)
        assertReadable(RigCheckOptionKind.Manual)
    }

    @Test
    fun aDisabledCardIgnoresTaps() {
        var clicks = 0
        composeRule.setRigCheckContent {
            RigCheckOptionCard(
                kind = RigCheckOptionKind.Scan,
                title = "Scan Photo",
                description = "Read the tag from a photo.",
                icon = Icons.Filled.CameraAlt,
                onClick = { clicks++ },
                modifier = Modifier.testTag("card"),
                enabled = false,
            )
        }
        composeRule.onNodeWithTag("card").assertIsNotEnabled().performClick()
        assertEquals(0, clicks)
    }
}
