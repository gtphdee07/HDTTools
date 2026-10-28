package com.rigcheck.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.creditChipDescription
import com.rigcheck.app.ui.creditChipLabel
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

// The scan balance chip, as the design draws it (components.md, "Credit chip"): 48 dp high, a white pill with a
// small shadow, a 26 dp camera icon and the balance. null balance = not known: "…" while an account's balance
// loads, "0 scans" when signed out (creditChipLabel). Shown near every Scan Photo entry point,
// per ANDROID_DESIGN_BRIEF.md ("contextual, not a nav destination"). An optional onClick turns it into a "get more
// scans" affordance to the Paywall - the only other entry point besides tapping Scan Photo at 0 credits.
@Composable
fun CreditBalanceChip(
    balance: Int?,
    modifier: Modifier = Modifier,
    signedOut: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    val description = creditChipDescription(balance, signedOut)
    Surface(
        shape = RoundedCornerShape(Sizes.CreditChip),
        color = SurfaceWhite,
        shadowElevation = Elevations.Sm,
        modifier = modifier
            .heightIn(min = Sizes.CreditChip)
            .semantics { contentDescription = description }
            .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.heightIn(min = Sizes.CreditChip).padding(horizontal = 16.dp),
        ) {
            Icon(
                Icons.Filled.CameraAlt,
                contentDescription = null,
                modifier = Modifier.size(Sizes.CreditChipIcon),
                tint = Ink,
            )
            Text(creditChipLabel(balance, signedOut), style = RigCheckStyles.chip, color = Ink)
        }
    }
}
