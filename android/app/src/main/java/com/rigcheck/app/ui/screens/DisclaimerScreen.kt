package com.rigcheck.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckFooter
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.OrangeDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.TintOrange

// Exact wording finalized 2026-08-17 (ANDROID_DESIGN_BRIEF.md) - Android-
// specific, deliberately not identical to web/Streamlit's disclaimer,
// since the "OCR-read photos" phrasing there doesn't fit Android's
// manual-entry-first default.
private const val BODY_1 = "RigCheck is an experimental project built to learn app development, " +
    "not a certified or professional weight-safety tool. You type in numbers straight off your " +
    "own tag and ticket photos, and the math that follows is simplified — any step of that chain " +
    "can be wrong."
private const val BODY_2 = "Do not use this tool to decide whether your rig is safe to tow. " +
    "Always verify actual weights and ratings using a certified scale and your vehicle's official " +
    "documentation, and consult a qualified professional if you're unsure. You use this tool, and " +
    "any decisions you make based on it, entirely at your own risk and responsibility."

// "DM Sans 400 16/24 ink" (the map): the body style with the 24 dp line the design gives these paragraphs.
private val PARAGRAPH = RigCheckStyles.body.copy(lineHeight = 24.sp)

// The design's page (resize-rules.md, "What scrolls and what is pinned"): the icon, the title and both paragraphs scroll
// as one page, and "I Understand, Continue" is pinned in the footer, so a large font or a small phone can no longer
// push it off the screen. The page has no top bar (components.md: not on the Disclaimer).
@Composable
fun DisclaimerScreen(onAcknowledge: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 20.dp, top = 40.dp, end = 20.dp, bottom = 24.dp),
        ) {
            // `IconTile`: a 72 dp tile in tint-orange with an orange-deep warning glyph, drawn at the left.
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .testTag(UiTags.DISCLAIMER_ICON)
                    .size(72.dp)
                    .background(TintOrange, RoundedCornerShape(Radii.Panel)),
            ) {
                Icon(Icons.Outlined.Warning, contentDescription = null, tint = OrangeDeep, modifier = Modifier.size(36.dp))
            }
            Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.padding(top = 16.dp)) {
                Text(
                    "Experimental Tool —\nNot for Safety Decisions",
                    style = RigCheckStyles.heading,
                    color = Ink,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.DISCLAIMER_TITLE),
                )
                Text(
                    BODY_1,
                    style = PARAGRAPH,
                    color = Ink,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.DISCLAIMER_BODY_1),
                )
                Text(
                    BODY_2,
                    style = PARAGRAPH,
                    color = Ink,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.DISCLAIMER_BODY_2),
                )
            }
        }
        RigCheckFooter {
            RigCheckButton(
                text = "I Understand, Continue",
                onClick = onAcknowledge,
                modifier = Modifier.testTag(UiTags.DISCLAIMER_ACCEPT_BUTTON),
            )
        }
    }
}
