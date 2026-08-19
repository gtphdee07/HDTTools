package com.rigcheck.app.ui

import android.app.Activity
import android.app.Application
import android.content.ContentResolver
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rigcheck.app.data.PurchaseCancelledException
import com.rigcheck.app.data.RecentRigsRepository
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.ScanApiClient
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.data.encodePhotoForScan
import com.rigcheck.app.data.mergeScanFields
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.domain.computeBreakdown
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.domain.verdictFor
import com.rigcheck.app.ui.navigation.EntryModule
import com.revenuecat.purchases.Package
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

sealed interface ScanUiState {
    data object Idle : ScanUiState
    data object Loading : ScanUiState
    data class Error(val message: String) : ScanUiState
}

// Nav-graph-scoped: one instance shared across every screen so the
// in-progress truck/trailer/scale data survives navigating back and forth.
// disclaimerAcknowledged is deliberately never persisted - session/process-
// scoped only, per ANDROID_DESIGN_BRIEF.md ("shown once per app session").
class RigCheckViewModel(application: Application) : AndroidViewModel(application) {
    private val recentRigsRepository = RecentRigsRepository(application)

    val recentRigs: StateFlow<List<RecentRig>> = recentRigsRepository.recentRigs
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    var rigNickname by mutableStateOf("")
        private set
    var truck by mutableStateOf(TruckTag())
    var trailer by mutableStateOf(TrailerTag())
    var scale by mutableStateOf(ScaleTicket())
    var disclaimerAcknowledged by mutableStateOf(false)
        private set

    // null = not loaded yet (distinct from a real 0-credit balance).
    var creditBalance by mutableStateOf<Int?>(null)
        private set
    var scanState by mutableStateOf<ScanUiState>(ScanUiState.Idle)
        private set

    val breakdown: List<BreakdownItem>
        get() = computeBreakdown(truck, trailer, scale)

    val verdict: VerdictInfo
        get() = verdictFor(breakdown)

    init {
        refreshCreditBalance()
    }

    fun refreshCreditBalance() {
        viewModelScope.launch {
            runCatching { RevenueCatManager.getScanCreditBalance() }
                .onSuccess { creditBalance = it }
        }
    }

    fun selectRecentRig(rig: RecentRig) {
        rigNickname = rig.nickname
        truck = rig.truck
        trailer = rig.trailer
        scale = ScaleTicket()
    }

    fun startNewRig(nickname: String) {
        rigNickname = nickname
        truck = TruckTag()
        trailer = TrailerTag()
        scale = ScaleTicket()
    }

    fun acknowledgeDisclaimer() {
        disclaimerAcknowledged = true
    }

    fun saveCurrentRig() {
        viewModelScope.launch { recentRigsRepository.saveRecentRig(rigNickname, truck, trailer) }
    }

    // On success, merges the extracted fields onto the current module's
    // state and refreshes the credit balance (the Worker already charged
    // it server-side). onDone is called with true on success (caller
    // should navigate to the entry screen for review) or false on failure
    // (caller should surface scanState.Error and stay put - no client-side
    // retry, matching the Worker's own charge/refund discipline).
    fun performScan(
        module: EntryModule,
        contentResolver: ContentResolver,
        photoUri: Uri,
        onDone: (success: Boolean) -> Unit,
    ) {
        scanState = ScanUiState.Loading
        viewModelScope.launch {
            val result = runCatching {
                val base64 = encodePhotoForScan(contentResolver, photoUri)
                ScanApiClient.scan(RevenueCatManager.appUserId, module, base64)
            }.getOrElse { ScanResult.Failure("client_error", it.message ?: "Something went wrong.") }

            when (result) {
                is ScanResult.Success -> {
                    when (module) {
                        EntryModule.TRUCK -> truck = truck.mergeScanFields(result.fields)
                        EntryModule.TRAILER -> trailer = trailer.mergeScanFields(result.fields)
                        EntryModule.SCALE -> scale = scale.mergeScanFields(result.fields)
                    }
                    scanState = ScanUiState.Idle
                    refreshCreditBalance()
                    onDone(true)
                }
                is ScanResult.Failure -> {
                    scanState = ScanUiState.Error(result.message)
                    if (result.code != "insufficient_credits") refreshCreditBalance()
                    onDone(false)
                }
            }
        }
    }

    fun clearScanError() {
        scanState = ScanUiState.Idle
    }

    fun purchase(activity: Activity, pkg: Package, onResult: (success: Boolean, error: String?) -> Unit) {
        viewModelScope.launch {
            runCatching { RevenueCatManager.purchasePackage(activity, pkg) }
                .onSuccess {
                    refreshCreditBalance()
                    onResult(true, null)
                }
                .onFailure { error ->
                    if (error is PurchaseCancelledException) {
                        onResult(false, null)
                    } else {
                        onResult(false, error.message ?: "Purchase failed.")
                    }
                }
        }
    }

    fun restorePurchases(onResult: (success: Boolean, error: String?) -> Unit) {
        viewModelScope.launch {
            runCatching { RevenueCatManager.restorePurchases() }
                .onSuccess {
                    refreshCreditBalance()
                    onResult(true, null)
                }
                .onFailure { onResult(false, it.message ?: "Restore failed.") }
        }
    }
}
