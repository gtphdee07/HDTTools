package com.rigcheck.app.data

import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

// The slice of RevenueCat that says whether the customer RevenueCat is logged
// in as owns Pro, however and wherever it was bought.
interface PlanSource {
    suspend fun isPro(): Boolean
}

// Whether the signed-in account is Pro: true, false, or null when that is not
// known (signed out, RevenueCat not yet linked to the account, or the read has
// not succeeded). Unknown is never shown as Free. The plan is read only once
// RevenueCat is linked to the account, since before that it would answer for
// whichever customer RevenueCat held last, and an answer is applied only if the
// account it was asked for is still the signed-in one.
class AccountPlan(
    accountState: Flow<AccountState>,
    private val source: PlanSource,
    private val scope: CoroutineScope,
) {
    private val _isPro = MutableStateFlow<Boolean?>(null)
    val isPro: StateFlow<Boolean?> = _isPro

    private var linkedAccountId: String? = null

    init {
        scope.launch {
            accountState
                .map { state -> (state as? AccountState.SignedIn)?.takeIf { it.billingLinked }?.account?.id }
                .distinctUntilChanged()
                .collectLatest { accountId ->
                    linkedAccountId = accountId
                    _isPro.value = null
                    if (accountId != null) read(accountId)
                }
        }
    }

    // Reads the plan again, for after a purchase or restore, or when the user
    // looks at it. Does nothing while no account is linked.
    fun refresh() {
        val accountId = linkedAccountId ?: return
        scope.launch { read(accountId) }
    }

    private suspend fun read(accountId: String) {
        val pro = try {
            source.isPro()
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            return
        }
        if (linkedAccountId == accountId) _isPro.value = pro
    }
}
