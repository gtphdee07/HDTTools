package com.rigcheck.app.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import kotlin.math.pow

// WCAG 2 contrast, for the tests that hold each shared component's text colour to AA against its own fill.

/** Relative luminance of an opaque colour. */
private fun luminance(color: Color): Double {
    fun channel(c: Float): Double {
        val v = c.toDouble()
        return if (v <= 0.03928) v / 12.92 else ((v + 0.055) / 1.055).pow(2.4)
    }
    return 0.2126 * channel(color.red) + 0.7152 * channel(color.green) + 0.0722 * channel(color.blue)
}

/** The contrast ratio of [foreground] on [background]; a translucent colour is first laid over [behind]. */
fun contrastRatio(foreground: Color, background: Color, behind: Color = Surface): Double {
    val fill = background.compositeOver(behind)
    val text = foreground.compositeOver(fill)
    val a = luminance(text)
    val b = luminance(fill)
    return (maxOf(a, b) + 0.05) / (minOf(a, b) + 0.05)
}

const val AA_NORMAL_TEXT = 4.5
const val AA_LARGE_TEXT = 3.0

fun meetsAa(foreground: Color, background: Color, largeText: Boolean = false, behind: Color = Surface): Boolean =
    contrastRatio(foreground, background, behind) >= if (largeText) AA_LARGE_TEXT else AA_NORMAL_TEXT
