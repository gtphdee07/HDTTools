package com.rigcheck.app.ui

import com.rigcheck.app.data.SaveRigOutcome

// What a check that could not save its Rig to the Garage tells the user (mirrors web/src/App.tsx
// garageNoticeFor and web/src/plan.ts garageFullText). The check itself is never affected. `offerPro` marks a
// full Garage that Pro would make room in.
data class GarageNotice(val message: String, val offerPro: Boolean)

fun garageNoticeFor(nickname: String, outcome: SaveRigOutcome, isPro: Boolean?): GarageNotice? = when (outcome) {
    SaveRigOutcome.Saved -> null
    is SaveRigOutcome.Full -> GarageNotice(
        message = "Your Garage ${garageFullText(outcome.cap, isPro)}, so \"$nickname\" wasn't saved to it. " +
            "Your check is not affected.",
        offerPro = isPro == false,
    )
    SaveRigOutcome.Failed -> GarageNotice(
        message = "We couldn't save \"$nickname\" to your Garage. Your check is not affected.",
        offerPro = false,
    )
}

// How a full Garage is described: "is full (the Free plan holds 5 Rigs)". The cap is the one the database
// named, so it is never written here; whose it is depends on the plan the save reported.
internal fun garageFullText(cap: Int?, isPro: Boolean?): String {
    if (cap == null) return "is full"
    val rigs = "$cap Rig${if (cap == 1) "" else "s"}"
    return when (isPro) {
        false -> "is full (the Free plan holds $rigs)"
        true -> "is full (Pro holds $rigs)"
        null -> "is full ($rigs, which may be the Free limit because we couldn't check your plan)"
    }
}
