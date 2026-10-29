package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Orange
import com.rigcheck.app.ui.theme.RigCheckStyles

/** What a numbered badge draws with, named so its test holds exactly these to AA: the ink digit on the orange fill. */
object RigCheckNumberBadgeColors {
    val fill = Orange
    val digit = Ink
}

// components.md, "Text field": "Hint numbers on the Scale screen carry an orange badge (22 dp, `ink` digit) in front of
// the label"; "Reference card": orange numbered badges (24 dp) drawn on the ticket image. The same number is on the
// photo, in the legend and in front of the field's label, so the match is by number.
@Composable
fun RigCheckNumberBadge(number: Int, modifier: Modifier = Modifier, size: Dp = 22.dp) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier.size(size).background(RigCheckNumberBadgeColors.fill, CircleShape),
    ) {
        Text("$number", style = RigCheckStyles.label, color = RigCheckNumberBadgeColors.digit)
    }
}
