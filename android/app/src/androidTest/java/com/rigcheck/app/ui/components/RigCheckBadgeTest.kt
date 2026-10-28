package com.rigcheck.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.assertAa
import com.rigcheck.app.testsupport.assertEveryClickableIsAtLeast48dp
import com.rigcheck.app.testsupport.setRigCheckContent
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// components.md, "Badge": the seven kinds.
@RunWith(AndroidJUnit4::class)
class RigCheckBadgeTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun showAndAssert(kind: RigCheckBadgeKind, text: String) {
        composeRule.setRigCheckContent { RigCheckBadge(text, kind) }
        composeRule.onNodeWithText(text).assertIsDisplayed()
        composeRule.assertEveryClickableIsAtLeast48dp()
        val colors = rigCheckBadgeColors(kind)
        assertAa("$kind badge text", colors.content, colors.container)
    }

    @Test
    fun creditBadge() = showAndAssert(RigCheckBadgeKind.Credit, "1 scan")

    @Test
    fun freeBadge() = showAndAssert(RigCheckBadgeKind.Free, "Free")

    @Test
    fun withinLimitBadge() = showAndAssert(RigCheckBadgeKind.WithinLimit, "Within limit")

    @Test
    fun overLimitBadge() = showAndAssert(RigCheckBadgeKind.OverLimit, "Over limit")

    @Test
    fun partiallyCheckedBadge() = showAndAssert(RigCheckBadgeKind.PartiallyChecked, "Partially checked")

    @Test
    fun notCheckedBadge() = showAndAssert(RigCheckBadgeKind.NotChecked, "Not checked")

    @Test
    fun planBadge() = showAndAssert(RigCheckBadgeKind.Plan, "Pro")

    @Test
    fun badgeWithAnIcon() {
        composeRule.setRigCheckContent { RigCheckBadge("1 scan", RigCheckBadgeKind.Credit, icon = Icons.Filled.CameraAlt) }
        composeRule.onNodeWithText("1 scan").assertIsDisplayed()
    }
}
