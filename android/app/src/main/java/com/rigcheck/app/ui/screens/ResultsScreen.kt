package com.rigcheck.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.ui.GarageNotice
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.EstimatedFiguresNotice
import com.rigcheck.app.ui.components.RigCheckBreakdownRow
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckButtonKind
import com.rigcheck.app.ui.components.RigCheckButtonSize
import com.rigcheck.app.ui.components.RigCheckFooter
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.components.RigCheckTopBarColors
import com.rigcheck.app.ui.components.RigCheckVerdictBand
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Elevations
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private val DATE_FORMAT = DateTimeFormatter.ofPattern("MMM d, yyyy")

// The skeleton the design gives this screen (resize-rules.md, "What scrolls and what is pinned"): the top bar (Back, the
// Rig's name over the date) is pinned at the top; the verdict, the notices, the breakdown and the footer note scroll as
// one page (the breakdown card no longer scrolls inside itself); "Start another check" is pinned in the footer. In the
// scroll, the notices come in the frames' order: the estimate, the Garage (with Get Pro under it), the History.
@Composable
fun ResultsScreen(
    rigNickname: String,
    breakdown: List<BreakdownItem>,
    verdict: VerdictInfo,
    onStartAnother: () -> Unit,
    garageNotice: GarageNotice? = null,
    historyNotice: String? = null,
    onGetPro: () -> Unit = {},
    onBack: () -> Unit = {},
) {
    val rigName = rigNickname.ifBlank { "Rig" }
    Column(modifier = Modifier.fillMaxSize()) {
        RigCheckTopBar(
            title = rigName,
            onBack = onBack,
            backModifier = Modifier.testTag(UiTags.RESULTS_BACK),
            brand = {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        rigName,
                        style = RigCheckStyles.topBarTitle,
                        color = RigCheckTopBarColors.content,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.testTag(UiTags.RESULTS_RIG_NAME),
                    )
                    Text(
                        LocalDate.now().format(DATE_FORMAT),
                        style = RigCheckStyles.caption.copy(lineHeight = 16.sp),
                        color = RigCheckTopBarColors.content,
                        modifier = Modifier.testTag(UiTags.RESULTS_DATE),
                    )
                }
            },
        )
        Column(
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(SurfaceSunken)
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, top = 16.dp, end = 16.dp, bottom = 24.dp),
        ) {
            RigCheckVerdictBand(
                verdict,
                modifier = Modifier.testTag(UiTags.RESULTS_VERDICT),
                iconModifier = Modifier.testTag(UiTags.RESULTS_VERDICT_ICON),
            )

            if (breakdown.any { it.estimated }) EstimatedFiguresNotice()

            if (garageNotice != null) GarageNoticeBlock(garageNotice, onGetPro)

            if (historyNotice != null) {
                // The check went ahead; only its History entry did not reach the account.
                RigCheckNoticeCard(text = historyNotice, tone = RigCheckNoticeTone.Info, modifier = Modifier.testTag(UiTags.HISTORY_NOTICE))
            }

            BreakdownCard(breakdown)

            Text(
                "Experimental tool, not a certified safety decision.",
                style = RigCheckStyles.caption,
                color = InkMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.RESULTS_FOOTER_NOTE),
            )
        }
        RigCheckFooter {
            RigCheckButton(
                text = "Start another check",
                onClick = onStartAnother,
                modifier = Modifier.testTag(UiTags.RESULTS_START_ANOTHER_BUTTON),
            )
        }
    }
}

// The check went ahead; only its Rig did not reach the Garage. A Free account with a full Garage is offered Pro, in a
// ghost button under the notice.
@Composable
private fun GarageNoticeBlock(notice: GarageNotice, onGetPro: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        RigCheckNoticeCard(text = notice.message, tone = RigCheckNoticeTone.Info, modifier = Modifier.testTag(UiTags.GARAGE_NOTICE))
        if (notice.offerPro) {
            RigCheckButton(
                text = "Get Pro for a bigger Garage",
                onClick = onGetPro,
                kind = RigCheckButtonKind.Ghost,
                size = RigCheckButtonSize.Compact,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.GARAGE_NOTICE_GET_PRO),
            )
        }
    }
}

// components.md, "Breakdown row" and the frames: one white card (24 dp radius, a 1 dp border, shadow sm) with the rows
// flat in it. A 1 dp rule sets a row off from the one above it when either of the two has a note: the frames draw none
// between the two plain axle rows and one before every row from the first with a note on.
@Composable
private fun BreakdownCard(breakdown: List<BreakdownItem>) {
    Surface(
        shape = RoundedCornerShape(Radii.Panel),
        color = SurfaceWhite,
        border = BorderStroke(1.dp, Border),
        shadowElevation = Elevations.Sm,
        modifier = Modifier.fillMaxWidth().testTag(UiTags.RESULTS_BREAKDOWN_CARD),
    ) {
        Column(modifier = Modifier.padding(vertical = 4.dp)) {
            breakdown.forEachIndexed { index, item ->
                val setOff = index > 0 && (item.note != null || breakdown[index - 1].note != null)
                if (setOff) HorizontalDivider(color = Border, modifier = Modifier.padding(horizontal = 16.dp))
                RigCheckBreakdownRow(item)
            }
        }
    }
}
