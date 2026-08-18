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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.theme.SunsetOrange

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
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Scale Ticket", style = MaterialTheme.typography.headlineMedium)
        Text("Step 3 of 3", style = MaterialTheme.typography.bodySmall)

        Text(
            "Find these values on your CAT Scale printout.",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp),
        )

        Image(
            painter = painterResource(R.drawable.ref_scale_ticket),
            contentDescription = "CAT Scale ticket",
            contentScale = ContentScale.FillWidth,
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)),
        )

        Row(
            modifier = Modifier.padding(vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            LEGEND.forEach { entry ->
                Text(entry, style = MaterialTheme.typography.bodySmall, color = SunsetOrange)
            }
        }

        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            LabeledTextField(
                label = "Scale location",
                value = scale.locationName ?: "",
                onValueChange = { onScaleChange(scale.copy(locationName = it.ifBlank { null })) },
            )
            LabeledNumberField(
                label = "Steer axle, lb",
                value = scale.steerAxleLb,
                onValueChange = { onScaleChange(scale.copy(steerAxleLb = it)) },
            )
            LabeledNumberField(
                label = "Drive axle, lb",
                value = scale.driveAxleLb,
                onValueChange = { onScaleChange(scale.copy(driveAxleLb = it)) },
            )
            LabeledNumberField(
                label = "Trailer axle(s), lb",
                value = scale.trailerAxleLb,
                onValueChange = { onScaleChange(scale.copy(trailerAxleLb = it)) },
            )
            LabeledNumberField(
                label = "Gross weight, lb",
                value = scale.grossWeightLb,
                onValueChange = { onScaleChange(scale.copy(grossWeightLb = it)) },
            )
        }

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
        ) { Text("Check Weights") }
    }
}
