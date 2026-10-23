package com.rigcheck.app.domain.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class RecentRig(
    val nickname: String,
    val truck: TruckTag,
    val trailer: TrailerTag,
    val lastUsedAt: String,
    // Set for a Rig stored in the account's Garage; null for one kept on this phone.
    val id: String? = null,
    // What another app (Web) saved in this Rig's truck and trailer that Android has no field for, such as
    // a VIN or tire sizes. Carried through untouched so saving the Rig here does not erase it.
    val truckExtra: JsonObject = JsonObject(emptyMap()),
    val trailerExtra: JsonObject = JsonObject(emptyMap()),
)
