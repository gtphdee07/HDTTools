package com.rigcheck.app.domain.model

import kotlinx.serialization.Serializable

@Serializable
data class RecentRig(
    val nickname: String,
    val truck: TruckTag,
    val trailer: TrailerTag,
    val lastUsedAt: String,
)
