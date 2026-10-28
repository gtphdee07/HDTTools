package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.LabeledIntField
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.ReferenceImageCard
import com.rigcheck.app.ui.components.ScanNoticeCard
import com.rigcheck.app.ui.components.StepProgressBar

@Composable
fun TrailerTagEntryScreen(
    trailer: TrailerTag,
    onTrailerChange: (TrailerTag) -> Unit,
    onContinue: () -> Unit,
    scanNotice: ScanNotice? = null,
) {
    Column(modifier = Modifier.fillMaxSize()) {
    Column(
        modifier = Modifier
            .weight(1f)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Trailer Tag", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.testTag(UiTags.TRAILER_TITLE))
        StepProgressBar(
            step = 2,
            totalSteps = 3,
            modifier = Modifier.padding(top = 8.dp).testTag(UiTags.TRAILER_STEP_BAR),
        )

        ScanNoticeCard(scanNotice?.textFor(trailer), modifier = Modifier.padding(top = 16.dp))

        Text(
            "Find these values on your trailer's compliance label (usually near the front, curb side).",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp).testTag(UiTags.TRAILER_INSTRUCTIONS),
        )

        ReferenceImageCard(
            imageRes = R.drawable.ref_trailer_tag,
            contentDescription = "Trailer compliance label",
            modifier = Modifier.testTag(UiTags.TRAILER_REFERENCE_IMAGE),
        )

        Text(
            "Hover a field to zoom in on its spot on the tag",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(vertical = 8.dp).testTag(UiTags.TRAILER_REFERENCE_HINT),
        )

        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
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
                modifier = Modifier.testTag(UiTags.TRAILER_GVWR_FIELD),
            )
            LabeledNumberField(
                label = "GAWR per axle, lb",
                value = trailer.gawrPerAxleLb,
                onValueChange = { onTrailerChange(trailer.copy(gawrPerAxleLb = it)) },
                modifier = Modifier.testTag(UiTags.TRAILER_GAWR_FIELD),
            )
            Column {
                LabeledIntField(
                    label = "Axle count",
                    optionalHint = "optional",
                    value = trailer.axleCount,
                    onValueChange = { onTrailerChange(trailer.copy(axleCount = it)) },
                    modifier = Modifier.testTag(UiTags.TRAILER_AXLE_COUNT_FIELD),
                )
                Text(
                    "Defaults to 2 if left blank.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.testTag(UiTags.TRAILER_AXLE_COUNT_HELP),
                )
            }
            LabeledNumberField(
                label = "Unloaded weight (UVW), lb",
                value = trailer.uvwLb,
                onValueChange = { onTrailerChange(trailer.copy(uvwLb = it)) },
                modifier = Modifier.testTag(UiTags.TRAILER_UVW_FIELD),
            )
        }
    }

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp).testTag(UiTags.TRAILER_NEXT_BUTTON),
        ) { Text("Next: Scale Ticket") }
    }
}
