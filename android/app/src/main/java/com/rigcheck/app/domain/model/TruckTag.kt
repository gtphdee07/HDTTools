package com.rigcheck.app.domain.model

import kotlinx.serialization.Serializable

@Serializable
data class TruckTag(
    val description: String? = null,
    val name: String? = null,
    val gvwrLb: Double? = null,
    val frontGawrLb: Double? = null,
    val rearGawrLb: Double? = null,
    val standaloneWeightLb: Double? = null,
    // Typed by hand from the owner's manual; a Scan never returns it. A Rig
    // saved before this field existed decodes it as null (no Combined row).
    val gcwrLb: Double? = null,
)
