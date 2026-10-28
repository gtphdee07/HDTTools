package com.rigcheck.app.ui.screens

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.revenuecat.purchases.Package
import com.rigcheck.app.BuildConfig
import com.rigcheck.app.data.PaywallOffers
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.paywallOffers
import com.rigcheck.app.ui.UiTags

// Custom Compose layout per ANDROID_DESIGN_BRIEF.md - not RevenueCat's
// prebuilt Paywall UI, since the mockup is bespoke/brand-matched. Prices
// always come from StoreProduct.price.formatted (Test Store while
// testing), never hardcoded.
//
// Scan packs are sold to Pro accounts only (ADR-0006's 2026-10-12 amendment): a
// Free account is offered Pro and no packs, a Pro account the packs and not Pro.
// Buying Pro here does not close the screen; the plan is read again, and the packs
// replace the Pro offer.
//
// Back sits above the scrolling content so it is always reachable, whatever the
// screen's height or the font size (#186); everything under it scrolls.
@Composable
fun PaywallScreen(
    creditBalance: Int?,
    onPurchase: (Package, (success: Boolean, error: String?) -> Unit) -> Unit,
    onRestore: ((success: Boolean, error: String?) -> Unit) -> Unit,
    // Leaves the screen: after a pack is bought, and from the Back control.
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
    // True in the beta build (#174): the offers are bought with test cards, and the screen says so (#182).
    // A parameter so a test can show it both ways.
    isBeta: Boolean = BuildConfig.IS_BETA,
) {
    val context = LocalContext.current
    var offers by remember { mutableStateOf<PaywallOffers?>(null) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var isBusy by remember { mutableStateOf(false) }
    // Pro was bought here but the plan has not been read as Pro yet: the Pro offer must
    // not be buyable again in that gap (the store refuses a second lifetime purchase).
    var proBought by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        runCatching { loadPackages() }
            .onSuccess { offers = paywallOffers(it) }
            .onFailure { loadError = it.message ?: "Could not load offers." }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Not while a purchase or restore is out: leaving then would let its result close
        // another screen, since a bought pack pops the back stack when it finishes.
        TextButton(
            enabled = !isBusy,
            onClick = onDone,
            modifier = Modifier.padding(horizontal = 8.dp).testTag(UiTags.PAYWALL_BACK),
        ) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Back")
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 20.dp, end = 20.dp, bottom = 20.dp),
        ) {
            Text(
                if (isPro == false) "Unlock Pro" else "Get More Scans",
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.testTag(UiTags.PAYWALL_TITLE),
            )
            accountLabel?.let { label ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "Buying for $label",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f).testTag(UiTags.PAYWALL_ACCOUNT_LABEL),
                    )
                    TextButton(
                        enabled = !isBusy,
                        onClick = onSignOut,
                        modifier = Modifier.testTag(UiTags.PAYWALL_SIGN_OUT_BUTTON),
                    ) { Text("Sign out") }
                }
            }
            isPro?.let { pro ->
                Text(
                    if (pro) "Pro plan" else "Free plan",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 8.dp).testTag(UiTags.PAYWALL_PLAN_LABEL),
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
                modifier = Modifier.padding(top = 12.dp, bottom = 24.dp).testTag(UiTags.PAYWALL_EXPLAINER),
            )

            // Buying a pack ends the visit; buying Pro stays, because what the account
            // can buy has just changed.
            fun buy(pkg: Package, closesScreen: Boolean, done: String, onBought: () -> Unit = {}) {
                isBusy = true
                onPurchase(pkg) { success, error ->
                    isBusy = false
                    if (success) {
                        onBought()
                        Toast.makeText(context, done, Toast.LENGTH_SHORT).show()
                        if (closesScreen) onDone()
                    } else if (error != null) {
                        Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                    }
                }
            }

            if (isBeta) {
                // The same words as Web's BetaPaymentsLabel.
                Text(
                    "Beta: test payments. Every purchase uses a test card; no real money moves.",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 16.dp).testTag(UiTags.PAYWALL_BETA_LABEL),
                )
            }

            val shown = offers
            when {
                loadError != null -> Text(
                    "Couldn't load offers: $loadError",
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.testTag(UiTags.PAYWALL_LOAD_ERROR),
                )
                shown == null -> CircularProgressIndicator(modifier = Modifier.testTag(UiTags.PAYWALL_LOADING))
                isPro == null -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Checking your plan before showing what you can buy.",
                        modifier = Modifier.testTag(UiTags.PAYWALL_PLAN_UNKNOWN),
                    )
                    TextButton(
                        enabled = !isBusy,
                        onClick = onRetryPlan,
                        modifier = Modifier.testTag(UiTags.PAYWALL_RETRY_BUTTON),
                    ) { Text("Try again") }
                }
                isPro -> if (shown.scanPacks.isEmpty()) {
                    Text(
                        "No scan packs are available right now.",
                        modifier = Modifier.testTag(UiTags.PAYWALL_NO_PACKS),
                    )
                } else {
                    OfferList(shown.scanPacks, isBusy) { pkg -> buy(pkg, closesScreen = true, done = "Purchase complete!") }
                }
                else -> shown.proUnlock?.let { pro ->
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        OfferList(listOf(pro), isBusy || proBought) {
                            buy(it, closesScreen = false, done = "Pro unlocked!") { proBought = true }
                        }
                        if (proBought) {
                            Text(
                                "Pro is yours. Updating your plan to show scan packs.",
                                modifier = Modifier.testTag(UiTags.PAYWALL_PRO_BOUGHT),
                            )
                            TextButton(
                        enabled = !isBusy,
                        onClick = onRetryPlan,
                        modifier = Modifier.testTag(UiTags.PAYWALL_RETRY_BUTTON),
                    ) { Text("Try again") }
                        }
                    }
                } ?: Text("Pro isn't available to buy right now.", modifier = Modifier.testTag(UiTags.PAYWALL_NO_PRO))
            }

            TextButton(
                enabled = !isBusy,
                modifier = Modifier.padding(top = 16.dp).testTag(UiTags.PAYWALL_RESTORE_BUTTON),
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
}

@Composable
private fun OfferList(packages: List<Package>, isBusy: Boolean, onBuy: (Package) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        packages.forEach { pkg ->
            Surface(
                shape = MaterialTheme.shapes.medium,
                tonalElevation = 1.dp,
                modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_OFFER_CARD),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            pkg.product.title,
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.testTag(UiTags.PAYWALL_OFFER_TITLE),
                        )
                        pkg.product.description.takeIf { it.isNotBlank() }?.let {
                            Text(
                                it,
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.testTag(UiTags.PAYWALL_OFFER_DESCRIPTION),
                            )
                        }
                    }
                    Button(
                        enabled = !isBusy,
                        onClick = { onBuy(pkg) },
                        modifier = Modifier.testTag(UiTags.PAYWALL_BUY_BUTTON),
                    ) {
                        Text(pkg.product.price.formatted)
                    }
                }
            }
        }
    }
}
