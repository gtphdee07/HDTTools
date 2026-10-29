package com.rigcheck.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.ui.ScanNotice
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.LabeledNumberField
import com.rigcheck.app.ui.components.LabeledTextField
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckNumberBadge
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.SurfaceSunken
import kotlin.math.roundToInt

// The numbered-callout pattern (not tap-and-hold zoom): the same number 1 to 5 is on the ticket photo, in the legend
// pill and in front of the field's label, so the match is by number, not by hover.
private val LEGEND = listOf("Scale location", "Steer", "Drive", "Trailer", "Gross")

/** The tag of a badge drawn on the ticket photo: this, then its number (1 to 5). */
internal const val SCALE_PHOTO_BADGE_TAG = "scale_photo_badge_"

// Where each badge sits on the ticket photo, as fractions of the whole photo: the scale location line, and the four
// weights beside their names. Position data for the badges the design draws, not a stored crop of a field.
private data class PhotoBadge(val number: Int, val x: Float, val y: Float)

private val PHOTO_BADGES = listOf(
    PhotoBadge(1, 0.24f, 0.545f),
    PhotoBadge(2, 0.50f, 0.465f),
    PhotoBadge(3, 0.50f, 0.513f),
    PhotoBadge(4, 0.50f, 0.559f),
    PhotoBadge(5, 0.50f, 0.600f),
)

// The map's 167 dp high ReferenceImage shows the part of the photo that holds those lines, so the five rows are far
// enough apart for 24 dp badges: this much of its width, from here across and from here down (fractions of the photo).
private const val WINDOW_LEFT = 0.22f
private const val WINDOW_WIDTH = 0.56f
private const val WINDOW_TOP = 0.44f
private val PHOTO_HEIGHT = 167.dp
private val PHOTO_BADGE_SIZE = 24.dp

@Composable
fun ScaleTicketEntryScreen(
    scale: ScaleTicket,
    onScaleChange: (ScaleTicket) -> Unit,
    onContinue: () -> Unit,
    scanNotice: ScanNotice? = null,
    onBack: () -> Unit = {},
) {
    EntryScreenFrame(
        title = "Scale Ticket",
        step = 3,
        onBack = onBack,
        titleModifier = Modifier.testTag(UiTags.SCALE_TITLE),
        backModifier = Modifier.testTag(UiTags.SCALE_BACK),
        stepModifier = Modifier.testTag(UiTags.SCALE_STEP_BAR),
        footer = {
            RigCheckButton(
                text = "Check Weights",
                onClick = onContinue,
                modifier = Modifier.testTag(UiTags.SCALE_CHECK_BUTTON),
            )
        },
    ) {
        scanNotice?.textFor(scale)?.let { text ->
            RigCheckNoticeCard(text = text, tone = RigCheckNoticeTone.Scan, modifier = Modifier.testTag(UiTags.SCAN_NOTICE))
        }

        Text(
            "Find these values on your CAT Scale printout.",
            style = RigCheckStyles.body,
            color = InkMuted,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.SCALE_INSTRUCTIONS),
        )

        TicketPhoto(modifier = Modifier.testTag(UiTags.SCALE_REFERENCE_IMAGE))
        Legend(modifier = Modifier.testTag(UiTags.SCALE_LEGEND))

        LabeledTextField(
            label = "Scale location",
            value = scale.locationName ?: "",
            onValueChange = { onScaleChange(scale.copy(locationName = it.ifBlank { null })) },
            labelBadge = { RigCheckNumberBadge(1) },
            modifier = Modifier.testTag(UiTags.SCALE_LOCATION),
        )
        LabeledNumberField(
            label = "Steer axle, lb",
            value = scale.steerAxleLb,
            onValueChange = { onScaleChange(scale.copy(steerAxleLb = it)) },
            unit = "lb",
            labelBadge = { RigCheckNumberBadge(2) },
            modifier = Modifier.testTag(UiTags.SCALE_STEER_FIELD),
        )
        LabeledNumberField(
            label = "Drive axle, lb",
            value = scale.driveAxleLb,
            onValueChange = { onScaleChange(scale.copy(driveAxleLb = it)) },
            unit = "lb",
            labelBadge = { RigCheckNumberBadge(3) },
            modifier = Modifier.testTag(UiTags.SCALE_DRIVE_FIELD),
        )
        LabeledNumberField(
            label = "Trailer axle(s), lb",
            value = scale.trailerAxleLb,
            onValueChange = { onScaleChange(scale.copy(trailerAxleLb = it)) },
            unit = "lb",
            labelBadge = { RigCheckNumberBadge(4) },
            modifier = Modifier.testTag(UiTags.SCALE_TRAILER_FIELD),
        )
        LabeledNumberField(
            label = "Gross weight, lb",
            value = scale.grossWeightLb,
            onValueChange = { onScaleChange(scale.copy(grossWeightLb = it)) },
            unit = "lb",
            labelBadge = { RigCheckNumberBadge(5) },
            modifier = Modifier.testTag(UiTags.SCALE_GROSS_FIELD),
        )
    }
}

