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
import com.rigcheck.app.ui.components.LabeledIntField
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.ReferenceImageCard
import com.rigcheck.app.ui.components.StepProgressBar

@Composable
fun TrailerTagEntryScreen(
    trailer: TrailerTag,
    onTrailerChange: (TrailerTag) -> Unit,
    onContinue: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize()) {
    Column(
        modifier = Modifier
            .weight(1f)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Trailer Tag", style = MaterialTheme.typography.headlineMedium)
        StepProgressBar(step = 2, totalSteps = 3, modifier = Modifier.padding(top = 8.dp))

        Text(
            "Find these values on your trailer's compliance label (usually near the front, curb side).",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp),
        )

        ReferenceImageCard(
            imageRes = R.drawable.ref_trailer_tag,
            contentDescription = "Trailer compliance label",
        )

        Text(
            "Hover a field to zoom in on its spot on the tag",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(vertical = 8.dp),
        )

        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            LabeledTextField(
                label = "Description",
                value = trailer.description ?: "",
                onValueChange = { onTrailerChange(trailer.copy(description = it.ifBlank { null })) },
                placeholder = "e.g. Brinkley RV",
                modifier = Modifier.testTag("trailer_description"),
            )
            LabeledTextField(
                label = "Name",
                value = trailer.name ?: "",
                onValueChange = { onTrailerChange(trailer.copy(name = it.ifBlank { null })) },
            )
            LabeledNumberField(
                label = "GVWR, lb",
                value = trailer.gvwrLb,
                onValueChange = { onTrailerChange(trailer.copy(gvwrLb = it)) },
            )
            LabeledNumberField(
                label = "GAWR per axle, lb",
                value = trailer.gawrPerAxleLb,
                onValueChange = { onTrailerChange(trailer.copy(gawrPerAxleLb = it)) },
            )
            Column {
                LabeledIntField(
                    label = "Axle count",
                    optionalHint = "optional",
                    value = trailer.axleCount,
                    onValueChange = { onTrailerChange(trailer.copy(axleCount = it)) },
                )
                Text(
                    "Defaults to 2 if left blank.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            LabeledNumberField(
                label = "Unloaded weight (UVW), lb",
                value = trailer.uvwLb,
                onValueChange = { onTrailerChange(trailer.copy(uvwLb = it)) },
            )
        }
    }

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp),
        ) { Text("Next: Scale Ticket") }
    }
}
