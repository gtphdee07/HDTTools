package com.rigcheck.app.ui.screens

import android.text.format.DateUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.isImeVisible
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.CreditBalanceChip
import com.rigcheck.app.ui.components.FeedbackLink
import com.rigcheck.app.ui.components.RigCheckAccount
import com.rigcheck.app.ui.components.RigCheckAccountSheet
import com.rigcheck.app.ui.components.RigCheckAccountStatus
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckButtonKind
import com.rigcheck.app.ui.components.RigCheckButtonSize
import com.rigcheck.app.ui.components.RigCheckDialog
import com.rigcheck.app.ui.components.RigCheckEmptyState
import com.rigcheck.app.ui.components.RigCheckLogo
import com.rigcheck.app.ui.components.RigCheckRigCard
import com.rigcheck.app.ui.components.RigCheckTextField
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.components.chipBelowTitle
import com.rigcheck.app.ui.theme.DangerText
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.PurpleDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.TintPurple
import java.time.Instant
import kotlinx.coroutines.launch

// Below this content width (a 360 dp phone is 328 dp of content), "History" goes under the heading, full width
// (resize-rules.md, "360 x 640").
private val HistoryBesideHeadingMinWidth = 360.dp

@Composable
fun RigPickerScreen(
    recentRigs: List<RecentRig>,
    creditBalance: Int?,
    onSelectRecentRig: (RecentRig) -> Unit,
    onStartNewRig: (String) -> Unit,
    onOpenPaywall: () -> Unit,
    onOpenHistory: () -> Unit = {},
    // Whether the account is signed out: then the balance chip says "0 scans", not "…", and the header says
    // "Not signed in".
    signedOut: Boolean = false,
    // The signed-in account's email (its id if it has none): the header says "Signed in as" and it. null with
    // `signedOut` false is an account still being looked up: the header has no account row yet.
    accountLabel: String? = null,
    // Signed out: the account row goes to sign-in (the same route the chip takes). Signed in: the sheet's Sign out.
    onSignIn: () -> Unit = {},
    onSignOut: () -> Unit = {},
    // Deletes a Rig from the Garage: true once it is gone, false if it could not be deleted and is still
    // there. Passed only when Rigs can be deleted (a signed-in account); with null no Rig has a delete control.
    onDeleteRig: (suspend (RecentRig) -> Boolean)? = null,
    // A paid Scan is out, from the Chooser the user backed out of or otherwise: the sheet offers no Sign out until it
    // answers (#197).
    scanIsOut: Boolean = false,
) {
    var newRigNickname by remember { mutableStateOf("") }
    // The Rig the user has asked to delete and has not yet confirmed or cancelled.
    var rigToDelete by remember { mutableStateOf<RecentRig?>(null) }
    var accountSheetOpen by remember { mutableStateOf(false) }
    // Signing out takes the delete handler away; the open question goes with it and does not come back at the
    // next sign-in.
    LaunchedEffect(onDeleteRig == null) { if (onDeleteRig == null) rigToDelete = null }

    val account: RigCheckAccount? = when {
        signedOut -> RigCheckAccount.SignedOut
        accountLabel != null -> RigCheckAccount.SignedIn(accountLabel)
        else -> null
    }
    // The account the user is signed in as goes away with the sign-out; so does the sheet that offered it.
    LaunchedEffect(account is RigCheckAccount.SignedIn) { if (account !is RigCheckAccount.SignedIn) accountSheetOpen = false }

    // At a large font the chip goes to a row of its own under the name (resize-rules.md).
    val chipBelow = chipBelowTitle()
    // At a large font with the keyboard open the pinned bar would leave no room for the form: it drops the tagline and
    // the account row (the keyboard-open bar is compact, resize-rules.md) so the new-Rig panel can still scroll into view.
    @OptIn(ExperimentalLayoutApi::class)
    val compact = chipBelow && WindowInsets.isImeVisible
    val chip: @Composable (Modifier) -> Unit = { modifier ->
        CreditBalanceChip(
            balance = creditBalance,
            signedOut = signedOut,
            modifier = modifier.testTag(UiTags.PICKER_CREDIT_CHIP),
            onClick = onOpenPaywall,
        )
    }
    val belowTheNameAndLogo: (@Composable ColumnScope.() -> Unit)? = if ((account == null || compact) && !chipBelow) {
        null
    } else {
        {
            if (chipBelow) chip(Modifier.align(Alignment.End))
            if (account != null && !compact) {
                RigCheckAccountStatus(
                    account = account,
                    onClick = if (account is RigCheckAccount.SignedIn) ({ accountSheetOpen = true }) else onSignIn,
                    modifier = Modifier.testTag(UiTags.PICKER_ACCOUNT_STATUS),
                    avatarModifier = Modifier.testTag(UiTags.PICKER_ACCOUNT_AVATAR),
                )
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        RigCheckTopBar(
            title = "RigCheck",
            compact = compact,
            brand = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.weight(1f),
                ) {
                    RigCheckLogo(modifier = Modifier.testTag(UiTags.PICKER_LOGO))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            "RigCheck",
                            style = RigCheckStyles.topBarTitle,
                            color = Ink,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.testTag(UiTags.PICKER_APP_TITLE),
                        )
                        if (!compact) {
                            Text(
                                "Weight safety, before you roll",
                                style = RigCheckStyles.caption.copy(fontSize = 13.sp, lineHeight = 16.sp),
                                color = Ink,
                                modifier = Modifier.testTag(UiTags.PICKER_TAGLINE),
                            )
                        }
                    }
                }
            },
            end = { if (!chipBelow) chip(Modifier) },
            below = belowTheNameAndLogo,
        )

        // Everything under the bar scrolls as one column (resize-rules.md): the heading, the Rig cards, the new-Rig
        // panel and the feedback link.
        Column(
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 24.dp),
        ) {
            HeadingRow(onOpenHistory)

            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                recentRigs.forEachIndexed { index, rig ->
                    RecentRigCard(
                        rig = rig,
                        index = index,
                        onClick = { onSelectRecentRig(rig) },
                        onAskDelete = if (onDeleteRig != null) ({ rigToDelete = rig }) else null,
                    )
                }
                if (recentRigs.isEmpty()) {
                    RigCheckEmptyState(
                        title = "No saved rigs yet",
                        text = "Finish a check and your rig shows up here. Manual entry is free.",
                        mark = { RigCheckLogo() },
                        modifier = Modifier.testTag(UiTags.PICKER_EMPTY_STATE),
                    )
                }
            }

            NewRigPanel(
                nickname = newRigNickname,
                onNicknameChange = { newRigNickname = it },
                onCreate = { onStartNewRig(newRigNickname.trim()) },
            )
            FeedbackLink(
                modifier = Modifier.fillMaxWidth(),
                linkModifier = Modifier.testTag(UiTags.PICKER_FEEDBACK_LINK),
            )
        }
    }

    val asked = rigToDelete
    if (asked != null && onDeleteRig != null) {
        DeleteRigDialog(rig = asked, onDelete = onDeleteRig, onClose = { rigToDelete = null })
    }

    if (accountSheetOpen && account is RigCheckAccount.SignedIn) {
        RigCheckAccountSheet(
            account = account,
            onSignOut = {
                accountSheetOpen = false
                onSignOut()
            },
            onDismiss = { accountSheetOpen = false },
            modifier = Modifier.testTag(UiTags.PICKER_ACCOUNT_MENU),
            emailModifier = Modifier.testTag(UiTags.PICKER_ACCOUNT_MENU_EMAIL),
            signOutModifier = Modifier.testTag(UiTags.PICKER_SIGN_OUT_BUTTON),
            cancelModifier = Modifier.testTag(UiTags.PICKER_ACCOUNT_MENU_CANCEL),
            signOutUnavailableReason = ScanMessages.SIGN_OUT_UNAVAILABLE.takeIf { scanIsOut },
        )
    }
}

