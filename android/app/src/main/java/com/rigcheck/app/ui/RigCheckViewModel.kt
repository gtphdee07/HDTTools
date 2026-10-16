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
import com.rigcheck.app.data.ScanAttempts
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
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

private const val BILLING_NOT_LINKED = "Couldn't connect your account to purchases. Check your connection and try again."

sealed interface ScanUiState {
    data object Idle : ScanUiState
    data object Loading : ScanUiState
    data class Error(val message: String, val nextSteps: List<ScanNextStep> = emptyList()) : ScanUiState
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

    // Shared by both Scan entry points (the three documents and the stand-alone
    // ticket), so a photo's request id survives a lost answer on either.
    private val scanAttempts = ScanAttempts()

    // The Scan the user last started, so "Try again" can send its photo again.
    private val scanRetry = ScanRetry<Uri>()

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
        // The SCAN balance belongs to whichever account RevenueCat is logged
        // in as. Clear it whenever that changes (so one account's balance is
        // never shown for another) and only read it once RevenueCat is
        // linked to the signed-in account; signed out or unlinked, it stays
        // "not loaded", which also routes Scan Photo to the sign-in screen.
        viewModelScope.launch {
            accountManager.state
                .map { state -> (state as? AccountState.SignedIn)?.takeIf { it.billingLinked }?.account?.id }
                .distinctUntilChanged()
                .collect { linkedAccountId ->
                    creditBalance = null
                    if (linkedAccountId != null) refreshCreditBalance()
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

    // A purchase or restore made before RevenueCat knows the account would
    // land on the wrong customer, so both wait for the link.
    private suspend fun billingLinkedOrReport(onResult: (success: Boolean, error: String?) -> Unit): Boolean {
        val linked = accountManager.ensureBillingLinked()
        if (!linked) onResult(false, BILLING_NOT_LINKED)
        return linked
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
    // (caller should surface scanState.Error and stay put - no automatic
    // retry; the user's own retry of the same photo reuses its request id
    // after a lost answer, so the Worker charges once).
    fun performScan(
        module: EntryModule,
        contentResolver: ContentResolver,
        photoUri: Uri,
        onDone: (success: Boolean) -> Unit,
    ) {
        scanRetry.started(module, photoUri)
        scanState = ScanUiState.Loading
        viewModelScope.launch {
            val result = sendScan(module, contentResolver, photoUri)

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
                    showScanFailure(result)
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
        scanRetry.startedStandalone(photoUri)
        scanState = ScanUiState.Loading
        viewModelScope.launch {
            val result = sendScan(EntryModule.SCALE, contentResolver, photoUri)

            when (result) {
                is ScanResult.Success -> {
                    val standalone = standaloneWeightFrom(result.fields)
                    scanState = ScanUiState.Idle
                    refreshCreditBalance()
                    if (standalone != null) {
                        truck = truck.copy(standaloneWeightLb = standalone)
                        onDone(true)
                    } else {
                        scanState = NO_WEIGHT_ERROR
                        onDone(false)
                    }
                }
                is ScanResult.Failure -> {
                    showScanFailure(result)
                    onDone(false)
                }
            }
        }
    }

    private fun showScanFailure(failure: ScanResult.Failure) = reportScanFailure(
        failure,
        show = { scanState = it },
        refreshBalance = ::refreshCreditBalance,
        setBalance = { creditBalance = it },
    )

    // Sends the photo of the last Scan again, through the same entry point, for
    // the error dialog's "Try again". Does nothing if no Scan was started.
    fun retryScan(contentResolver: ContentResolver, onDone: (success: Boolean) -> Unit) {
        scanRetry.again(
            main = { module, photoUri -> performScan(module, contentResolver, photoUri, onDone) },
            standalone = { photoUri -> performStandaloneScan(contentResolver, photoUri, onDone) },
        )
    }

    // The one place a Scan request is sent, for both entry points. The Worker
    // dedupes the RevenueCat charge on the request id, so the same photo keeps
    // its id until an answer settles the attempt (see ScanAttempts): a user's
    // retry after a lost answer is then charged once.
    private suspend fun sendScan(module: EntryModule, contentResolver: ContentResolver, photoUri: Uri): ScanResult =
        runCatching {
            scanAttempts.run(module, photoUri.toString()) { clientRequestId ->
                val token = accountManager.accessToken() ?: return@run NOT_SIGNED_IN
                // A photo that cannot be opened or decoded fails before anything is sent.
                val base64 = runCatching { encodePhotoForScan(contentResolver, photoUri) }
                    .getOrElse { return@run PHOTO_UNSENDABLE }
                ScanApiClient.scan(token, module, base64, clientRequestId = clientRequestId)
            }
        }.getOrElse { ScanResult.Failure("client_error", it.message ?: "Something went wrong.") }

    fun clearScanError() {
        scanState = ScanUiState.Idle
    }

    fun purchase(activity: Activity, pkg: Package, onResult: (success: Boolean, error: String?) -> Unit) {
        viewModelScope.launch {
            if (!billingLinkedOrReport(onResult)) return@launch
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
            if (!billingLinkedOrReport(onResult)) return@launch
            runCatching { RevenueCatManager.restorePurchases() }
                .onSuccess {
                    refreshCreditBalance()
                    onResult(true, null)
                }
                .onFailure { onResult(false, it.message ?: "Restore failed.") }
        }
    }
}
