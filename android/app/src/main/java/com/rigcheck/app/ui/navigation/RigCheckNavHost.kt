package com.rigcheck.app.ui.navigation

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
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import com.rigcheck.app.data.AccountState
import com.rigcheck.app.ui.RigCheckViewModel
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

            ChooserScreen(
                module = route.module,
                creditBalance = viewModel.creditBalance,
                scanState = viewModel.scanState,
                onChooseManual = { navController.navigate(destinationFor(route.module)) },
                onPhotoScanned = { uri ->
                    viewModel.performScan(route.module, context.contentResolver, uri) { success ->
                        if (success) navController.navigate(destinationFor(route.module))
                    }
                },
                onNeedCredits = { navController.navigate(RigCheckRoute.Paywall) },
                onOpenPaywall = { navController.navigate(RigCheckRoute.Paywall) },
                onDismissScanError = { viewModel.clearScanError() },
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
                onContinue = { navController.navigate(RigCheckRoute.Chooser(EntryModule.TRAILER)) },
                pinWeightPct = viewModel.pinWeightPct,
                onPinWeightPctChange = { viewModel.updatePinWeightPct(it) },
                scanState = viewModel.scanState,
                onScanStandaloneTicket = { uri ->
                    viewModel.performStandaloneScan(context.contentResolver, uri) {}
                },
                onDismissStandaloneScanError = { viewModel.clearScanError() },
            )
        }

        composable<RigCheckRoute.TrailerTagEntry> {
            TrailerTagEntryScreen(
                trailer = viewModel.trailer,
                onTrailerChange = { viewModel.trailer = it },
                onContinue = { navController.navigate(RigCheckRoute.Chooser(EntryModule.SCALE)) },
            )
        }

        composable<RigCheckRoute.ScaleTicketEntry> {
            ScaleTicketEntryScreen(
                scale = viewModel.scale,
                onScaleChange = { viewModel.scale = it },
                onContinue = { goToDisclaimerOrResults() },
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
}
