package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import com.rigcheck.app.R
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.LabeledIntField
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.PinnedReferenceCard
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.RigCheckStyles

@Composable
fun TrailerTagEntryScreen(
    trailer: TrailerTag,
    onTrailerChange: (TrailerTag) -> Unit,
    onContinue: () -> Unit,
    scanNotice: ScanNotice? = null,
    onBack: () -> Unit = {},
) {
    EntryScreenFrame(
        title = "Trailer Tag",
        step = 2,
        onBack = onBack,
        titleModifier = Modifier.testTag(UiTags.TRAILER_TITLE),
        backModifier = Modifier.testTag(UiTags.TRAILER_BACK),
        stepModifier = Modifier.testTag(UiTags.TRAILER_STEP_BAR),
        reference = { compact ->
            PinnedReferenceCard(
                imageRes = R.drawable.ref_trailer_tag,
                imageDescription = "Trailer compliance label",
                hint = "Tap a field to see its spot on the tag",
                compact = compact,
                hintModifier = Modifier.testTag(UiTags.TRAILER_REFERENCE_HINT),
                imageModifier = Modifier.testTag(UiTags.TRAILER_REFERENCE_IMAGE),
            )
        },
        footer = {
            RigCheckButton(
                text = "Next: Scale Ticket",
                onClick = onContinue,
                icon = Icons.AutoMirrored.Filled.ArrowForward,
                modifier = Modifier.testTag(UiTags.TRAILER_NEXT_BUTTON),
            )
        },
    ) {
        scanNotice?.textFor(trailer)?.let { text ->
            RigCheckNoticeCard(text = text, tone = RigCheckNoticeTone.Scan, modifier = Modifier.testTag(UiTags.SCAN_NOTICE))
        }

        Text(
            "Find these values on your trailer's compliance label (usually near the front, curb side).",
            style = RigCheckStyles.body,
            color = InkMuted,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.TRAILER_INSTRUCTIONS),
        )

        LabeledTextField(
            label = "Description",
            value = trailer.description ?: "",
            onValueChange = { onTrailerChange(trailer.copy(description = it.ifBlank { null })) },
            placeholder = "e.g. Brinkley RV",
            modifier = Modifier.testTag(UiTags.TRAILER_DESCRIPTION),
        )
        LabeledTextField(
            label = "Name",
            value = trailer.name ?: "",
            onValueChange = { onTrailerChange(trailer.copy(name = it.ifBlank { null })) },
            modifier = Modifier.testTag(UiTags.TRAILER_NAME_FIELD),
        )
        LabeledNumberField(
            label = "GVWR, lb",
            value = trailer.gvwrLb,
            onValueChange = { onTrailerChange(trailer.copy(gvwrLb = it)) },
            unit = "lb",
            modifier = Modifier.testTag(UiTags.TRAILER_GVWR_FIELD),
        )
        LabeledNumberField(
            label = "GAWR per axle, lb",
            value = trailer.gawrPerAxleLb,
            onValueChange = { onTrailerChange(trailer.copy(gawrPerAxleLb = it)) },
            unit = "lb",
            modifier = Modifier.testTag(UiTags.TRAILER_GAWR_FIELD),
        )
        LabeledIntField(
            label = "Axle count",
            optionalHint = "optional",
            value = trailer.axleCount,
            onValueChange = { onTrailerChange(trailer.copy(axleCount = it)) },
            help = "Defaults to 2 if left blank.",
            helpModifier = Modifier.testTag(UiTags.TRAILER_AXLE_COUNT_HELP),
            modifier = Modifier.testTag(UiTags.TRAILER_AXLE_COUNT_FIELD),
        )
        LabeledNumberField(
            label = "Unloaded weight (UVW), lb",
            value = trailer.uvwLb,
            onValueChange = { onTrailerChange(trailer.copy(uvwLb = it)) },
            unit = "lb",
            modifier = Modifier.testTag(UiTags.TRAILER_UVW_FIELD),
        )
    }
}
