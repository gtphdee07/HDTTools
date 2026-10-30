package com.rigcheck.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.OrangeDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken
import com.rigcheck.app.ui.theme.TintOrange
import com.rigcheck.app.ui.theme.TintRed

/** Info is quiet; Scan and Warn are the orange tone (a Scan used, estimated figures); Error is red. */
enum class RigCheckNoticeTone { Info, Scan, Warn, Error }

data class RigCheckNoticeColors(val container: Color, val text: Color, val icon: Color, val border: Color?)

fun rigCheckNoticeColors(tone: RigCheckNoticeTone): RigCheckNoticeColors = when (tone) {
    RigCheckNoticeTone.Info -> RigCheckNoticeColors(SurfaceSunken, Ink, InkMuted, Border)
    RigCheckNoticeTone.Scan, RigCheckNoticeTone.Warn -> RigCheckNoticeColors(TintOrange, Ink, OrangeDeep, null)
    RigCheckNoticeTone.Error -> RigCheckNoticeColors(TintRed, Ink, DangerText, null)
}

private fun defaultNoticeIcon(tone: RigCheckNoticeTone): ImageVector =
    if (tone == RigCheckNoticeTone.Info) Icons.Filled.Info else Icons.Filled.Warning

// components.md, "Notice card": 14 dp radius, 12 x 14 padding, a 22 dp leading icon, the text in `body-sm`, an
// optional title in `title-sm`. The text is always ink; the tone shows in the fill and the icon.
@Composable
fun RigCheckNoticeCard(
    text: String,
    tone: RigCheckNoticeTone,
    modifier: Modifier = Modifier,
    title: String? = null,
    icon: ImageVector? = defaultNoticeIcon(tone),
    // For the tag of the words (the design measures the words, not the card around them).
    textModifier: Modifier = Modifier,
) {
    val colors = rigCheckNoticeColors(tone)
    RigCheckNoticeCard(tone = tone, modifier = modifier, title = title, icon = icon, contentSpacing = 2.dp) {
        Text(text, style = RigCheckStyles.bodySm, color = colors.text, modifier = textModifier)
    }
}

// The same card around content of its own (the estimated-figures notice holds a list), with no icon when `icon` is
// null: that notice keeps the warning emoji its frozen title already carries, and the design draws no second one.
@Composable
fun RigCheckNoticeCard(
    tone: RigCheckNoticeTone,
    modifier: Modifier = Modifier,
    title: String? = null,
    icon: ImageVector? = defaultNoticeIcon(tone),
    // Between the title and the content, and between the content's own lines.
    contentSpacing: Dp = 6.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    val colors = rigCheckNoticeColors(tone)
    Surface(
        shape = RoundedCornerShape(Radii.Card),
        color = colors.container,
        border = colors.border?.let { BorderStroke(1.dp, it) },
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
        ) {
            if (icon != null) Icon(icon, contentDescription = null, tint = colors.icon, modifier = Modifier.size(22.dp))
            Column(verticalArrangement = Arrangement.spacedBy(contentSpacing), modifier = Modifier.weight(1f)) {
                if (title != null) Text(title, style = RigCheckStyles.titleSm, color = colors.text)
                content()
            }
        }
    }
}
