package com.rigcheck.app.layoutcapture

import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.positionOnScreen
import androidx.compose.ui.semantics.SemanticsNode
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.junit4.ComposeTestRule
import kotlin.math.roundToLong
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

// Where one tagged element sits on the screen, in dp: its top-left corner and size as laid out (not cut by a scroll
// container), and whether any of it is on show. A tag on a repeated item (a rig card, a breakdown row) is the first
// of them, with `count` saying how many there are.
data class TaggedBounds(
    val x: Double,
    val y: Double,
    val width: Double,
    val height: Double,
    val visible: Boolean,
    val count: Int,
)

// Every tagged node of the screen on show, dialogs included, found in the unmerged tree (a tag inside a tappable card
// is only there). Positions are on the display, so they are the pixels of a screenshot of it divided by the density.
fun ComposeTestRule.measureTaggedElements(pxPerDp: Double): Map<String, TaggedBounds> =
    onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsProperties.TestTag), useUnmergedTree = true)
        .fetchSemanticsNodes()
        .groupBy { it.config[SemanticsProperties.TestTag] }
        .mapValues { (_, nodes) -> boundsOf(nodes.first(), nodes.size, pxPerDp) }
        .toSortedMap()

private fun boundsOf(node: SemanticsNode, count: Int, pxPerDp: Double): TaggedBounds {
    val coordinates = node.layoutInfo.coordinates
    val position = coordinates.positionOnScreen()
    val shown: Rect = coordinates.boundsInWindow()
    return TaggedBounds(
        x = dp(position.x, pxPerDp),
        y = dp(position.y, pxPerDp),
        width = dp(node.size.width.toFloat(), pxPerDp),
        height = dp(node.size.height.toFloat(), pxPerDp),
        visible = node.layoutInfo.isPlaced && shown.width > 0f && shown.height > 0f,
        count = count,
    )
}

// To a tenth of a dp, so the same layout is the same number on every run and in the JSON.
private fun dp(px: Float, pxPerDp: Double): Double = (px / pxPerDp * 10).roundToLong() / 10.0

// `order` is the state's place in the capture's list, which the merge uses to pick a screen's first state.
fun boundsFileText(screen: String, state: String, order: Int, frame: Frame, bounds: Map<String, TaggedBounds>): String {
    val file = buildJsonObject {
        put("screen", screen)
        put("state", state)
        put("order", order)
        put(
            "frame",
            buildJsonObject {
                put("name", frame.name)
                put("widthDp", frame.widthDp)
                put("heightDp", frame.heightDp)
                put("fontScale", frame.fontScale.toDouble())
            },
        )
        put(
            "elements",
            JsonObject(
                bounds.mapValues { (_, b) ->
                    buildJsonObject {
                        put("x", JsonPrimitive(b.x))
                        put("y", JsonPrimitive(b.y))
                        put("width", JsonPrimitive(b.width))
                        put("height", JsonPrimitive(b.height))
                        put("visible", JsonPrimitive(b.visible))
                        put("count", JsonPrimitive(b.count))
                    }
                },
            ),
        )
    }
    return Json { prettyPrint = true }.encodeToString(JsonObject.serializer(), file) + "\n"
}

// What differs between two measurements of the same state, one line per tag, or empty when they agree.
fun describeDifferences(first: Map<String, TaggedBounds>, second: Map<String, TaggedBounds>): List<String> =
    (first.keys + second.keys).sorted().mapNotNull { tag ->
        if (first[tag] == second[tag]) null else "$tag: ${first[tag] ?: "absent"} then ${second[tag] ?: "absent"}"
    }
