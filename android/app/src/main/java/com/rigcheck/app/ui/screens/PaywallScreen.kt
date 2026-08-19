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
import com.revenuecat.purchases.Offering
import com.revenuecat.purchases.Package
import com.rigcheck.app.data.RevenueCatManager

// Custom Compose layout per ANDROID_DESIGN_BRIEF.md - not RevenueCat's
// prebuilt Paywall UI, since the mockup is bespoke/brand-matched. Prices
// always come from StoreProduct.price.formatted (Test Store while
// testing), never hardcoded.
@Composable
fun PaywallScreen(
    creditBalance: Int?,
    onPurchase: (Package, (success: Boolean, error: String?) -> Unit) -> Unit,
    onRestore: ((success: Boolean, error: String?) -> Unit) -> Unit,
    onDone: () -> Unit,
) {
    val context = LocalContext.current
    var offering by remember { mutableStateOf<Offering?>(null) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var isBusy by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        runCatching { RevenueCatManager.getOfferings() }
            .onSuccess { offering = it.current }
            .onFailure { loadError = it.message ?: "Could not load offers." }
    }

    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        Text("Get More Scans", style = MaterialTheme.typography.headlineMedium)
        Text(
            "You have ${creditBalance ?: 0} scan credit${if (creditBalance == 1) "" else "s"} left. " +
                "Claude reads your truck tag, trailer tag, or scale ticket for you.",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp),
        )

        when {
            loadError != null -> Text(
                "Couldn't load offers: $loadError",
                color = MaterialTheme.colorScheme.error,
            )
            offering == null -> CircularProgressIndicator()
            offering!!.availablePackages.isEmpty() -> Text("No offers are available right now.")
            else -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                offering!!.availablePackages.forEach { pkg ->
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
                            Button(
                                enabled = !isBusy,
                                onClick = {
                                    isBusy = true
                                    onPurchase(pkg) { success, error ->
                                        isBusy = false
                                        if (success) {
                                            Toast.makeText(context, "Purchase complete!", Toast.LENGTH_SHORT).show()
                                            onDone()
                                        } else if (error != null) {
                                            Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                                        }
                                    }
                                },
                            ) {
                                Text(pkg.product.price.formatted)
                            }
                        }
                    }
                }
            }
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
