package com.rigcheck.app.testsupport

import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.performScrollTo

// `performScrollTo()` throws "Semantic Node has no parent layout with a Scroll
// SemanticsAction" for a node with no scrolling container above it (#84; #76 hit
// it on the buttons pinned below the form). Scrolls the node into view when a
// scrolling container sits above it, and otherwise leaves it where it is, so a
// test need not know whether the node is inside the scroll column. The caller's
// next assertion or action still has to find the node on screen, so a node that
// is really out of reach still fails the test. See android/TESTING.md.
fun SemanticsNodeInteraction.scrollToIfScrollable(): SemanticsNodeInteraction {
    var ancestor = fetchSemanticsNode().parent
    while (ancestor != null) {
        if (SemanticsActions.ScrollBy in ancestor.config) return performScrollTo()
        ancestor = ancestor.parent
    }
    return this
}
