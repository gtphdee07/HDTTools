package com.rigcheck.app.ui.components

import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.getBoundsInRoot
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Notice card": info, scan, warn and error tones, with and without a title.
@RunWith(AndroidJUnit4::class)
class RigCheckNoticeCardTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun assertReadable(tone: RigCheckNoticeTone) {
        val colors = rigCheckNoticeColors(tone)
        assertAa("$tone text", colors.text, colors.container)
        assertAa("$tone icon", colors.icon, colors.container, largeText = true)
    }

    private fun showAndAssert(tone: RigCheckNoticeTone, title: String? = null) {
        composeRule.setRigCheckContent { RigCheckNoticeCard("Everything here is an estimate.", tone, title = title) }
        composeRule.onNodeWithText("Everything here is an estimate.").assertIsDisplayed()
        if (title != null) composeRule.onNodeWithText(title).assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
        assertReadable(tone)
    }

    @Test
    fun infoNotice() = showAndAssert(RigCheckNoticeTone.Info)

    @Test
    fun scanNotice() = showAndAssert(RigCheckNoticeTone.Scan)

    @Test
    fun warnNotice() = showAndAssert(RigCheckNoticeTone.Warn)

    @Test
    fun errorNotice() = showAndAssert(RigCheckNoticeTone.Error)

    @Test
    fun noticeWithATitle() = showAndAssert(RigCheckNoticeTone.Scan, title = "A Scan was used")

    // The estimated-figures notice holds a list of its own and draws no icon (its frozen title carries an emoji).
    @Test
    fun noticeAroundItsOwnContentWithNoIcon() {
        composeRule.setRigCheckContent {
            RigCheckNoticeCard(tone = RigCheckNoticeTone.Warn, title = "A title", icon = null) {
                Text("First line")
                Text("Second line")
            }
        }
        composeRule.onNodeWithText("A title").assertIsDisplayed()
        composeRule.onNodeWithText("First line").assertIsDisplayed()
        composeRule.onNodeWithText("Second line").assertIsDisplayed()
        // With no icon the words start at the card's own padding (14 dp), not 10 dp further in after a 22 dp icon.
        val card = composeRule.onNodeWithText("A title").getBoundsInRoot().left
        val padding = 14.dp + 16.dp
        assertEquals(padding.value, card.value, 1f)
        assertReadable(RigCheckNoticeTone.Warn)
    }
}
