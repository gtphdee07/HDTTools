package com.rigcheck.app.testsupport

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.junit4.ComposeContentTestRule
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.PhotoRect
import com.rigcheck.app.ui.components.ReferenceCropKey
import com.rigcheck.app.ui.theme.AA_LARGE_TEXT
import com.rigcheck.app.ui.theme.AA_NORMAL_TEXT
import com.rigcheck.app.ui.theme.RigCheckTheme
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.Surface
import com.rigcheck.app.ui.theme.contrastRatio
import org.junit.Assert.assertTrue

// Shared checks for the design components (#191): every component test shows one state and asserts that every
// tappable thing in it has a touch target of at least 48 x 48 dp and that the text colour it draws meets WCAG AA
// against the fill it draws on (4.5:1, or 3:1 for large text).

/** Shows [content] in the RigCheck theme on a white page with a 16 dp margin, as the screens do. */
fun ComposeContentTestRule.setRigCheckContent(content: @Composable () -> Unit) {
    setContent {
        RigCheckTheme {
            Box(Modifier.fillMaxWidth().background(Surface).padding(16.dp)) { content() }
        }
    }
}

/**
 * Every node with a click action has a touch area (what a finger can hit, including a Material control's minimum-size
 * inflation) of at least 48 x 48 dp. [expectAtLeast] is how many there must be, so a
 * state that should have tappable controls cannot pass because none were found.
 */
fun ComposeContentTestRule.assertEveryClickableIsAtLeast48dp(expectAtLeast: Int = 0) {
    val nodes = onAllNodes(hasClickAction()).fetchSemanticsNodes()
    assertTrue("expected at least $expectAtLeast clickable nodes, found ${nodes.size}", nodes.size >= expectAtLeast)
    val minimum = Sizes.TouchTargetMin.value
    with(density) {
        for (node in nodes) {
            val bounds = node.touchBoundsInRoot
            val width = bounds.width.toDp().value
            val height = bounds.height.toDp().value
            assertTrue(
                "a clickable node is ${width} x ${height} dp, under ${minimum} x ${minimum} dp: ${node.config}",
                width >= minimum - 0.5f && height >= minimum - 0.5f,
            )
        }
    }
}

/** The pinned reference card is centred on [crop] of its photo (#199): what it shows, read from its semantics. */
fun SemanticsNodeInteraction.assertShowsCrop(crop: PhotoRect): SemanticsNodeInteraction =
    assert(SemanticsMatcher.expectValue(ReferenceCropKey, crop))

/** [foreground] on [background] meets AA: 4.5:1, or 3:1 when [largeText]. [behind] is what a translucent fill sits on. */
fun assertAa(what: String, foreground: Color, background: Color, largeText: Boolean = false, behind: Color = Surface) {
    val ratio = contrastRatio(foreground, background, behind)
    val needed = if (largeText) AA_LARGE_TEXT else AA_NORMAL_TEXT
    assertTrue("$what is $ratio:1, under AA $needed:1", ratio >= needed)
}

/**
 * A disabled control is exempt from WCAG 1.4.3 (inactive components), and the design's own disabled pair is 4.35:1; it
 * still has to stay readable, so it is held to 3:1.
 */
fun assertReadableWhenDisabled(what: String, foreground: Color, background: Color) =
    assertAa("$what (disabled)", foreground, background, largeText = true)
