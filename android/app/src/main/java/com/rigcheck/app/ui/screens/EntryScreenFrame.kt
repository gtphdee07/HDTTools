package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.isImeVisible
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.components.RigCheckFooter
import com.rigcheck.app.ui.components.RigCheckStepIndicator
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.components.chipBelowTitle

// The skeleton the design gives the three entry screens (resize-rules.md, "Layout skeleton, every screen" and "What
// scrolls and what is pinned"): the top bar (Back, the title, the balance chip where there is one, the step indicator)
// and, on the Truck and Trailer screens, the reference card are pinned at the top; the form scrolls as one column; the
// primary action is pinned in the footer.
//
// While the keyboard is open the bar is compact and drops the step indicator. On a phone with too little room left
// for the form under the pinned card (a short screen with the keyboard up), the card scrolls with the form instead,
// so the form and the primary action always have room; a short screen or a large font gives the card its compact size.
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun EntryScreenFrame(
    title: String,
    step: Int,
    onBack: () -> Unit,
    titleModifier: Modifier,
    backModifier: Modifier,
    stepModifier: Modifier,
    footer: @Composable ColumnScope.() -> Unit,
    modifier: Modifier = Modifier,
    backEnabled: Boolean = true,
    chip: (@Composable (Modifier) -> Unit)? = null,
    // The reference card; `compact` is the size it takes on a short screen or at a large font.
    reference: (@Composable (compact: Boolean) -> Unit)? = null,
    body: @Composable ColumnScope.() -> Unit,
) {
    // At a large font the chip goes to a row of its own under the title (resize-rules.md).
    val chipBelow = chip != null && chipBelowTitle()
    val keyboardOpen = WindowInsets.isImeVisible
    val configuration = LocalConfiguration.current
    val compactReference = configuration.screenHeightDp < SHORT_SCREEN_DP || configuration.fontScale >= 1.6f

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val pinReference = reference != null && maxHeight >= MIN_ROOM_TO_PIN_DP.dp
        Column(modifier = Modifier.fillMaxSize()) {
            RigCheckTopBar(
                title = title,
                onBack = onBack,
                backEnabled = backEnabled,
                compact = keyboardOpen,
                titleModifier = titleModifier,
                backModifier = backModifier,
                end = { if (chip != null && !chipBelow) chip(Modifier) },
                below = if (keyboardOpen) {
                    null
                } else {
                    {
                        if (chipBelow && chip != null) chip(Modifier.align(Alignment.End))
                        RigCheckStepIndicator(step = step, modifier = stepModifier)
                    }
                },
            )
            if (reference != null && pinReference) {
                Column(modifier = Modifier.padding(start = 16.dp, top = 12.dp, end = 16.dp)) { reference(compactReference) }
            }
            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(start = 16.dp, top = 16.dp, end = 16.dp, bottom = 24.dp),
            ) {
                if (reference != null && !pinReference) reference(true)
                body()
            }
            RigCheckFooter(content = footer)
        }
    }
}

// resize-rules.md: the reference card "may collapse to its caption row and one label line below 700 dp of height".
private const val SHORT_SCREEN_DP = 700

// Below this much height for everything (the screen less the bars and the keyboard) the pinned card would leave the
// form no room, so it scrolls with the form.
private const val MIN_ROOM_TO_PIN_DP = 420
