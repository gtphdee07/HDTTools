package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Teal

/**
 * At a large font the title and the balance chip no longer fit one row on a small phone: the chip moves to a row of its
 * own under the title (resize-rules.md, "Font scale 2.0"). From a font scale of 1.6, where the chip, at least 48 dp
 * high and one line long, already takes more than half of a 360 dp phone.
 */
@Composable
fun chipBelowTitle(): Boolean = LocalDensity.current.fontScale >= 1.6f

/** What the bar draws with, named so its test holds exactly these to AA: ink on teal. */
object RigCheckTopBarColors {
    val fill = Teal
    val content = Ink
}

// components.md, "Top app bar (header)": teal fill, 24 dp bottom corners, shadow sm, 16 dp side padding. Row 1 holds
// the Back button (when there is somewhere to go back to), the title, then the end content (the balance chip);
// an optional row 2 (the account status, or the step indicator) goes under it. While the keyboard is open the bar is
// compact: less bottom padding, and the caller leaves row 2 out. The status bar is not part of this component:
// RigCheckApp already pads the app inside the system bars.
@Composable
fun RigCheckTopBar(
    title: String,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    backEnabled: Boolean = true,
    compact: Boolean = false,
    // The tags of the title text and of the Back button (a screen tags them; `modifier` is for the whole bar).
    titleModifier: Modifier = Modifier,
    backModifier: Modifier = Modifier,
    // The Rig picker's variant: the logo, the name and the tagline in place of the plain title (the content brings its
    // own weight, as the title does).
    brand: (@Composable RowScope.() -> Unit)? = null,
    end: @Composable RowScope.() -> Unit = {},
    below: (@Composable ColumnScope.() -> Unit)? = null,
) {
    Surface(
        color = RigCheckTopBarColors.fill,
        contentColor = RigCheckTopBarColors.content,
        shape = RoundedCornerShape(bottomStart = Radii.Band, bottomEnd = Radii.Band),
        shadowElevation = Elevations.Sm,
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = if (compact) 12.dp else 16.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (onBack != null) {
                    RigCheckIconButton(
                        icon = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        onClick = onBack,
                        enabled = backEnabled,
                        onTeal = true,
                        modifier = backModifier,
                    )
                }
                if (brand != null) {
                    brand()
                } else {
                    Text(
                        title,
                        style = RigCheckStyles.topBarTitle,
                        color = RigCheckTopBarColors.content,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f).then(titleModifier),
                    )
                }
                end()
            }
            if (below != null) below()
        }
    }
}
