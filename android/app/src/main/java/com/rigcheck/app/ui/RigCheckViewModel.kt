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
import com.rigcheck.app.data.AccountManager
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.data.AccountState
import com.rigcheck.app.data.PurchaseCancelledException
import com.rigcheck.app.data.RecentRigsRepository
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.ScanApiClient
import com.rigcheck.app.data.ScanResult
import com.rigcheck.app.data.SupabaseAccountBackend
import com.rigcheck.app.data.UnavailableAccountBackend
import com.rigcheck.app.data.encodePhotoForScan
import com.rigcheck.app.data.googleFailureMessage
import com.rigcheck.app.data.mergeScanFields
import com.rigcheck.app.data.requestGoogleIdentity
import com.rigcheck.app.data.standaloneWeightFrom
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.DEFAULT_PIN_WEIGHT_PCT
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.domain.computeBreakdown
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.domain.verdictFor
import com.rigcheck.app.ui.navigation.EntryModule
import com.revenuecat.purchases.Package
import java.util.UUID
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

private const val BILLING_NOT_LINKED = "Couldn't connect your account to purchases. Check your connection and try again."
private val NOT_SIGNED_IN = ScanResult.Failure("not_signed_in", "Sign in to scan.")

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

    // Whole-number percentage (15-25, default 20), same convention as
    // Web's wizard.pinWeightPct - converted to a fraction only at the
    // computeBreakdown call site below.
    var pinWeightPct by mutableStateOf((DEFAULT_PIN_WEIGHT_PCT * 100).toInt())

    // null = not loaded yet (distinct from a real 0-credit balance).
    var creditBalance by mutableStateOf<Int?>(null)
        private set
    var scanState by mutableStateOf<ScanUiState>(ScanUiState.Idle)
        private set

    val breakdown: List<BreakdownItem>
        get() = computeBreakdown(truck, trailer, scale, pinWeightPct / 100.0)

    val verdict: VerdictInfo
        get() = verdictFor(breakdown)

    // The shared account (#22). Free manual entry never touches it; only
    // buying and scanning need a signed-in account.
    private val accountManager = AccountManager(
        backend = SupabaseAccountBackend.get() ?: UnavailableAccountBackend,
        billing = RevenueCatManager,
        scope = viewModelScope,
    )
    val accountState: StateFlow<AccountState> = accountManager.state

    init {
        refreshCreditBalance()
        // The SCAN balance belongs to whichever account RevenueCat is
        // currently logged in as, so re-read it whenever that changes.
        viewModelScope.launch {
            accountManager.state
                .map { state -> (state as? AccountState.SignedIn)?.let { it.account.id to it.billingLinked } }
                .distinctUntilChanged()
                .drop(1)
                .collect { signedIn ->
                    if (signedIn == null) creditBalance = null
                    refreshCreditBalance()
                }
        }
    }

    fun signIn(email: String, password: String, onResult: (AccountResult) -> Unit) =
        launchAccountAction(onResult) { accountManager.signIn(email, password) }

    fun signUp(email: String, password: String, onResult: (AccountResult) -> Unit) =
        launchAccountAction(onResult) { accountManager.signUp(email, password) }

    fun requestPasswordReset(email: String, onResult: (AccountResult) -> Unit) =
        launchAccountAction(onResult) { accountManager.requestPasswordReset(email) }

    fun signInWithApple(onResult: (AccountResult) -> Unit) =
        launchAccountAction(onResult) { accountManager.signInWithApple() }

    fun signInWithGoogle(activity: Activity, onResult: (AccountResult) -> Unit) =
        launchAccountAction(onResult) {
            try {
                val identity = requestGoogleIdentity(activity)
                accountManager.signInWithGoogle(identity.idToken, identity.rawNonce)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                googleFailureMessage(e)?.let { AccountResult.Failure(it) } ?: AccountResult.Cancelled
            }
        }

    fun signOut() {
        viewModelScope.launch { accountManager.signOut() }
    }

    private fun launchAccountAction(onResult: (AccountResult) -> Unit, action: suspend () -> AccountResult) {
        viewModelScope.launch { onResult(action()) }
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
        pinWeightPct = (DEFAULT_PIN_WEIGHT_PCT * 100).toInt()
    }

    fun startNewRig(nickname: String) {
        rigNickname = nickname
        truck = TruckTag()
        trailer = TrailerTag()
        scale = ScaleTicket()
        pinWeightPct = (DEFAULT_PIN_WEIGHT_PCT * 100).toInt()
    }

    fun updatePinWeightPct(value: Int) {
        pinWeightPct = value
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
            // One id per user-initiated tap - the Worker uses this to dedupe
            // the RevenueCat charge if this attempt has to be retried after
            // a lost/timed-out response. There's no existing client-side
            // retry loop, so generating it once here (not inside
            // ScanApiClient) is enough to cover "the same logical attempt."
            val clientRequestId = UUID.randomUUID().toString()
            val result = runCatching {
                val token = accountManager.accessToken() ?: return@runCatching NOT_SIGNED_IN
                val base64 = encodePhotoForScan(contentResolver, photoUri)
                ScanApiClient.scan(token, module, base64, clientRequestId = clientRequestId)
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

    // Scans a tow-vehicle-only ticket (same scale_ticket doc type/endpoint
    // as a real scale scan, no trailer attached) and maps its reading onto
    // truck.standaloneWeightLb instead of the scale - mirrors Web's
    // scanStandaloneTicket in App.tsx. Uses the same paid EntryModule.SCALE
    // pipeline as a normal scan (this is Android's only OCR path, unlike
    // Web's separate free-tier extraction endpoint), so it consumes a
    // credit like any other scan.
    fun performStandaloneScan(
        contentResolver: ContentResolver,
        photoUri: Uri,
        onDone: (success: Boolean) -> Unit,
    ) {
        scanState = ScanUiState.Loading
        viewModelScope.launch {
            val clientRequestId = UUID.randomUUID().toString()
            val result = runCatching {
                val token = accountManager.accessToken() ?: return@runCatching NOT_SIGNED_IN
                val base64 = encodePhotoForScan(contentResolver, photoUri)
                ScanApiClient.scan(token, EntryModule.SCALE, base64, clientRequestId = clientRequestId)
            }.getOrElse { ScanResult.Failure("client_error", it.message ?: "Something went wrong.") }

            when (result) {
                is ScanResult.Success -> {
                    val standalone = standaloneWeightFrom(result.fields)
                    scanState = ScanUiState.Idle
                    refreshCreditBalance()
                    if (standalone != null) {
                        truck = truck.copy(standaloneWeightLb = standalone)
                        onDone(true)
                    } else {
                        scanState = ScanUiState.Error(
                            "Couldn't find a weight on that ticket — try a clearer photo, or enter it manually.",
                        )
                        onDone(false)
                    }
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
            // A purchase made before RevenueCat knows the account would land
            // on the wrong customer, so it waits for the link.
            if (!accountManager.ensureBillingLinked()) {
                onResult(false, BILLING_NOT_LINKED)
                return@launch
            }
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
            if (!accountManager.ensureBillingLinked()) {
                onResult(false, BILLING_NOT_LINKED)
                return@launch
            }
            runCatching { RevenueCatManager.restorePurchases() }
                .onSuccess {
                    refreshCreditBalance()
                    onResult(true, null)
                }
                .onFailure { onResult(false, it.message ?: "Restore failed.") }
        }
    }
}
