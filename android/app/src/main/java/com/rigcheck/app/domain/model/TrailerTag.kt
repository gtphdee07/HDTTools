package com.rigcheck.app.domain.model

data class TrailerTag(
    val manufacturer: String? = null,
    val gvwrLb: Double? = null,
    val gawrPerAxleLb: Double? = null,
    val axleCount: Int? = null,
    val uvwLb: Double? = null,
)
