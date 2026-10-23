package com.rigcheck.app.data

import com.rigcheck.app.domain.VerdictStatus
import java.time.Instant
import java.util.UUID
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

// History: a signed-in user's past checks live in the account (ADR-0005), so every device sees the same
// ones, and the server keeps only the newest few (the plan's cap), dropping the oldest. A signed-out user's
// checks last only for the app session, so the free flow is never gated. Checks made while signed out are not
// carried into the account: they were never saved anywhere, and signing in switches to the account's own list
// (signing out switches back). Mirrors web/src/history.tsx.

// One past check. `checkedAt` is an ISO instant; the screen shows it as a date.
data class HistoryEntry(val id: String, val checkedAt: String, val rigNickname: String, val verdict: VerdictStatus)

// How many checks each plan keeps, as the server counts them.
data class HistoryCaps(val free: Int, val pro: Int)

// Used when the Supabase client can't be built, so no one can be signed in; nothing is read or saved.
object UnavailableHistoryBackend : HistoryBackend {
    override suspend fun list(): List<HistoryEntry> = emptyList()
    override suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?) =
        throw IllegalStateException("Accounts are not available right now.")
    override suspend fun caps(): HistoryCaps = throw IllegalStateException("Accounts are not available right now.")
}

// The account's History store. Kept narrow so tests can fake it (the real one is SupabaseHistoryBackend).
interface HistoryBackend {
    // The account's checks, newest first.
    suspend fun list(): List<HistoryEntry>

    // Adds a check; the server drops the oldest past the cap, which `isPro` (null when the plan could not be
    // read) picks. The same key sent twice creates one entry.
    suspend fun addEntry(idempotencyKey: String, rigNickname: String, verdict: VerdictStatus, isPro: Boolean?)

    // How many checks each plan keeps.
    suspend fun caps(): HistoryCaps
}

class History(
    accountState: Flow<AccountState>,
    private val backend: HistoryBackend,
    // The plan the account's saves report to the database, which picks the cap from it: true Pro, false Free,
    // null not known (the database then keeps the Pro count: pruning a Pro account to the Free count cannot
    // be undone).
    private val isPro: () -> Boolean?,
    private val scope: CoroutineScope,
    private val newKey: () -> String = { UUID.randomUUID().toString() },
    private val now: () -> String = { Instant.now().toString() },
) {
    private val _entries = MutableStateFlow<List<HistoryEntry>>(emptyList())
    val entries: StateFlow<List<HistoryEntry>> = _entries

    // How many checks each plan keeps; null while signed out or until the account's caps have been read (a
    // failed read leaves it null, and the History screen then says nothing about the cap).
    private val _caps = MutableStateFlow<HistoryCaps?>(null)
    val caps: StateFlow<HistoryCaps?> = _caps

    // The signed-in account the History is showing, null when it is showing this session's own checks.
    private var accountId: String? = null

    // This session's checks, shown while nobody is signed in.
    private var visitEntries = emptyList<HistoryEntry>()

    // Numbers each read so an older one answering late cannot overwrite a newer list.
    private var latestLoad = 0

    init {
        scope.launch {
            accountState
                .map { state -> (state as? AccountState.SignedIn)?.account?.id }
                .distinctUntilChanged()
                .collectLatest { id ->
                    accountId = id
                    _caps.value = null
                    if (id == null) {
                        _entries.value = visitEntries
                    } else {
                        _entries.value = emptyList()
                        coroutineScope {
                            launch { readCaps(id) }
                            load()
                        }
                    }
                }
        }
    }

    // Reads the account's checks again, to pick up checks made on another device. Does nothing signed out.
    fun refresh() {
        scope.launch { load() }
    }

    // The caps only change when the owner edits them, so they are read once per account.
    private suspend fun readCaps(forAccount: String) {
        val read = try {
            backend.caps()
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            return
        }
        if (accountId == forAccount) _caps.value = read
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
        if (accountId == forAccount && latestLoad == thisLoad) _entries.value = fetched
    }

    // Records a finished check. False if the account could not save it; the check is still a result.
    suspend fun recordCheck(rigNickname: String, verdict: VerdictStatus): Boolean {
        val nickname = rigNickname.trim()
        if (accountId == null) {
            visitEntries = listOf(HistoryEntry(newKey(), now(), nickname, verdict)) + visitEntries
            _entries.value = visitEntries
            return true
        }
        try {
            addWithOneRetry(nickname, verdict)
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            return false
        }
        load()
        return true
    }

    // One key per check, reused on the retry, so a request that did land but whose reply was lost is
    // recognised by the server instead of recorded twice.
    private suspend fun addWithOneRetry(rigNickname: String, verdict: VerdictStatus) {
        val key = newKey()
        val pro = isPro()
        try {
            backend.addEntry(key, rigNickname, verdict, pro)
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            backend.addEntry(key, rigNickname, verdict, pro)
        }
    }
}
