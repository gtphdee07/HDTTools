package com.rigcheck.app.domain

data class VerdictInfo(
    val headline: String,
    val subline: String,
    val tone: Tone,
)

fun verdictFor(items: List<BreakdownItem>): VerdictInfo {
    val anyFail = items.any { it.tone == Tone.WARNING }
    return if (anyFail) {
        VerdictInfo(
            headline = "Not Safe to Tow",
            subline = "One or more axles are over their rated limit — see the breakdown below.",
            tone = Tone.WARNING,
        )
    } else {
        VerdictInfo(
            headline = "Safe to Tow",
            subline = "Every axle checks out under its rated limit.",
            tone = Tone.SUCCESS,
        )
    }
}
