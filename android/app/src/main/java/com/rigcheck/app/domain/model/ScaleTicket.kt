package com.rigcheck.app.domain.model

data class ScaleTicket(
    val locationName: String? = null,
    val steerAxleLb: Double? = null,
    val driveAxleLb: Double? = null,
    val trailerAxleLb: Double? = null,
    val grossWeightLb: Double? = null,
)
