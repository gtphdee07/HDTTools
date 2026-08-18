package com.rigcheck.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import java.time.Instant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

private const val MAX_RECENT_RIGS = 5

private val Context.rigCheckDataStore by preferencesDataStore(name = "rigcheck_prefs")
private val RECENT_RIGS_KEY = stringPreferencesKey("recent_rigs")

// Kotlin port of web/src/recentRigs.ts's exact algorithm (case-insensitive
// dedupe by nickname, prepend, slice to 5), backed by Preferences DataStore
// instead of localStorage - one serialized JSON blob, same mental model.
class RecentRigsRepository(context: Context) {
    private val dataStore = context.rigCheckDataStore
    private val json = Json { ignoreUnknownKeys = true }

    val recentRigs: Flow<List<RecentRig>> = dataStore.data.map { prefs ->
        val raw = prefs[RECENT_RIGS_KEY] ?: return@map emptyList()
        runCatching { json.decodeFromString<List<RecentRig>>(raw) }.getOrDefault(emptyList())
    }

    suspend fun saveRecentRig(nickname: String, truck: TruckTag, trailer: TrailerTag): List<RecentRig> {
        val existing = recentRigs.first().filter { it.nickname.lowercase() != nickname.lowercase() }
        val updated = RecentRig(
            nickname = nickname,
            truck = truck,
            trailer = trailer,
            lastUsedAt = Instant.now().toString(),
        )
        val next = (listOf(updated) + existing).take(MAX_RECENT_RIGS)
        dataStore.edit { prefs -> prefs[RECENT_RIGS_KEY] = json.encodeToString(next) }
        return next
    }
}
