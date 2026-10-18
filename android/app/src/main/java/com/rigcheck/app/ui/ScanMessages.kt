package com.rigcheck.app.ui

// What the user is told when a Scan does not deliver, in one place. Each
// message says whether a Scan Credit was used, whether it was refunded, whether
// a retry costs another, and the next step. The words are the ones approved in
// docs/research/scan-failure-handling.md (R2); where that table gives none, the
// phrasing follows Web's (web/src/api.ts).
internal object ScanMessages {
    const val OUT_OF_SCANS =
        "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself."
    const val EXPIRED_SIGN_IN = "Your sign-in has expired. Nothing was used. Sign in again to scan."
    const val NOT_SIGNED_IN = "Sign in to scan. Nothing was used."
    const val AUTH_UNAVAILABLE =
        "We couldn't verify your account just now. Nothing was used. Try again in a moment."
    const val EXTRACTION_FAILED =
        "We couldn't read that photo, and your Scan Credit was refunded. Trying again uses another Scan. " +
            "A clearer photo may work better, or type the numbers in yourself."
    const val EXTRACTION_FAILED_NO_REFUND =
        "We couldn't read that photo, and couldn't refund your Scan Credit automatically. " +
            "Trying this photo again won't charge you again. If it keeps happening, contact support."
    const val BILLING_ERROR =
        "We couldn't confirm your Scan balance, so nothing was read. You may not have been charged. " +
            "Try again in a moment; a retry is not charged twice."
    const val BAD_REQUEST =
        "We couldn't use that photo. Try a different photo, or type the numbers in yourself. Nothing was used."
    const val PHOTO_UNSENDABLE =
        "We couldn't open that photo. Try a different photo, or type the numbers in yourself. Nothing was used."
    const val NO_CONNECTION =
        "We couldn't reach the scan service. You may not have been charged. " +
            "Check your connection and try again; a retry is not charged twice."
    const val NO_ANSWER =
        "We didn't get a usable answer from the scan service. You may not have been charged. " +
            "Try again; a retry is not charged twice."
    const val TOO_SLOW =
        "The scan service took too long to answer. You may not have been charged. " +
            "Try again; a retry is not charged twice."

    // A stand-alone ticket that came back with no weight: the Scan was
    // delivered, so it was charged and is not refunded.
    const val NO_WEIGHT =
        "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. " +
            "Type the weight in, or choose a different photo."

    // A Scan that was delivered but read nothing, or only some of the fields, on
    // the entry screen it leads to. The Scan was charged, so the user is told one
    // was used; it is a notice, not a failure, and offers no Try again (#120).
    const val NOTHING_READ =
        "A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo."

    fun someNotRead(labels: List<String>): String {
        val names = if (labels.size < 2) labels.joinToString() else labels.dropLast(1).joinToString() + " and " + labels.last()
        val them = if (labels.size == 1) "it" else "them"
        return "A Scan was used, but we couldn't read: $names. Type $them in, or go back and choose a different photo."
    }

    // Any code this app has no wording for: nothing is claimed about the charge,
    // and no retry is offered, since a retry of an unknown outcome could be charged twice.
    const val UNKNOWN =
        "Something went wrong with that Scan, and we can't tell whether a Scan Credit was used. " +
            "Check your Scan balance before you try again."
}
