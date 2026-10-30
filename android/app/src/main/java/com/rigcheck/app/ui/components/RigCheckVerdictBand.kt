package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Cancel
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.dp
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.domain.VerdictStatus
import com.rigcheck.app.ui.theme.DangerRed
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Pine
import com.rigcheck.app.ui.theme.Purple
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** The band's fill and its icon: Safe pine and a tick, Not Safe danger and a cross, the two unsure ones purple and an "i". */
data class RigCheckVerdictLook(val fill: Color, val text: Color, val icon: ImageVector)

fun rigCheckVerdictLook(status: VerdictStatus): RigCheckVerdictLook = when (status) {
    VerdictStatus.PASS -> RigCheckVerdictLook(Pine, SurfaceWhite, Icons.Outlined.CheckCircle)
    VerdictStatus.FAIL -> RigCheckVerdictLook(DangerRed, SurfaceWhite, Icons.Outlined.Cancel)
    VerdictStatus.PARTIAL, VerdictStatus.INSUFFICIENT -> RigCheckVerdictLook(Purple, SurfaceWhite, Icons.Outlined.Info)
}

// resize-rules.md, "360 x 640": the band stacks its icon above the text under 380 dp of width.
private const val STACK_UNDER_DP = 380

// components.md, "Verdict band": 24 dp radius, shadow md, 20 dp padding; a 64 dp translucent circle (white at 22%)
// holding a 36 dp icon, the headline in `headline-verdict` and the subline in `body-md`, all white. The icon is
// different for each outcome, so the verdict never rests on colour alone. `iconModifier` is for the 64 dp circle
// (the map's `results.verdict_icon` is the circle, not the glyph in it).
@Composable
fun RigCheckVerdictBand(verdict: VerdictInfo, modifier: Modifier = Modifier, iconModifier: Modifier = Modifier) {
    val look = rigCheckVerdictLook(verdict.status)
    val stacked = LocalConfiguration.current.screenWidthDp < STACK_UNDER_DP
    Surface(
        shape = RoundedCornerShape(Radii.Band),
        color = look.fill,
        shadowElevation = Elevations.Md,
        modifier = modifier.fillMaxWidth(),
    ) {
        val circle: @Composable () -> Unit = {
            Box(
                contentAlignment = Alignment.Center,
                modifier = iconModifier.size(64.dp).background(SurfaceWhite.copy(alpha = 0.22f), CircleShape),
            ) {
                Icon(look.icon, contentDescription = null, tint = look.text, modifier = Modifier.size(36.dp))
            }
        }
        val words: @Composable (Modifier) -> Unit = { placement ->
            Column(verticalArrangement = Arrangement.spacedBy(4.dp), modifier = placement) {
                Text(verdict.headline, style = RigCheckStyles.headlineVerdict, color = look.text)
                Text(verdict.subline, style = RigCheckStyles.bodyMd, color = look.text)
            }
        }
        if (stacked) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.padding(20.dp)) {
                circle()
                words(Modifier)
            }
        } else {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier.padding(20.dp),
            ) {
                circle()
                words(Modifier.weight(1f))
            }
        }
    }
}
