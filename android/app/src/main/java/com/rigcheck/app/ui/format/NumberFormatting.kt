package com.rigcheck.app.ui.format

import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.Tone
import com.rigcheck.app.domain.formatWholeNumber
import kotlin.math.abs

fun formatLb(value: Double): String = "${formatWholeNumber(value)} lb"

fun badgeLabel(item: BreakdownItem): String =
    if (item.tone == Tone.SUCCESS) {
        "${formatWholeNumber(item.margin)} lb to spare"
    } else {
        "${formatWholeNumber(abs(item.margin))} lb over"
    }
