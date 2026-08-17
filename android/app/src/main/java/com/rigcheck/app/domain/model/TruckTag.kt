package com.rigcheck.app.domain.model

data class TruckTag(
    val manufacturer: String? = null,
    val gvwrLb: Double? = null,
    val frontGawrLb: Double? = null,
    val rearGawrLb: Double? = null,
    val standaloneWeightLb: Double? = null,
)
