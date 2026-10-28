package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** Where a step stands: finished, the one in progress, or still ahead. */
enum class RigCheckStepStatus { Done, Current, Upcoming }

/** A step circle's fill, the colour of its digit or tick, and its border colour (null: none). */
data class RigCheckStepColors(val fill: Color, val content: Color, val border: Color?)

fun rigCheckStepColors(status: RigCheckStepStatus): RigCheckStepColors = when (status) {
    RigCheckStepStatus.Done, RigCheckStepStatus.Current -> RigCheckStepColors(Ink, SurfaceWhite, null)
    RigCheckStepStatus.Upcoming -> RigCheckStepColors(SurfaceWhite, Ink, Ink)
}

internal val RigCheckStepLabels = listOf("Truck", "Trailer", "Scale")

// components.md, "Step indicator": three 32 dp circles (Truck, Trailer, Scale) joined by 2 dp lines at 35% ink. The
// current one is ink with a white digit and a bold label; a done one is ink with a tick; an upcoming one is white
// with a 2 dp ink border. The caption "Step n of 3" is above. It counts only the three documents.
@Composable
fun RigCheckStepIndicator(step: Int, modifier: Modifier = Modifier) {
    val total = RigCheckStepLabels.size
    require(step in 1..total) { "step must be 1..$total, was $step" }
    // 76 dp in all (the map's new_height): the caption (16), 8 dp, the circles (32), 4 dp and the label (16).
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier.fillMaxWidth().semantics(mergeDescendants = true) {
            contentDescription = "Step $step of $total: ${RigCheckStepLabels[step - 1]}"
        },
    ) {
        Text("Step $step of $total", style = RigCheckStyles.label, color = Ink)
        Row(verticalAlignment = Alignment.Top, modifier = Modifier.fillMaxWidth()) {
            RigCheckStepLabels.forEachIndexed { index, label ->
                val status = when {
                    index + 1 < step -> RigCheckStepStatus.Done
                    index + 1 == step -> RigCheckStepStatus.Current
                    else -> RigCheckStepStatus.Upcoming
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    StepCircle(number = index + 1, status = status)
                    Text(
                        label,
                        style = if (status == RigCheckStepStatus.Current) RigCheckStyles.label else RigCheckStyles.micro,
                        fontWeight = if (status == RigCheckStepStatus.Current) FontWeight.Bold else FontWeight.Normal,
                        color = Ink,
                    )
                }
                if (index < total - 1) {
                    // The connector sits at the middle of the 32 dp circles (15 dp down, 2 dp thick).
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .padding(top = 15.dp)
                            .height(2.dp)
                            .background(Ink.copy(alpha = Opacity.StepConnector)),
                    )
                }
            }
        }
    }
}

@Composable
private fun StepCircle(number: Int, status: RigCheckStepStatus) {
    val colors = rigCheckStepColors(status)
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(32.dp)
            .background(colors.fill, CircleShape)
            .then(if (colors.border != null) Modifier.border(2.dp, colors.border, CircleShape) else Modifier),
    ) {
        if (status == RigCheckStepStatus.Done) {
            Icon(Icons.Filled.Check, contentDescription = null, tint = colors.content, modifier = Modifier.size(18.dp))
        } else {
            Text("$number", style = RigCheckStyles.label, color = colors.content)
        }
    }
}
