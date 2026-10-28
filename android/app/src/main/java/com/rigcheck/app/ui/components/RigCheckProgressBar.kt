package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.Pine
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.Slate

enum class RigCheckProgressTone { Pass, Fail, NotChecked }

/** components.md, "Progress bar": the track is #e7edf0. */
val ProgressTrack = Color(0xFFE7EDF0)

fun rigCheckProgressFill(tone: RigCheckProgressTone): Color = when (tone) {
    RigCheckProgressTone.Pass -> Pine
    RigCheckProgressTone.Fail -> DangerRed
    RigCheckProgressTone.NotChecked -> Slate
}

// components.md, "Progress bar": 10 dp, fully rounded, one fill on one track with no gap between them and no dot at
// the track end (Material 3's bar has both), so it is drawn directly. A fill over 100% stops at the end of the bar.
@Composable
fun RigCheckProgressBar(
    fraction: Float,
    tone: RigCheckProgressTone,
    modifier: Modifier = Modifier,
) {
    val clamped = fraction.coerceIn(0f, 1f)
    val fill = rigCheckProgressFill(tone)
    val shape = RoundedCornerShape(Sizes.ProgressBar / 2)
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(Sizes.ProgressBar)
            .clip(shape)
            .semantics { progressBarRangeInfo = ProgressBarRangeInfo(clamped, 0f..1f) }
            .drawBehind {
                drawRect(ProgressTrack)
                val radius = CornerRadius(size.height / 2)
                if (clamped > 0f) {
                    drawRoundRect(fill, size = Size(maxOf(size.width * clamped, size.height), size.height), cornerRadius = radius)
                }
            },
    )
}