// The ticket photo, as wide as the column and 167 dp high: the part of it that holds the scale location and the four
// weights, with the numbered badges drawn on the lines they stand for.
@Composable
private fun TicketPhoto(modifier: Modifier = Modifier) {
    val photo = ImageBitmap.imageResource(R.drawable.ref_scale_ticket)
    BoxWithConstraints(
        modifier = modifier.fillMaxWidth().height(PHOTO_HEIGHT).clip(RoundedCornerShape(Radii.Card)),
    ) {
        // The window, in the photo's pixels: its width is fixed, its height is what the box's shape asks for.
        val sourceWidth = photo.width * WINDOW_WIDTH
        val sourceHeight = sourceWidth * PHOTO_HEIGHT.value / maxWidth.value
        val sourceLeft = photo.width * WINDOW_LEFT
        val sourceTop = (photo.height * WINDOW_TOP).coerceAtMost(photo.height - sourceHeight)
        Canvas(modifier = Modifier.fillMaxSize().semantics { contentDescription = "CAT Scale ticket" }) {
            drawImage(
                image = photo,
                srcOffset = IntOffset(sourceLeft.roundToInt(), sourceTop.roundToInt()),
                srcSize = IntSize(sourceWidth.roundToInt(), sourceHeight.roundToInt()),
                dstSize = IntSize(size.width.roundToInt(), size.height.roundToInt()),
                filterQuality = FilterQuality.High,
            )
        }
        val half = PHOTO_BADGE_SIZE / 2
        PHOTO_BADGES.forEach { badge ->
            RigCheckNumberBadge(
                number = badge.number,
                size = PHOTO_BADGE_SIZE,
                modifier = Modifier
                    .offset(
                        x = maxWidth * ((badge.x * photo.width - sourceLeft) / sourceWidth) - half,
                        y = PHOTO_HEIGHT * ((badge.y * photo.height - sourceTop) / sourceHeight) - half,
                    )
                    .testTag("$SCALE_PHOTO_BADGE_TAG${badge.number}"),
            )
        }
    }
}

// Five numbered pills that wrap, in the badge style of the field labels (they replace the old orange text, which failed
// contrast): the number, then the same words as before.
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Legend(modifier: Modifier = Modifier) {
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier.fillMaxWidth(),
    ) {
        LEGEND.forEachIndexed { index, label ->
            Surface(
                shape = RoundedCornerShape(Radii.Pill),
                color = SurfaceSunken,
                border = BorderStroke(1.dp, Border),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(start = 4.dp, top = 4.dp, end = 14.dp, bottom = 4.dp),
                ) {
                    RigCheckNumberBadge(index + 1, size = 24.dp)
                    Text(label, style = RigCheckStyles.body, color = Ink)
                }
            }
        }
    }
}
