package com.rigcheck.app.ui.screens

import android.widget.Toast
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.revenuecat.purchases.Package
import com.rigcheck.app.BuildConfig
import com.rigcheck.app.data.PaywallOffers
import com.rigcheck.app.data.RevenueCatManager
import com.rigcheck.app.data.paywallOffers
import com.rigcheck.app.ui.ScanMessages
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.components.RigCheckBadge
import com.rigcheck.app.ui.components.RigCheckBadgeKind
import com.rigcheck.app.ui.components.RigCheckButton
import com.rigcheck.app.ui.components.RigCheckButtonKind
import com.rigcheck.app.ui.components.RigCheckButtonSize
import com.rigcheck.app.ui.components.RigCheckFooter
import com.rigcheck.app.ui.components.RigCheckNoticeCard
import com.rigcheck.app.ui.components.RigCheckNoticeTone
import com.rigcheck.app.ui.components.RigCheckSnackbarHost
import com.rigcheck.app.ui.components.RigCheckSpinner
import com.rigcheck.app.ui.components.RigCheckTopBar
import com.rigcheck.app.ui.theme.Border
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.InkMuted
import com.rigcheck.app.ui.theme.PurpleDeep
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.RigCheckStyles
import com.rigcheck.app.ui.theme.TintPurple
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite
import kotlinx.coroutines.launch

