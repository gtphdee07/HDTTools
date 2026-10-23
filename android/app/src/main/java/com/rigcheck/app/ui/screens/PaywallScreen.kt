package com.rigcheck.app.ui.screens

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.revenuecat.purchases.Package
import com.rigcheck.app.data.PaywallOffers
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.paywallOffers

// Custom Compose layout per ANDROID_DESIGN_BRIEF.md - not RevenueCat's
// prebuilt Paywall UI, since the mockup is bespoke/brand-matched. Prices
// always come from StoreProduct.price.formatted (Test Store while
// testing), never hardcoded.
//
// Scan packs are sold to Pro accounts only (ADR-0006's 2026-10-12 amendment): a
// Free account is offered Pro and no packs, a Pro account the packs and not Pro.
// Buying Pro here does not close the screen; the plan is read again, and the packs
// replace the Pro offer.
@Composable
fun PaywallScreen(
    creditBalance: Int?,
    onPurchase: (Package, (success: Boolean, error: String?) -> Unit) -> Unit,
    onRestore: ((success: Boolean, error: String?) -> Unit) -> Unit,
    onDone: () -> Unit,
    // The signed-in account the purchase will be made for (its email, else
    // its id) - purchases land on this account across every device.
    accountLabel: String? = null,
    onSignOut: () -> Unit = {},
    // The account's plan, Pro however it was bought (Web included); null = not known yet,
    // which shows nothing rather than Free, and offers nothing to buy until it is known.
    isPro: Boolean? = null,
    // Reads the plan again, for when it could not be read.
    onRetryPlan: () -> Unit = {},
    // The current Offering's packages; a seam so tests can fake RevenueCat.
    loadPackages: suspend () -> List<Package> = {
        RevenueCatManager.getOfferings().current?.availablePackages.orEmpty()
    },
) {
    val context = LocalContext.current
    var offers by remember { mutableStateOf<PaywallOffers?>(null) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var isBusy by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        runCatching { loadPackages() }
            .onSuccess { offers = paywallOffers(it) }
            .onFailure { loadError = it.message ?: "Could not load offers." }
    }

    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        Text(if (isPro == false) "Unlock Pro" else "Get More Scans", style = MaterialTheme.typography.headlineMedium)
        accountLabel?.let { label ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Buying for $label", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                TextButton(enabled = !isBusy, onClick = onSignOut) { Text("Sign out") }
            }
        }
        isPro?.let { pro ->
            Text(
                if (pro) "Pro plan" else "Free plan",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
        val scansLeft = "You have ${creditBalance ?: 0} scan${if (creditBalance == 1) "" else "s"} left. "
        val whatItIsFor = "Claude reads your truck tag, trailer tag, or scale ticket for you."
        Text(
            scansLeft + when (isPro) {
                false -> "Pro is a one-time purchase, yours to keep, and comes with a starter bundle of scans. "
                true -> "Buy more scans any time. "
                null -> ""
            } + whatItIsFor,
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp),
        )

        // Buying a pack ends the visit; buying Pro stays, because what the account
        // can buy has just changed.
        fun buy(pkg: Package, closesScreen: Boolean, done: String) {
            isBusy = true
            onPurchase(pkg) { success, error ->
                isBusy = false
                if (success) {
                    Toast.makeText(context, done, Toast.LENGTH_SHORT).show()
                    if (closesScreen) onDone()
                } else if (error != null) {
                    Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                }
            }
        }

        val shown = offers
        when {
            loadError != null -> Text(
                "Couldn't load offers: $loadError",
                color = MaterialTheme.colorScheme.error,
            )
            shown == null -> CircularProgressIndicator()
            isPro == null -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Checking your plan before showing what you can buy.")
                TextButton(enabled = !isBusy, onClick = onRetryPlan) { Text("Try again") }
            }
            isPro -> if (shown.scanPacks.isEmpty()) {
                Text("No scan packs are available right now.")
            } else {
                OfferList(shown.scanPacks, isBusy) { pkg -> buy(pkg, closesScreen = true, done = "Purchase complete!") }
            }
            else -> shown.proUnlock?.let { pro ->
                OfferList(listOf(pro), isBusy) { buy(it, closesScreen = false, done = "Pro unlocked!") }
            } ?: Text("Pro isn't available to buy right now.")
        }

        Spacer(modifier = Modifier.weight(1f))

        TextButton(
            enabled = !isBusy,
            onClick = {
                isBusy = true
                onRestore { success, error ->
                    isBusy = false
                    if (success) {
                        Toast.makeText(context, "Purchases restored.", Toast.LENGTH_SHORT).show()
                    } else if (error != null) {
                        Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                    }
                }
            },
        ) {
            Text("Restore purchase")
        }
    }
}

@Composable
private fun OfferList(packages: List<Package>, isBusy: Boolean, onBuy: (Package) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        packages.forEach { pkg ->
            Surface(
                shape = MaterialTheme.shapes.medium,
                tonalElevation = 1.dp,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(pkg.product.title, style = MaterialTheme.typography.titleMedium)
                        pkg.product.description.takeIf { it.isNotBlank() }?.let {
                            Text(it, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                    Button(enabled = !isBusy, onClick = { onBuy(pkg) }) {
                        Text(pkg.product.price.formatted)
                    }
                }
            }
        }
    }
}
