package com.rigcheck.app.ui.navigation

import android.content.ContentResolver
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavBackStackEntry
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import com.rigcheck.app.data.APPLE_SIGN_IN_ENABLED
import com.rigcheck.app.data.AccountState
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.ScanNextStep
import com.rigcheck.app.ui.ScanScreen
import com.rigcheck.app.ui.components.LateScanDialog
import com.rigcheck.app.ui.screens.AccountScreen
import com.rigcheck.app.ui.screens.ChooserScreen
import com.rigcheck.app.ui.screens.DisclaimerScreen
import com.rigcheck.app.ui.screens.PaywallScreen
import com.rigcheck.app.ui.screens.ResultsScreen
import com.rigcheck.app.ui.screens.RigPickerScreen
import com.rigcheck.app.ui.screens.ScaleTicketEntryScreen
import com.rigcheck.app.ui.screens.TrailerTagEntryScreen
import com.rigcheck.app.ui.screens.TruckTagEntryScreen
import com.rigcheck.app.ui.util.findActivity

@Composable
fun RigCheckNavHost(
    navController: NavHostController = rememberNavController(),
    viewModel: RigCheckViewModel = viewModel(),
) {
    val recentRigs by viewModel.recentRigs.collectAsStateWithLifecycle()
    val accountState by viewModel.accountState.collectAsStateWithLifecycle()

    // Routes to the screen after the scale ticket - the disclaimer only
    // once per process lifetime (per the brief: "shown once per app
    // session"), straight to results on every check after that.
    fun goToDisclaimerOrResults() {
        val destination = if (viewModel.disclaimerAcknowledged) RigCheckRoute.Results else RigCheckRoute.Disclaimer
        navController.navigate(destination) {
            popUpTo(RigCheckRoute.RigPicker) { inclusive = false }
        }
    }

    // What a failed Scan's dialog offers beyond OK. Signing in and buying Scans
    // end at the Paywall route, which shows the sign-in screen to a signed-out
    // user. A user the Worker refused is still signed in here, so that session
    // is ended first, as Web does for its "Sign in again". Try again sends the
    // last photo again, so the screen that started it says what happens when it
    // succeeds. The screens handle the rest themselves: they own the photo
    // choice and the fields to type into.
    fun followScanNextStep(step: ScanNextStep, resolver: ContentResolver, onTryAgainDone: (success: Boolean) -> Unit) {
        viewModel.clearScanError()
        when (step) {
            ScanNextStep.SIGN_IN -> {
                if (accountState is AccountState.SignedIn) viewModel.signOut()
                navController.navigate(RigCheckRoute.Paywall)
            }
            ScanNextStep.BUY_SCANS -> navController.navigate(RigCheckRoute.Paywall)
            ScanNextStep.TRY_AGAIN -> viewModel.retryScan(resolver, onTryAgainDone)
            ScanNextStep.CHOOSE_DIFFERENT_PHOTO, ScanNextStep.TYPE_IT_IN -> Unit
        }
    }

    // A Scan belongs to the screen it started on: tell the view model which
    // screen is on show, so one started elsewhere is over for its check (#118).
    // Collecting again after turning the device sends the same screen, which
    // ends nothing.
    LaunchedEffect(navController) {
        navController.currentBackStackEntryFlow.collect { viewModel.screenShown(scanScreenOf(it)) }
    }

    NavHost(navController = navController, startDestination = RigCheckRoute.RigPicker) {
        composable<RigCheckRoute.RigPicker> {
            RigPickerScreen(
                recentRigs = recentRigs,
                creditBalance = viewModel.creditBalance,
                onSelectRecentRig = { rig ->
                    viewModel.selectRecentRig(rig)
                    navController.navigate(RigCheckRoute.Chooser(EntryModule.SCALE))
                },
                onStartNewRig = { nickname ->
                    viewModel.startNewRig(nickname)
                    navController.navigate(RigCheckRoute.Chooser(EntryModule.TRUCK))
                },
                onOpenPaywall = { navController.navigate(RigCheckRoute.Paywall) },
            )
        }

        composable<RigCheckRoute.Chooser> { backStackEntry ->
            val route: RigCheckRoute.Chooser = backStackEntry.toRoute()
            val context = LocalContext.current

            fun destinationFor(module: EntryModule) = when (module) {
                EntryModule.TRUCK -> RigCheckRoute.TruckTagEntry
                EntryModule.TRAILER -> RigCheckRoute.TrailerTagEntry
                EntryModule.SCALE -> RigCheckRoute.ScaleTicketEntry
            }

            // A Scan that delivers goes on to this document's entry screen to be
            // reviewed; a retry from the error dialog ends the same way.
            val onScanDone = { success: Boolean ->
                if (success) navController.navigate(destinationFor(route.module))
            }

            ChooserScreen(
                module = route.module,
                creditBalance = viewModel.creditBalance,
                scanState = viewModel.scanState,
                onChooseManual = {
                    viewModel.scanNoticeState.enteredManually()
                    navController.navigate(destinationFor(route.module))
                },
                onPhotoScanned = { uri ->
                    viewModel.performScan(route.module, context.contentResolver, uri, onScanDone)
                },
                onNeedCredits = { navController.navigate(RigCheckRoute.Paywall) },
                onOpenPaywall = { navController.navigate(RigCheckRoute.Paywall) },
                onDismissScanError = { viewModel.clearScanError() },
                onScanErrorNextStep = { step -> followScanNextStep(step, context.contentResolver, onScanDone) },
            )
        }

        // Buying (and so scanning, which needs credits) is the one place the
        // app asks for an account - the free manual flow never gets here.
        composable<RigCheckRoute.Paywall> {
            val activity = LocalContext.current.findActivity()
            when (val account = accountState) {
                AccountState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                AccountState.SignedOut -> AccountScreen(
                    reason = "Sign in or create an account to buy scans. Your purchases and scan balance " +
                        "follow your account to every device.",
                    showApple = APPLE_SIGN_IN_ENABLED,
                    onSignIn = { email, password, onResult -> viewModel.signIn(email, password, onResult) },
                    onSignUp = { email, password, onResult -> viewModel.signUp(email, password, onResult) },
                    onGoogle = { onResult -> viewModel.signInWithGoogle(activity, onResult) },
                    onApple = { onResult -> viewModel.signInWithApple(onResult) },
                    onForgotPassword = { email, onResult -> viewModel.requestPasswordReset(email, onResult) },
                    onNotNow = { navController.popBackStack() },
                )
                is AccountState.SignedIn -> PaywallScreen(
                    creditBalance = viewModel.creditBalance,
                    onPurchase = { pkg, onResult -> viewModel.purchase(activity, pkg, onResult) },
                    onRestore = { onResult -> viewModel.restorePurchases(onResult) },
                    onDone = { navController.popBackStack() },
                    accountLabel = account.account.email ?: account.account.id,
                    onSignOut = { viewModel.signOut() },
                )
            }
        }

        composable<RigCheckRoute.TruckTagEntry> {
            val context = LocalContext.current
            TruckTagEntryScreen(
                truck = viewModel.truck,
                onTruckChange = { viewModel.truck = it },
                onContinue = {
                    viewModel.scanNoticeState.leftEntryScreen()
                    navController.navigate(RigCheckRoute.Chooser(EntryModule.TRAILER))
                },
                scanNotice = viewModel.scanNoticeState.notice,
                pinWeightPct = viewModel.pinWeightPct,
                onPinWeightPctChange = { viewModel.updatePinWeightPct(it) },
                scanState = viewModel.scanState,
                onScanStandaloneTicket = { uri ->
                    viewModel.performStandaloneScan(context.contentResolver, uri) {}
                },
                onDismissStandaloneScanError = { viewModel.clearScanError() },
                creditBalance = viewModel.creditBalance,
                onNeedCredits = { navController.navigate(RigCheckRoute.Paywall) },
                onScanErrorNextStep = { step -> followScanNextStep(step, context.contentResolver) {} },
            )
        }

        composable<RigCheckRoute.TrailerTagEntry> {
            TrailerTagEntryScreen(
                trailer = viewModel.trailer,
                onTrailerChange = { viewModel.trailer = it },
                onContinue = {
                    viewModel.scanNoticeState.leftEntryScreen()
                    navController.navigate(RigCheckRoute.Chooser(EntryModule.SCALE))
                },
                scanNotice = viewModel.scanNoticeState.notice,
            )
        }

        composable<RigCheckRoute.ScaleTicketEntry> {
            ScaleTicketEntryScreen(
                scale = viewModel.scale,
                onScaleChange = { viewModel.scale = it },
                onContinue = {
                    viewModel.scanNoticeState.leftEntryScreen()
                    goToDisclaimerOrResults()
                },
                scanNotice = viewModel.scanNoticeState.notice,
            )
        }

        composable<RigCheckRoute.Disclaimer> {
            DisclaimerScreen(
                onAcknowledge = {
                    viewModel.acknowledgeDisclaimer()
                    navController.navigate(RigCheckRoute.Results) {
                        popUpTo(RigCheckRoute.RigPicker) { inclusive = false }
                    }
                },
            )
        }

        composable<RigCheckRoute.Results> {
            LaunchedEffect(Unit) { viewModel.saveCurrentRig() }
            ResultsScreen(
                rigNickname = viewModel.rigNickname,
                breakdown = viewModel.breakdown,
                verdict = viewModel.verdict,
                onStartAnother = {
                    navController.navigate(RigCheckRoute.RigPicker) {
                        popUpTo(RigCheckRoute.RigPicker) { inclusive = true }
                    }
                },
            )
        }
    }

    // On whichever screen the user is on, so a Scan that answered after they
    // left its check is never missed. One at a time, oldest first.
    viewModel.lateScanNotices.firstOrNull()?.let { message ->
        LateScanDialog(message = message, onDismiss = { viewModel.dismissLateScanNotice() })
    }
}

private fun scanScreenOf(entry: NavBackStackEntry): ScanScreen = when {
    entry.destination.hasRoute<RigCheckRoute.Chooser>() -> ScanScreen.Chooser(entry.toRoute<RigCheckRoute.Chooser>().module)
    entry.destination.hasRoute<RigCheckRoute.TruckTagEntry>() -> ScanScreen.TruckTagEntry
    else -> ScanScreen.Elsewhere
}
