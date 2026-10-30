package com.rigcheck.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.OnTealWash
import com.rigcheck.app.ui.theme.Opacity
import com.rigcheck.app.ui.theme.Purple
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

/** Who the Rig picker's header says is using the app: nobody, or this account (its email, or its id if it has none). */
sealed interface RigCheckAccount {
    data object SignedOut : RigCheckAccount
    data class SignedIn(val label: String) : RigCheckAccount
}

/**
 * What the account row draws with, named so its test holds exactly these to AA: ink on the wash. The design draws the
 * "Sign in" label in teal-deep, which is 4.3:1 on the wash over the teal bar (AA needs 4.5:1), so it is ink, in bold,
 * and the chevron says it is a link.
 */
object RigCheckAccountStatusColors {
    val fill = OnTealWash
    val text = Ink
    val signInLabel = Ink
    val avatarFill = Purple
    val avatarInitial = SurfaceWhite
}

internal fun accountInitial(label: String): String = label.trim().take(1).uppercase()

private fun accountStatusDescription(account: RigCheckAccount): String = when (account) {
    RigCheckAccount.SignedOut -> "Not signed in. Sign in"
    is RigCheckAccount.SignedIn -> "Account: signed in as ${account.label}. Opens account menu"
}

// components.md, "Account status row": 48 dp high, 14 dp radius, the on-teal wash, a 32 dp avatar (purple with a white
// initial when signed in, white with a person icon when signed out), two lines ("Signed in as" and the email, which
// is cut short with an ellipsis; or "Not signed in" and a "Sign in" label) and a chevron. The whole row is one target.
@Composable
fun RigCheckAccountStatus(
    account: RigCheckAccount,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    avatarModifier: Modifier = Modifier,
) {
    val source = remember { MutableInteractionSource() }
    val focused by source.collectIsFocusedAsState()
    val shape = RoundedCornerShape(Radii.Card)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .focusRing(focused, cornerRadius = Radii.Card)
            .background(RigCheckAccountStatusColors.fill, shape)
            .semantics { contentDescription = accountStatusDescription(account) }
            .clickable(interactionSource = source, indication = ripple(), role = Role.Button, onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 6.dp),
    ) {
        when (account) {
            RigCheckAccount.SignedOut -> {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = avatarModifier.size(32.dp).background(SurfaceWhite, CircleShape),
                ) {
                    Icon(Icons.Filled.Person, contentDescription = null, tint = Ink, modifier = Modifier.size(20.dp))
                }
                Text(
                    "Not signed in",
                    style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Bold),
                    color = RigCheckAccountStatusColors.text,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    "Sign in",
                    style = RigCheckStyles.buttonCompact.copy(fontWeight = FontWeight.Bold),
                    color = RigCheckAccountStatusColors.signInLabel,
                )
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = Ink)
            }
            is RigCheckAccount.SignedIn -> {
                AccountAvatar(account.label, size = 32, modifier = avatarModifier)
                // Two lines of 14 and 18 dp, within the 48 dp the row is at least.
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        "Signed in as",
                        style = RigCheckStyles.micro.copy(lineHeight = 14.sp),
                        color = RigCheckAccountStatusColors.text,
                    )
                    Text(
                        account.label,
                        style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Bold, lineHeight = 18.sp),
                        color = RigCheckAccountStatusColors.text,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Icon(Icons.Filled.KeyboardArrowDown, contentDescription = null, tint = Ink)
            }
        }
    }
}

@Composable
private fun AccountAvatar(label: String, size: Int, modifier: Modifier = Modifier) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier.size(size.dp).background(RigCheckAccountStatusColors.avatarFill, CircleShape),
    ) {
        // Outfit 700, 15 sp in the 32 dp avatar of the row and 20 sp in the 48 dp avatar of the sheet.
        Text(
            accountInitial(label),
            style = RigCheckStyles.title.copy(fontSize = if (size >= 48) 20.sp else 15.sp, lineHeight = 22.sp),
            color = RigCheckAccountStatusColors.avatarInitial,
        )
    }
}

// components.md, "Bottom sheet": 24 dp top corners, white, a 40 x 4 handle, 16 dp side padding, 64 dp bottom padding.
// The account sheet is the avatar and the email, a destructive "Sign out", then a ghost "Cancel". The scrim, a tap
// outside, Cancel and the system Back all dismiss it.
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RigCheckAccountSheet(
    account: RigCheckAccount.SignedIn,
    onSignOut: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    emailModifier: Modifier = Modifier,
    signOutModifier: Modifier = Modifier,
    cancelModifier: Modifier = Modifier,
    // Why Sign out is not offered right now (a paid Scan is out, #197); null when it is. The button is disabled and the
    // words are shown under it, so the reason is not left to colour alone.
    signOutUnavailableReason: String? = null,
    signOutReasonModifier: Modifier = Modifier,
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        // The sheet's own 64 dp at the bottom is the allowance for the navigation bar (see below).
        contentWindowInsets = { WindowInsets(0, 0, 0, 0) },
        shape = RoundedCornerShape(topStart = Radii.SheetTop, topEnd = Radii.SheetTop),
        containerColor = SurfaceWhite,
        scrimColor = Ink.copy(alpha = Opacity.Scrim),
        // The design's handle is a picture, drawn at the top of the content below. Material's own handle slot is a
        // clickable that expands and collapses the sheet, which this one never does (it has no half-open state), and
        // it gave a screen reader an unlabelled 40 x 16 dp target (the accessibility checks of #197 found it).
        dragHandle = null,
        modifier = modifier,
    ) {
        // 288 dp in all (the map's new_height): the handle (12 + 4), 16 dp, the avatar row (48), 20 dp, Sign out (56),
        // 12 dp, Cancel (56) and the 64 dp that clears the 3-button bar.
        Box(
            modifier = Modifier
                .padding(top = 12.dp)
                .align(Alignment.CenterHorizontally)
                .width(40.dp)
                .height(4.dp)
                .background(Border, RoundedCornerShape(2.dp))
                .clearAndSetSemantics {},
        )
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 64.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AccountAvatar(account.label, size = 48)
                Column {
                    Text("Signed in as", style = RigCheckStyles.micro, color = InkMuted)
                    Text(
                        account.label,
                        style = RigCheckStyles.titleSm,
                        color = Ink,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = emailModifier,
                    )
                }
            }
            Spacer(Modifier.height(20.dp))
            RigCheckButton(
                text = "Sign out",
                onClick = onSignOut,
                kind = RigCheckButtonKind.Destructive,
                enabled = signOutUnavailableReason == null,
                icon = Icons.AutoMirrored.Filled.Logout,
                modifier = signOutModifier,
            )
            if (signOutUnavailableReason != null) {
                Spacer(Modifier.height(8.dp))
                Text(signOutUnavailableReason, style = RigCheckStyles.bodySm, color = InkMuted, modifier = signOutReasonModifier)
            }
            Spacer(Modifier.height(12.dp))
            RigCheckButton(
                text = "Cancel",
                onClick = onDismiss,
                kind = RigCheckButtonKind.Ghost,
                modifier = cancelModifier,
            )
        }
    }
}
