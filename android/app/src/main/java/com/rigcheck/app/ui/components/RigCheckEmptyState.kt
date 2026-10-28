package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.BorderStrong
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken

// components.md, "Empty state": a dashed 2 dp border-strong outline, 24 dp radius, the surface-sunken fill, a 56 dp
// mark at the top, then the title and the text. The mark is a slot: the app logo goes there.
@Composable
fun RigCheckEmptyState(
    title: String,
    text: String,
    modifier: Modifier = Modifier,
    mark: (@Composable () -> Unit)? = null,
) {
    val shape = RoundedCornerShape(Radii.Panel)
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
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
            .padding(24.dp),
    ) {
        if (mark != null) Column(modifier = Modifier.size(56.dp)) { mark() }
        Text(title, style = RigCheckStyles.title, color = Ink, textAlign = TextAlign.Center)
        Text(text, style = RigCheckStyles.bodyMd, color = InkMuted, textAlign = TextAlign.Center)
    }
}
