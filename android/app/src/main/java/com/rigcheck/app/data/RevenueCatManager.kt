package com.rigcheck.app.data

import android.app.Activity
import com.revenuecat.purchases.CustomerInfo
import com.revenuecat.purchases.Offerings
import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PurchaseParams
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.awaitGetVirtualCurrencies
import com.revenuecat.purchases.interfaces.PurchaseCallback
import com.revenuecat.purchases.interfaces.ReceiveCustomerInfoCallback
import com.revenuecat.purchases.interfaces.ReceiveOfferingsCallback
import com.revenuecat.purchases.models.StoreTransaction
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.suspendCancellableCoroutine

// The "SCAN" virtual currency code, matching wrangler.toml's
// REVENUECAT_CURRENCY_CODE and src/revenuecat.ts server-side.
private const val SCAN_CURRENCY_CODE = "SCAN"

class PurchaseCancelledException : Exception("Purchase was cancelled by the user")

// Thin wrapper around the RevenueCat SDK's callback-based APIs, exposing
// suspend functions instead - keeps RigCheckViewModel from calling the
// SDK directly, mirroring the injectable-dependency pattern already used
// server-side (workers/scan-proxy/src/scan.ts's spendCredit/refundCredit).
object RevenueCatManager {

    // The Worker deducts/refunds credits via a direct server-side RevenueCat
    // REST call, not through this SDK's own purchase flow - so the SDK's
    // virtual-currency cache never sees an invalidation signal for that and
    // would otherwise keep serving a stale balance. Force a fresh fetch
    // every time this is called (on launch and after every scan attempt).
    suspend fun getScanCreditBalance(): Int {
        Purchases.sharedInstance.invalidateVirtualCurrenciesCache()
        val virtualCurrencies = Purchases.sharedInstance.awaitGetVirtualCurrencies()
        return virtualCurrencies.get(SCAN_CURRENCY_CODE)?.balance ?: 0
    }

    suspend fun getOfferings(): Offerings = suspendCancellableCoroutine { continuation ->
        Purchases.sharedInstance.getOfferings(object : ReceiveOfferingsCallback {
            override fun onReceived(offerings: Offerings) {
                continuation.resume(offerings)
            }

            override fun onError(error: com.revenuecat.purchases.PurchasesError) {
                continuation.resumeWithException(Exception(error.message))
            }
        })
    }

    suspend fun purchasePackage(activity: Activity, pkg: Package): StoreTransaction =
        suspendCancellableCoroutine { continuation ->
            val purchaseParams = PurchaseParams.Builder(activity, pkg).build()
            Purchases.sharedInstance.purchase(
                purchaseParams,
                object : PurchaseCallback {
                    override fun onCompleted(storeTransaction: StoreTransaction, customerInfo: CustomerInfo) {
                        continuation.resume(storeTransaction)
                    }

                    override fun onError(error: com.revenuecat.purchases.PurchasesError, userCancelled: Boolean) {
                        if (userCancelled) {
                            continuation.resumeWithException(PurchaseCancelledException())
                        } else {
                            continuation.resumeWithException(Exception(error.message))
                        }
                    }
                },
            )
        }

    suspend fun restorePurchases(): CustomerInfo = suspendCancellableCoroutine { continuation ->
        Purchases.sharedInstance.restorePurchases(object : ReceiveCustomerInfoCallback {
            override fun onReceived(customerInfo: CustomerInfo) {
                continuation.resume(customerInfo)
            }

            override fun onError(error: com.revenuecat.purchases.PurchasesError) {
                continuation.resumeWithException(Exception(error.message))
            }
        })
    }

    val appUserId: String
        get() = Purchases.sharedInstance.appUserID
}
