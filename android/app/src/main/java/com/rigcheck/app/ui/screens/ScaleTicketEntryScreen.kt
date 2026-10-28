package com.rigcheck.app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.ScanNoticeCard
import com.rigcheck.app.ui.components.StepProgressBar
import com.rigcheck.app.ui.theme.Orange

// Static numbered-callout pattern (not tap-and-hold zoom - this screen's
// reference image has no interactive hover pattern in the mockup, just a
// numbered legend). Exact badge x/y positions from the mockup's canvas
// weren't extractable from the design source, so the legend row carries
// the "which number is which field" mapping instead of overlaying badges
// on the image at specific points.
private val LEGEND = listOf("1 Scale location", "2 Steer", "3 Drive", "4 Trailer", "5 Gross")

@Composable
fun ScaleTicketEntryScreen(
    scale: ScaleTicket,
    onScaleChange: (ScaleTicket) -> Unit,
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
        Text("Scale Ticket", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.testTag(UiTags.SCALE_TITLE))
        StepProgressBar(
            step = 3,
            totalSteps = 3,
            modifier = Modifier.padding(top = 8.dp).testTag(UiTags.SCALE_STEP_BAR),
        )

        ScanNoticeCard(scanNotice?.textFor(scale), modifier = Modifier.padding(top = 16.dp))

        Text(
            "Find these values on your CAT Scale printout.",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp).testTag(UiTags.SCALE_INSTRUCTIONS),
        )

        Image(
            painter = painterResource(R.drawable.ref_scale_ticket),
            contentDescription = "CAT Scale ticket",
            contentScale = ContentScale.FillWidth,
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).testTag(UiTags.SCALE_REFERENCE_IMAGE),
        )

        Row(
            modifier = Modifier.padding(vertical = 12.dp).testTag(UiTags.SCALE_LEGEND),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            LEGEND.forEach { entry ->
                Text(entry, style = MaterialTheme.typography.bodySmall, color = Orange)
            }
        }

        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            LabeledTextField(
                label = "Scale location",
                value = scale.locationName ?: "",
                onValueChange = { onScaleChange(scale.copy(locationName = it.ifBlank { null })) },
                modifier = Modifier.testTag(UiTags.SCALE_LOCATION),
            )
            LabeledNumberField(
                label = "Steer axle, lb",
                value = scale.steerAxleLb,
                onValueChange = { onScaleChange(scale.copy(steerAxleLb = it)) },
                modifier = Modifier.testTag(UiTags.SCALE_STEER_FIELD),
            )
            LabeledNumberField(
                label = "Drive axle, lb",
                value = scale.driveAxleLb,
                onValueChange = { onScaleChange(scale.copy(driveAxleLb = it)) },
                modifier = Modifier.testTag(UiTags.SCALE_DRIVE_FIELD),
            )
            LabeledNumberField(
                label = "Trailer axle(s), lb",
                value = scale.trailerAxleLb,
                onValueChange = { onScaleChange(scale.copy(trailerAxleLb = it)) },
                modifier = Modifier.testTag(UiTags.SCALE_TRAILER_FIELD),
            )
            LabeledNumberField(
                label = "Gross weight, lb",
                value = scale.grossWeightLb,
                onValueChange = { onScaleChange(scale.copy(grossWeightLb = it)) },
                modifier = Modifier.testTag(UiTags.SCALE_GROSS_FIELD),
            )
        }
    }

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp).testTag(UiTags.SCALE_CHECK_BUTTON),
        ) { Text("Check Weights") }
    }
}