// The Paywall's running copy (the explainer and the lines about the plan): DM Sans 400 15/22, as the map gives it.
private val PaywallCopyStyle = RigCheckStyles.bodyMd.copy(lineHeight = 22.sp)

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
// On the design's skeleton (resize-rules.md, "What scrolls and what is pinned"): the top bar (Back and the title) is
// pinned so Back is always reachable, whatever the screen's height or the font size (#186); the beta notice, the
// account line, the plan, the explainer and the offers scroll as one column; Restore purchase is pinned in the footer,
// so the navigation bar can no longer cover it (#186). What a purchase or a restore answers is a Snackbar above the
// footer. The one exception is a bought pack: it leaves the screen at once, which would take a Snackbar with it, so
// that confirmation stays a system Toast (owner, 2026-10-30, on #196).
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
    // A paid Scan is out (#197): Sign out is disabled, with the reason in words, until it answers.
    scanIsOut: Boolean = false,
) {
    val context = LocalContext.current
    var offers by remember { mutableStateOf<PaywallOffers?>(null) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var isBusy by remember { mutableStateOf(false) }
    // Pro was bought here but the plan has not been read as Pro yet: the Pro offer must
    // not be buyable again in that gap (the store refuses a second lifetime purchase).
    var proBought by remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // One message at a time: a new one replaces the one still showing.
    fun say(message: String) {
        scope.launch {
            snackbar.currentSnackbarData?.dismiss()
            snackbar.showSnackbar(message, duration = SnackbarDuration.Short)
        }
    }

    LaunchedEffect(Unit) {
        runCatching { loadPackages() }
            .onSuccess { offers = paywallOffers(it) }
            .onFailure { loadError = it.message ?: "Could not load offers." }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Not while a purchase or restore is out: leaving then would let its result close
        // another screen, since a bought pack pops the back stack when it finishes.
        RigCheckTopBar(
            title = if (isPro == false) "Unlock Pro" else "Get More Scans",
            onBack = onDone,
            backEnabled = !isBusy,
            titleModifier = Modifier.testTag(UiTags.PAYWALL_TITLE),
            backModifier = Modifier.testTag(UiTags.PAYWALL_BACK),
        )

        // The Snackbar sits at the foot of this area, so it is above the pinned footer and clears Restore purchase.
        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(start = 16.dp, top = 20.dp, end = 16.dp, bottom = 24.dp),
            ) {
                if (isBeta) {
                    // The same words as Web's BetaPaymentsLabel.
                    RigCheckNoticeCard(
                        tone = RigCheckNoticeTone.Scan,
                        icon = Icons.Outlined.Info,
                        modifier = Modifier.testTag(UiTags.PAYWALL_BETA_LABEL),
                    ) {
                        Text(
                            "Beta: test payments. Every purchase uses a test card; no real money moves.",
                            style = RigCheckStyles.bodySm,
                            fontWeight = FontWeight.Bold,
                            color = Ink,
                        )
                    }
                }
                accountLabel?.let { label ->
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Buying for $label",
                                style = RigCheckStyles.bodySm,
                                color = InkMuted,
                                modifier = Modifier.weight(1f).testTag(UiTags.PAYWALL_ACCOUNT_LABEL),
                            )
                            RigCheckButton(
                                text = "Sign out",
                                onClick = onSignOut,
                                kind = RigCheckButtonKind.Ghost,
                                size = RigCheckButtonSize.Compact,
                                enabled = !isBusy && !scanIsOut,
                                icon = Icons.AutoMirrored.Filled.Logout,
                                modifier = Modifier.testTag(UiTags.PAYWALL_SIGN_OUT_BUTTON),
                            )
                        }
                        if (scanIsOut) {
                            Text(ScanMessages.SIGN_OUT_UNAVAILABLE, style = RigCheckStyles.bodySm, color = InkMuted)
                        }
                    }
                }
                isPro?.let { pro ->
                    RigCheckBadge(
                        text = if (pro) "Pro plan" else "Free plan",
                        kind = RigCheckBadgeKind.Plan,
                        modifier = Modifier.testTag(UiTags.PAYWALL_PLAN_LABEL),
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
                    style = PaywallCopyStyle,
                    color = Ink,
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_EXPLAINER),
                )

                // Buying a pack ends the visit; buying Pro stays, because what the account
                // can buy has just changed.
                fun buy(pkg: Package, closesScreen: Boolean, done: String, onBought: () -> Unit = {}) {
                    isBusy = true
                    onPurchase(pkg) { success, error ->
                        isBusy = false
                        if (success) {
                            onBought()
                            if (closesScreen) {
                                // The screen is gone in a moment, and a Snackbar goes with it: this one stays a Toast.
                                Toast.makeText(context, done, Toast.LENGTH_SHORT).show()
                                onDone()
                            } else {
                                say(done)
                            }
                        } else if (error != null) {
                            say(error)
                        }
                    }
                }

                val shown = offers
                when {
                    loadError != null -> RigCheckNoticeCard(
                        text = "Couldn't load offers: $loadError",
                        tone = RigCheckNoticeTone.Error,
                        icon = Icons.Outlined.Info,
                        modifier = Modifier.testTag(UiTags.PAYWALL_LOAD_ERROR),
                    )
                    shown == null -> Box(modifier = Modifier.fillMaxWidth().padding(top = 24.dp), contentAlignment = Alignment.Center) {
                        RigCheckSpinner(modifier = Modifier.testTag(UiTags.PAYWALL_LOADING))
                    }
                    isPro == null -> Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            "Checking your plan before showing what you can buy.",
                            style = PaywallCopyStyle,
                            color = Ink,
                            modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_PLAN_UNKNOWN),
                        )
                        TryAgainButton(enabled = !isBusy, onClick = onRetryPlan)
                    }
                    isPro -> if (shown.scanPacks.isEmpty()) {
                        RigCheckNoticeCard(
                            text = "No scan packs are available right now.",
                            tone = RigCheckNoticeTone.Info,
                            icon = Icons.Outlined.Info,
                            modifier = Modifier.testTag(UiTags.PAYWALL_NO_PACKS),
                        )
                    } else {
                        OfferList(shown.scanPacks, isBusy, large = false) { pkg ->
                            buy(pkg, closesScreen = true, done = "Purchase complete!")
                        }
                    }
                    else -> shown.proUnlock?.let { pro ->
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            OfferList(listOf(pro), isBusy || proBought, large = true) {
                                buy(it, closesScreen = false, done = "Pro unlocked!") { proBought = true }
                            }
                            if (proBought) {
                                Text(
                                    "Pro is yours. Updating your plan to show scan packs.",
                                    style = PaywallCopyStyle,
                                    color = Ink,
                                    modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_PRO_BOUGHT),
                                )
                                TryAgainButton(enabled = !isBusy, onClick = onRetryPlan)
                            }
                        }
                    } ?: RigCheckNoticeCard(
                        text = "Pro isn't available to buy right now.",
                        tone = RigCheckNoticeTone.Info,
                        icon = Icons.Outlined.Info,
                        modifier = Modifier.testTag(UiTags.PAYWALL_NO_PRO),
                    )
                }
            }

            RigCheckSnackbarHost(
                state = snackbar,
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 16.dp),
                snackbarModifier = Modifier.testTag(UiTags.PAYWALL_TOAST),
            )
        }

        RigCheckFooter {
            RigCheckButton(
                text = "Restore purchase",
                enabled = !isBusy,
                kind = RigCheckButtonKind.Ghost,
                modifier = Modifier.testTag(UiTags.PAYWALL_RESTORE_BUTTON),
                onClick = {
                    isBusy = true
                    onRestore { success, error ->
                        isBusy = false
                        if (success) {
                            say("Purchases restored.")
                        } else if (error != null) {
                            say(error)
                        }
                    }
                },
            )
        }
    }
}

