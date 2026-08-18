package com.rigcheck.app.domain.model

import kotlinx.serialization.Serializable

@Serializable
data class TrailerTag(
    val description: String? = null,
    val name: String? = null,
    val gvwrLb: Double? = null,
    val gawrPerAxleLb: Double? = null,
    val axleCount: Int? = null,
    val uvwLb: Double? = null,
)
