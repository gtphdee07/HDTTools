package com.rigcheck.app.data

import com.rigcheck.app.domain.model.RecentRig
import io.github.jan.supabase.SupabaseClient
import io.github.jan.supabase.postgrest.exception.PostgrestRestException
import io.github.jan.supabase.postgrest.from
import io.github.jan.supabase.postgrest.postgrest
import io.github.jan.supabase.postgrest.query.Columns
import io.github.jan.supabase.postgrest.query.Order
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject

// The account's Garage over the `garage_rigs` table and `add_rig` function from
// supabase/migrations/20261010000000_garage_rigs.sql (cap by plan: 20261023000000_plan_caps.sql). Row-level
// security scopes every call to the signed-in account; the cap and the idempotency live in add_rig, not
// here. Mirrors web/src/supabaseGarage.ts. The shape of a Rig's truck and trailer is GarageWire.kt's.

@Serializable
private class GarageRow(
    val id: String,
    val nickname: String,
    val truck: JsonObject,
    val trailer: JsonObject,
    @SerialName("last_used_at") val lastUsedAt: String,
)

@Serializable
private class IdRow(val id: String)

class SupabaseGarageBackend(private val client: SupabaseClient) : GarageBackend {

    override suspend fun list(): List<RecentRig> =
        client.postgrest.from("garage_rigs")
            .select(Columns.list("id", "nickname", "truck", "trailer", "last_used_at")) {
                order("last_used_at", Order.DESCENDING)
            }
            .decodeList<GarageRow>()
            .map { rigFromGarageRow(it.id, it.nickname, it.truck, it.trailer, it.lastUsedAt) }

    override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) {
        try {
            client.postgrest.rpc(
                "add_rig",
                buildJsonObject {
                    put("p_idempotency_key", JsonPrimitive(idempotencyKey))
                    put("p_nickname", JsonPrimitive(rig.nickname.trim()))
                    put("p_truck", garageTruckJson(rig))
                    put("p_trailer", garageTrailerJson(rig))
                    put("p_pro", isPro?.let { JsonPrimitive(it) } ?: JsonNull)
                },
            )
        } catch (e: PostgrestRestException) {
            throw garageFailureFor(e.error, (e.details as? JsonPrimitive)?.content)
        }
    }

    override suspend fun updateRig(rig: RecentRig) {
        val id = rig.id ?: throw IllegalArgumentException("rig_not_found")
        val updated = client.postgrest.from("garage_rigs")
            .update(
                {
                    set("truck", garageTruckJson(rig))
                    set("trailer", garageTrailerJson(rig))
                    set("last_used_at", rig.lastUsedAt)
                },
            ) {
                select(Columns.list("id"))
                filter { eq("id", id) }
            }
            .decodeList<IdRow>()
        if (updated.isEmpty()) throw IllegalStateException("rig_not_found")
    }
}
