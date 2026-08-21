package com.rigcheck.app.domain

// status mirrors Python's verdict_for's explicit "status" field - never
// derive pass/fail from headline text (both "Not Safe to Tow" and "Not
// Enough Information" start with "Not").
enum class VerdictStatus { PASS, FAIL, PARTIAL, INSUFFICIENT }

data class VerdictInfo(
    val headline: String,
    val subline: String,
    val tone: Tone,
    val status: VerdictStatus,
)

fun verdictFor(items: List<BreakdownItem>): VerdictInfo {
    val tones = items.map { it.tone }
    val anyFail = tones.any { it == Tone.WARNING }
    val allInsufficient = tones.all { it == Tone.INSUFFICIENT }
    val anyInsufficient = tones.any { it == Tone.INSUFFICIENT }

    // A real failure always wins, even if other rows are insufficient -
    // never let missing data hide a genuine over-limit reading.
    return when {
        anyFail -> VerdictInfo(
            headline = "Not Safe to Tow",
            subline = "One or more axles are over their rated limit — see the breakdown below.",
            tone = Tone.WARNING,
            status = VerdictStatus.FAIL,
        )
        allInsufficient -> VerdictInfo(
            headline = "Not Enough Information",
            subline = "Add at least a truck tag, trailer tag, or scale ticket to check anything.",
            tone = Tone.INSUFFICIENT,
            status = VerdictStatus.INSUFFICIENT,
        )
        anyInsufficient -> VerdictInfo(
            headline = "Partially Checked",
            subline = "Some axles couldn't be checked yet — add more data for a complete picture.",
            tone = Tone.INSUFFICIENT,
            status = VerdictStatus.PARTIAL,
        )
        else -> VerdictInfo(
            headline = "Safe to Tow",
            subline = "Every axle checks out under its rated limit.",
            tone = Tone.SUCCESS,
            status = VerdictStatus.PASS,
        )
    }
}