// The plan could not be read (or has not caught up after Pro was bought): read it again. A secondary button at full
// width and 48 dp, as the map draws it.
@Composable
private fun TryAgainButton(enabled: Boolean, onClick: () -> Unit) {
    RigCheckButton(
        text = "Try again",
        onClick = onClick,
        kind = RigCheckButtonKind.Secondary,
        size = RigCheckButtonSize.Compact,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_RETRY_BUTTON),
    )
}

// components.md, "Offer card". A Free account is offered Pro on one large card (a tint-purple fill and a 1.5 dp
// purple-deep border, 24 dp radius, the full-width price button inside); a Pro account gets one white row card per pack
// with a compact price button at the right. The price text is the store's own, so the button grows and never truncates.
@Composable
private fun OfferList(packages: List<Package>, isBusy: Boolean, large: Boolean, onBuy: (Package) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        packages.forEach { pkg ->
            val description = pkg.product.description.takeIf { it.isNotBlank() }
            if (large) {
                Surface(
                    shape = RoundedCornerShape(Radii.Panel),
                    color = TintPurple,
                    border = BorderStroke(1.5.dp, PurpleDeep),
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_OFFER_CARD),
                ) {
                    // The frame's text starts 21.5 dp inside the card: the 1.5 dp border and 20 dp of padding.
                    Column(modifier = Modifier.padding(21.5.dp)) {
                        Text(
                            pkg.product.title,
                            style = RigCheckStyles.offerTitle,
                            color = PurpleDeep,
                            modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_OFFER_TITLE),
                        )
                        description?.let {
                            Text(
                                it,
                                style = RigCheckStyles.bodyMd,
                                color = Ink,
                                modifier = Modifier.fillMaxWidth().padding(top = 4.dp).testTag(UiTags.PAYWALL_OFFER_DESCRIPTION),
                            )
                        }
                        RigCheckButton(
                            text = pkg.product.price.formatted,
                            enabled = !isBusy,
                            onClick = { onBuy(pkg) },
                            modifier = Modifier.padding(top = 16.dp).testTag(UiTags.PAYWALL_BUY_BUTTON),
                        )
                    }
                }
            } else {
                Surface(
                    shape = RoundedCornerShape(Radii.Card),
                    color = SurfaceWhite,
                    border = BorderStroke(1.dp, Border),
                    modifier = Modifier.fillMaxWidth().testTag(UiTags.PAYWALL_OFFER_CARD),
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                pkg.product.title,
                                style = RigCheckStyles.title,
                                color = Ink,
                                modifier = Modifier.testTag(UiTags.PAYWALL_OFFER_TITLE),
                            )
                            description?.let {
                                Text(
                                    it,
                                    style = RigCheckStyles.bodySm,
                                    color = InkMuted,
                                    modifier = Modifier.testTag(UiTags.PAYWALL_OFFER_DESCRIPTION),
                                )
                            }
                        }
                        RigCheckButton(
                            text = pkg.product.price.formatted,
                            enabled = !isBusy,
                            onClick = { onBuy(pkg) },
                            size = RigCheckButtonSize.Compact,
                            modifier = Modifier.testTag(UiTags.PAYWALL_BUY_BUTTON),
                        )
                    }
                }
            }
        }
    }
}
