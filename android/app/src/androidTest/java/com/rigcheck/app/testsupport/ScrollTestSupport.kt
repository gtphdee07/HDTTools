package com.rigcheck.app.testsupport

import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.performScrollTo

// `performScrollTo()` throws "Semantic Node has no parent layout with a Scroll
// SemanticsAction" for a node that has no scrolling container above it (#84;
// #76 hit it on the buttons pinned below the form). Whether a node sits inside
// the scroll column or outside it is a layout detail a test should not have to
// know, and a screen that moves a node out of the column would otherwise break
// every test that scrolls to it.
//
// Scrolls the node into view when a scrolling container sits above it, and
// otherwise leaves it where it is. Either way the caller's next assertion or
// action still has to find the node on screen, so a node that is really out of
// reach still fails the test.
//
// Measured on Compose BOM 2026.02.01: a `verticalScroll` column whose content
// fits the window still exposes the scroll action, so `performScrollTo()` on a
// node inside it works at any screen size or font scale.
fun SemanticsNodeInteraction.scrollToIfScrollable(): SemanticsNodeInteraction {
    var ancestor = fetchSemanticsNode().parent
    while (ancestor != null) {
        if (SemanticsActions.ScrollBy in ancestor.config) return performScrollTo()
        ancestor = ancestor.parent
    }
    return this
}
