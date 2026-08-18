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
)
