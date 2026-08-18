package com.rigcheck.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.ReferenceImageCard

@Composable
fun TruckTagEntryScreen(
    truck: TruckTag,
    onTruckChange: (TruckTag) -> Unit,
    onContinue: () -> Unit,
) {
    var showStandaloneInfo by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Truck Tag", style = MaterialTheme.typography.headlineMedium)
        Text("Step 1 of 3", style = MaterialTheme.typography.bodySmall)

        Text(
            "Find these values on your truck's compliance label (usually inside the driver door jamb).",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 12.dp),
        )

        ReferenceImageCard(
            imageRes = R.drawable.ref_truck_tag,
            contentDescription = "Truck compliance label",
        )

        Text(
            "Hover a field to zoom in on its spot on the tag",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(vertical = 8.dp),
        )

        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            LabeledTextField(
                label = "Description",
                value = truck.description ?: "",
                onValueChange = { onTruckChange(truck.copy(description = it.ifBlank { null })) },
                placeholder = "e.g. Ford F-450",
            )
            LabeledTextField(
                label = "Name",
                value = truck.name ?: "",
                onValueChange = { onTruckChange(truck.copy(name = it.ifBlank { null })) },
            )
            LabeledNumberField(
                label = "GVWR, lb",
                value = truck.gvwrLb,
                onValueChange = { onTruckChange(truck.copy(gvwrLb = it)) },
            )
            LabeledNumberField(
                label = "Front GAWR, lb",
                value = truck.frontGawrLb,
                onValueChange = { onTruckChange(truck.copy(frontGawrLb = it)) },
            )
            LabeledNumberField(
                label = "Rear GAWR, lb",
                value = truck.rearGawrLb,
                onValueChange = { onTruckChange(truck.copy(rearGawrLb = it)) },
            )
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Stand-alone weight, lb — optional",
                        style = MaterialTheme.typography.labelLarge,
                    )
                    Icon(
                        Icons.Filled.Info,
                        contentDescription = "More info",
                        modifier = Modifier
                            .padding(start = 4.dp)
                            .clickable { showStandaloneInfo = !showStandaloneInfo },
                    )
                }
                if (showStandaloneInfo) {
                    Text(
                        "If left blank, we'll assume the trailer axle reading is 80% of the " +
                            "trailer's total weight. Fill this in for a more accurate tongue-weight " +
                            "estimate.",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
                LabeledNumberField(
                    label = "",
                    value = truck.standaloneWeightLb,
                    onValueChange = { onTruckChange(truck.copy(standaloneWeightLb = it)) },
                )
            }
        }

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
        ) { Text("Next: Trailer Tag") }
    }
}
