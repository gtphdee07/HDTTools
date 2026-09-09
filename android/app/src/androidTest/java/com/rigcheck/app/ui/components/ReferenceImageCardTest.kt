package com.rigcheck.app.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onChildren
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTouchInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.R
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// ReferenceImageCard has no dedicated test file (and no callback outputs -
// it's purely internal press-position state driving a graphicsLayer zoom
// overlay), so the only way to observe it from outside is the composed
// node tree itself: exactly one Image child (the base photo) when idle,
// two (base photo + zoom overlay) while pressPosition is non-null. A
// testTag is applied only from this test's own call site (via the
// existing `modifier` parameter) - ReferenceImageCard.kt itself is not
// modified.
//
// detectDragGesturesAfterLongPress(onDragStart, onDrag, onDragEnd,
// onDragCancel) is the pointer-input gesture lambda at a flat 0% per
// android/TESTING.md's cross-reference - these tests specifically drive
// each of those four callbacks for real via performTouchInput.
@RunWith(AndroidJUnit4::class)
class ReferenceImageCardTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val tag = "reference_image_card"

    @Test
    fun idleStateShowsOnlyTheBaseImage() {
        composeRule.setContent {
            ReferenceImageCard(
                imageRes = R.drawable.ref_truck_tag,
                contentDescription = "Truck compliance label",
                modifier = Modifier.testTag(tag),
            )
        }

        composeRule.onNodeWithTag(tag).onChildren().assertCountEquals(1)
    }

    @Test
    fun longPressAndHoldShowsZoomOverlayThenReleaseHidesIt() {
        composeRule.setContent {
            ReferenceImageCard(
                imageRes = R.drawable.ref_truck_tag,
                contentDescription = "Truck compliance label",
                modifier = Modifier.testTag(tag),
            )
        }

        val node = composeRule.onNodeWithTag(tag)

        // detectDragGesturesAfterLongPress only calls onDragStart once a
        // move is observed *after* the long-press hold - a hold with no
        // subsequent move (confirmed by actually running this: it left
        // the overlay absent, 1 child not 2) never fires onDragStart at
        // all. So: hold past the long-press timeout, then move - that's
        // what exercises onDragStart.
        node.performTouchInput {
            down(center)
            advanceEventTime(700)
            moveTo(center + androidx.compose.ui.geometry.Offset(10f, 10f))
        }
        composeRule.waitForIdle()
        node.onChildren().assertCountEquals(2)

        // Move again while still held - exercises onDrag (updates the
        // zoom origin to the new position).
        node.performTouchInput {
            moveTo(center + androidx.compose.ui.geometry.Offset(20f, 20f))
        }
        composeRule.waitForIdle()
        node.onChildren().assertCountEquals(2)

        // Release - exercises onDragEnd, which resets pressPosition to
        // null and removes the overlay.
        node.performTouchInput { up() }
        composeRule.waitForIdle()
        node.onChildren().assertCountEquals(1)
    }

    @Test
    fun cancellingTheGestureAfterLongPressHidesTheOverlay() {
        composeRule.setContent {
            ReferenceImageCard(
                imageRes = R.drawable.ref_truck_tag,
                contentDescription = "Truck compliance label",
                modifier = Modifier.testTag(tag),
            )
        }

        val node = composeRule.onNodeWithTag(tag)

        // As above: onDragStart needs hold-then-move, not hold alone.
        node.performTouchInput {
            down(center)
            advanceEventTime(700)
            moveTo(center + androidx.compose.ui.geometry.Offset(10f, 10f))
        }
        composeRule.waitForIdle()
        node.onChildren().assertCountEquals(2)

        // Simulates an interrupted gesture (e.g. a system gesture stealing
        // the pointer) - exercises onDragCancel, the fourth and last
        // callback.
        node.performTouchInput { cancel() }
        composeRule.waitForIdle()
        node.onChildren().assertCountEquals(1)
    }
}
