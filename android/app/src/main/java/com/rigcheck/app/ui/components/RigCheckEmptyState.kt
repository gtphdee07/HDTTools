package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.BorderStrong
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken

// components.md, "Empty state": a dashed 2 dp border-strong outline, 24 dp radius, the surface-sunken fill, a 56 dp
// mark, then the title and the text beside it (the frames rig_picker__signed_out_empty and history__empty draw the
// mark at the left). The mark is a slot: the app logo goes there. With no title (the History's frame draws one line of
// words), the text is the body style in ink, as that frame has it; with one, the text is the muted line under it.
// `textModifier` is for the tag of the words (the map measures the words, not the panel around them).
@Composable
fun RigCheckEmptyState(
    title: String?,
    text: String,
    modifier: Modifier = Modifier,
    mark: (@Composable () -> Unit)? = null,
    textModifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(Radii.Panel)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .fillMaxWidth()
            .background(SurfaceSunken, shape)
            .drawBehind {
                drawRoundRect(
                    color = BorderStrong,
                    cornerRadius = CornerRadius(Radii.Panel.toPx()),
                    style = Stroke(width = 2.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(10.dp.toPx(), 8.dp.toPx()))),
                )
            }
            .padding(20.dp),
    ) {
        if (mark != null) Box(modifier = Modifier.size(56.dp)) { mark() }
        Column(modifier = Modifier.weight(1f)) {
            if (title != null) {
                Text(title, style = RigCheckStyles.title, color = Ink)
                Text(text, style = RigCheckStyles.bodyMd, color = InkMuted, modifier = textModifier)
            } else {
                Text(text, style = RigCheckStyles.body, color = Ink, modifier = textModifier)
            }
        }
    }
}
