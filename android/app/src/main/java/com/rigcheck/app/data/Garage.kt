package com.rigcheck.app.data

import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import java.time.Instant
import java.util.UUID
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

// The Garage: the signed-in account's saved Rigs live in the account (ADR-0005), so every device sees the
// same ones and the server enforces the plan's cap. Signed out, the Garage is the Rigs kept on this phone,
// so the free flow is never gated. Mirrors web/src/garage.tsx.

class GarageFullException(val cap: Int?) : Exception("garage_full")

// Used when the Supabase client can't be built, so no one can be signed in; nothing is read or saved.
object UnavailableGarageBackend : GarageBackend {
    override suspend fun list(): List<RecentRig> = emptyList()
    override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) =
        throw IllegalStateException("Accounts are not available right now.")
    override suspend fun updateRig(rig: RecentRig) = throw IllegalStateException("Accounts are not available right now.")
}

sealed interface SaveRigOutcome {
    data object Saved : SaveRigOutcome

    // The Garage has no room; `cap` is the number the server named, null if it did not.
    data class Full(val cap: Int?) : SaveRigOutcome
    data object Failed : SaveRigOutcome
}

// The account's Garage store. Kept narrow so tests can fake it (the real one is SupabaseGarageBackend).
interface GarageBackend {
    // The account's Rigs, most recently used first.
    suspend fun list(): List<RecentRig>

    // Adds a Rig. Throws GarageFullException at the cap, which `isPro` (null when the plan could not be
    // read) picks. The same key sent twice creates one Rig.
    suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?)

    // Rewrites an existing Rig (its tags and last-used time). Uses no capacity.
    suspend fun updateRig(rig: RecentRig)
}

// The Rigs kept on this phone (RecentRigsRepository), for when nobody is signed in.
interface LocalRigs {
    val recentRigs: Flow<List<RecentRig>>
    suspend fun saveRecentRig(nickname: String, truck: TruckTag, trailer: TrailerTag): List<RecentRig>
}

// The one rule for telling Rigs apart by nickname: ignore case and surrounding spaces, as the Garage's own
// unique index and add_rig do (web/src/nickname.ts).
private fun nicknameKey(nickname: String) = nickname.trim().lowercase()

class Garage(
    accountState: Flow<AccountState>,
    private val backend: GarageBackend,
    private val local: LocalRigs,
    // The plan the account's saves report to the database, which picks the cap from it: true Pro, false Free,
    // null not known. Not known gets the Free cap, so a failed read is no free upgrade.
    private val isPro: () -> Boolean?,
    private val scope: CoroutineScope,
    private val newKey: () -> String = { UUID.randomUUID().toString() },
    private val now: () -> String = { Instant.now().toString() },
) {
    private val _rigs = MutableStateFlow<List<RecentRig>>(emptyList())
    val rigs: StateFlow<List<RecentRig>> = _rigs

    // The signed-in account the Garage is showing, null when it is showing this phone's Rigs.
    private var accountId: String? = null

    // Numbers each read so an older one answering late cannot overwrite a newer list.
    private var latestLoad = 0

    init {
        scope.launch {
            accountState
                .map { state -> (state as? AccountState.SignedIn)?.account?.id }
                .distinctUntilChanged()
                .collectLatest { id ->
                    accountId = id
                    _rigs.value = emptyList()
                    if (id == null) local.recentRigs.collect { _rigs.value = it } else load()
                }
        }
    }

    // Reads the account's Rigs again, to pick up changes made on another device. Does nothing signed out.
    fun refresh() {
        scope.launch { load() }
    }

    private suspend fun load() {
        val forAccount = accountId ?: return
        val thisLoad = ++latestLoad
        val fetched = try {
            backend.list()
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            return // keep what is shown; the next refresh tries again
        }
        // A reply that lands after a sign-out or an account switch, or after a newer read, is dropped.
        if (accountId == forAccount && latestLoad == thisLoad) _rigs.value = fetched
    }

    suspend fun saveRig(nickname: String, truck: TruckTag, trailer: TrailerTag): SaveRigOutcome {
        if (accountId == null) {
            local.saveRecentRig(nickname, truck, trailer)
            return SaveRigOutcome.Saved
        }
        try {
            val existing = _rigs.value.firstOrNull { it.id != null && nicknameKey(it.nickname) == nicknameKey(nickname) }
            val updated = existing != null && tryUpdate(existing.copy(truck = truck, trailer = trailer, lastUsedAt = now()))
            if (!updated) {
                addWithOneRetry(RecentRig(nickname = nickname, truck = truck, trailer = trailer, lastUsedAt = now()))
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: GarageFullException) {
            return SaveRigOutcome.Full(e.cap)
        } catch (_: Exception) {
            return SaveRigOutcome.Failed
        }
        load()
        return SaveRigOutcome.Saved
    }

    // False if the update failed. The Rig may have been removed on another device since the list was read;
    // the caller then adds it, which refreshes a Rig of that name if one is still there.
    private suspend fun tryUpdate(rig: RecentRig): Boolean = try {
        backend.updateRig(rig)
        true
    } catch (e: CancellationException) {
        throw e
    } catch (_: Exception) {
        false
    }

    // One key per save, reused on the retry, so a request that did land but whose reply was lost is
    // recognised by the server instead of counted twice. A full Garage is an answer, not a failure, so it
    // is not retried.
    private suspend fun addWithOneRetry(rig: RecentRig) {
        val key = newKey()
        val pro = isPro()
        try {
            backend.addRig(key, rig, pro)
        } catch (e: CancellationException) {
            throw e
        } catch (e: GarageFullException) {
            throw e
        } catch (_: Exception) {
            backend.addRig(key, rig, pro)
        }
    }
}