@Composable
private fun HeadingRow(onOpenHistory: () -> Unit) {
    BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
        val beside = maxWidth >= HistoryBesideHeadingMinWidth
        val heading: @Composable (Modifier) -> Unit = { modifier ->
            Column(modifier = modifier) {
                Text(
                    "Which rig?",
                    style = RigCheckStyles.heading,
                    color = Ink,
                    modifier = Modifier.testTag(UiTags.PICKER_HEADING),
                )
                Text(
                    "Pick one you have checked before, or start a new one.",
                    style = RigCheckStyles.body.copy(fontSize = 16.sp, lineHeight = 22.sp),
                    color = InkMuted,
                    modifier = Modifier.testTag(UiTags.PICKER_SUBHEADING),
                )
            }
        }
        val history: @Composable (Modifier) -> Unit = { modifier ->
            RigCheckButton(
                text = "History",
                onClick = onOpenHistory,
                kind = RigCheckButtonKind.Secondary,
                size = RigCheckButtonSize.Compact,
                icon = Icons.Outlined.Schedule,
                modifier = modifier.testTag(UiTags.OPEN_HISTORY),
            )
        }
        if (beside) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
                heading(Modifier.weight(1f))
                history(Modifier)
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                heading(Modifier)
                history(Modifier.fillMaxWidth())
            }
        }
    }
}

