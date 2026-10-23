package com.rigcheck.app.data

import com.rigcheck.app.domain.VerdictStatus
import io.github.jan.supabase.SupabaseClient
import io.github.jan.supabase.postgrest.from
import io.github.jan.supabase.postgrest.postgrest
import io.github.jan.supabase.postgrest.query.Columns
import io.github.jan.supabase.postgrest.query.Order
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject

// The account's History over the `history_entries` table and `add_history_entry` function from
// supabase/migrations/20261022000000_history_entries.sql (cap by plan: 20261023000000_plan_caps.sql).
// Row-level security scopes every call to the signed-in account; the cap and the idempotency live in
// add_history_entry, not here. Mirrors web/src/supabaseHistory.ts. How a verdict is stored is HistoryWire.kt's.

@Serializable
private class HistoryRow(
    val id: String,
    @SerialName("rig_nickname") val rigNickname: String,
    val verdict: String,
    @SerialName("checked_at") val checkedAt: String,
)

@Serializable
private class PlanCapsRow(
    val plan: String,
    @SerialName("history_cap") val historyCap: Int,
)

class SupabaseHistoryBackend(private val client: SupabaseClient) : HistoryBackend {

    override suspend fun list(): List<HistoryEntry> =
        client.postgrest.from("history_entries")
            .select(Columns.list("id", "rig_nickname", "verdict", "checked_at")) {
                // Insertion order, not the timestamp: the timestamp is only what the entry's date shows.
                order("seq", Order.DESCENDING)
            }
            .decodeList<HistoryRow>()
            .mapNotNull { historyEntryFromRow(it.id, it.rigNickname, it.verdict, it.checkedAt) }

    override suspend fun caps(): HistoryCaps {
        val rows = client.postgrest.from("plan_caps")
            .select(Columns.list("plan", "history_cap"))
            .decodeList<PlanCapsRow>()
        val free = rows.firstOrNull { it.plan == "free" }?.historyCap
        val pro = rows.firstOrNull { it.plan == "pro" }?.historyCap
        if (free == null || pro == null) throw IllegalStateException("plan_caps_missing")
        return HistoryCaps(free, pro)
    }

    override suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?) {
        client.postgrest.rpc(
            "add_history_entry",
            buildJsonObject {
                put("p_idempotency_key", JsonPrimitive(idempotencyKey))
                put("p_rig_nickname", JsonPrimitive(rigNickname.trim()))
                put("p_verdict", JsonPrimitive(verdictToWire(verdict)))
                put("p_pro", isPro?.let { JsonPrimitive(it) } ?: JsonNull)
            },
        )
    }
}
