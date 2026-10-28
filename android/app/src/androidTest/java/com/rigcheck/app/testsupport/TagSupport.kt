package com.rigcheck.app.testsupport

import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasAnyDescendant
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onAllNodesWithTag
import com.rigcheck.app.ui.UiTags

// Tests find a control, field or heading by its UiTags tag (#188), so a restyle or a reworded label moves
// nothing under them. Where a test is about what an element says, it finds the element by tag and checks the
// words on it: the tag does the finding, the text is only compared.

// An element tagged `tag` that shows `text` itself or in something it holds (a container's text is on its children).
fun hasTagShowing(tag: String, text: String, substring: Boolean = false): SemanticsMatcher =
    hasTestTag(tag) and (hasText(text, substring) or hasAnyDescendant(hasText(text, substring)))

// These look in the unmerged tree: a tag on something inside a tappable card or row (which merges what it holds
// into one node) is only there, and a tag on a button keeps its words on the Text it holds.
fun SemanticsNodeInteractionsProvider.onNodeWithTagText(
    tag: String,
    text: String,
    substring: Boolean = false,
): SemanticsNodeInteraction = onNode(hasTagShowing(tag, text, substring), useUnmergedTree = true)

fun SemanticsNodeInteractionsProvider.nodesWithTag(tag: String): Int =
    onAllNodesWithTag(tag, useUnmergedTree = true).fetchSemanticsNodes().size

fun SemanticsNodeInteractionsProvider.nodesWithTagShowing(tag: String, text: String, substring: Boolean = false): Int =
    onAllNodes(hasTagShowing(tag, text, substring), useUnmergedTree = true).fetchSemanticsNodes().size

private fun hasRigCard(nickname: String): SemanticsMatcher = hasTestTag(UiTags.PICKER_RIG_CARD) and hasText(nickname)

// A saved Rig's card on the Rig picker, found by the nickname the user gave it (data, not a label).
fun SemanticsNodeInteractionsProvider.onRigCard(nickname: String): SemanticsNodeInteraction =
    onNode(hasRigCard(nickname))

fun SemanticsNodeInteractionsProvider.rigCardCount(nickname: String): Int =
    onAllNodes(hasRigCard(nickname)).fetchSemanticsNodes().size

// The delete control on that Rig's card.
fun SemanticsNodeInteractionsProvider.onRigDeleteButton(nickname: String): SemanticsNodeInteraction =
    onNode(hasTestTag(UiTags.PICKER_RIG_DELETE) and hasAnyAncestor(hasRigCard(nickname)))

// A History entry, found by the Rig nickname it shows.
fun SemanticsNodeInteractionsProvider.onHistoryEntry(nickname: String): SemanticsNodeInteraction =
    onNodeWithTagText(UiTags.HISTORY_ENTRY, nickname)