// components.md, "Panel (tinted block)": a purple panel, 24 dp radius, 16 dp padding and 12 dp gaps, holding the
// label, the nickname field and Create (disabled until the nickname is not blank).
@Composable
private fun NewRigPanel(nickname: String, onNicknameChange: (String) -> Unit, onCreate: () -> Unit) {
    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .background(TintPurple, RoundedCornerShape(Radii.Panel))
            .padding(16.dp),
    ) {
        Text(
            "Or start a new rig",
            style = RigCheckStyles.title,
            color = PurpleDeep,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.PICKER_NEW_RIG_LABEL),
        )
        RigCheckTextField(
            label = null,
            value = nickname,
            onValueChange = onNicknameChange,
            placeholder = "Rig nickname",
            inputModifier = Modifier.testTag(UiTags.PICKER_NEW_RIG_INPUT),
        )
        RigCheckButton(
            text = "Create",
            onClick = onCreate,
            enabled = nickname.isNotBlank(),
            modifier = Modifier.testTag(UiTags.PICKER_CREATE_BUTTON),
        )
    }
}

// Asks, then deletes. It closes when the Rig is gone or the user cancels; after a failed delete it stays, with
// the error, for another try (as Web's RigDeleteConfirm does).
@Composable
private fun DeleteRigDialog(rig: RecentRig, onDelete: suspend (RecentRig) -> Boolean, onClose: () -> Unit) {
    var deleting by remember { mutableStateOf(false) }
    var failed by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    // The design's dialog (components.md, "Dialog"; frames delete_rig_dialog__question, __deleting and __delete_failed):
    // the question as its heading, the body, and after a failed delete the error in danger-text above the buttons;
    // "Yes, delete" in the destructive button, then Cancel as a ghost, stacked full width.
    RigCheckDialog(
        // Back and a tap outside cancel, but not while the delete runs.
        onDismissRequest = { if (!deleting) onClose() },
        modifier = Modifier.testTag(UiTags.DELETE_RIG_DIALOG),
        title = {
            Text(
                "Delete \"${rig.nickname}\"?",
                style = RigCheckStyles.titleLg,
                color = Ink,
                modifier = Modifier.testTag(UiTags.DELETE_RIG_TITLE),
            )
        },
        body = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "This frees its spot in your Garage and can't be undone.",
                    style = RigCheckStyles.body.copy(lineHeight = 24.sp),
                    color = Ink,
                    modifier = Modifier.testTag(UiTags.DELETE_RIG_BODY),
                )
                if (failed) {
                    Text(
                        "We couldn't delete \"${rig.nickname}\". It's still in your Garage; please try again.",
                        style = RigCheckStyles.bodySm.copy(fontWeight = FontWeight.Medium),
                        color = DangerText,
                        modifier = Modifier.testTag(UiTags.DELETE_RIG_ERROR),
                    )
                }
            }
        },
    ) {
        RigCheckButton(
            text = if (deleting) "Deleting…" else "Yes, delete",
            onClick = {
                deleting = true
                failed = false
                scope.launch {
                    val deleted = onDelete(rig)
                    deleting = false
                    if (deleted) onClose() else failed = true
                }
            },
            kind = RigCheckButtonKind.Destructive,
            size = RigCheckButtonSize.Dialog,
            enabled = !deleting,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.DELETE_RIG_CONFIRM),
        )
        RigCheckButton(
            text = "Cancel",
            onClick = onClose,
            kind = RigCheckButtonKind.Ghost,
            size = RigCheckButtonSize.Dialog,
            enabled = !deleting,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.DELETE_RIG_CANCEL),
        )
    }
}

@Composable
private fun RecentRigCard(rig: RecentRig, index: Int, onClick: () -> Unit, onAskDelete: (() -> Unit)?) {
    val subtitle = listOfNotNull(rig.truck.description, rig.trailer.description)
        .filter { it.isNotBlank() }
        .joinToString(" · ")
    val relativeTime = remember(rig.lastUsedAt) {
        runCatching {
            DateUtils.getRelativeTimeSpanString(
                Instant.parse(rig.lastUsedAt).toEpochMilli(),
                System.currentTimeMillis(),
                DateUtils.MINUTE_IN_MILLIS,
            ).toString()
        }.getOrDefault("")
    }

    // The card's tag is on its body, the part a tap starts a check from: it merges the Rig's words into one node, and
    // the delete bin beside it is its own control, tagged apart.
    RigCheckRigCard(
        nickname = rig.nickname,
        subtitle = subtitle,
        lastChecked = relativeTime.takeIf { it.isNotBlank() }?.let { "Last checked $it" },
        index = index,
        onClick = onClick,
        onDelete = onAskDelete,
        bodyModifier = Modifier.testTag(UiTags.PICKER_RIG_CARD),
        deleteModifier = Modifier.testTag(UiTags.PICKER_RIG_DELETE),
        avatarModifier = Modifier.testTag(UiTags.PICKER_RIG_AVATAR),
        nicknameModifier = Modifier.testTag(UiTags.PICKER_RIG_NICKNAME),
        subtitleModifier = Modifier.testTag(UiTags.PICKER_RIG_SUBTITLE),
        lastCheckedModifier = Modifier.testTag(UiTags.PICKER_RIG_LAST_CHECKED),
    )
}
