package com.rigcheck.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import com.rigcheck.app.ui.RigCheckViewModel
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
                onSelectRecentRig = { rig ->
                    viewModel.selectRecentRig(rig)
                    navController.navigate(RigCheckRoute.Chooser(EntryModule.SCALE))
                },
                onStartNewRig = { nickname ->
                    viewModel.startNewRig(nickname)
                    navController.navigate(RigCheckRoute.Chooser(EntryModule.TRUCK))
                },
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

        composable<RigCheckRoute.Paywall> {
            val activity = LocalContext.current.findActivity()
            PaywallScreen(
                creditBalance = viewModel.creditBalance,
                onPurchase = { pkg, onResult -> viewModel.purchase(activity, pkg, onResult) },
                onRestore = { onResult -> viewModel.restorePurchases(onResult) },
                onDone = { navController.popBackStack() },
            )
        }

        composable<RigCheckRoute.TruckTagEntry> {
            TruckTagEntryScreen(
                truck = viewModel.truck,
                onTruckChange = { viewModel.truck = it },
                onContinue = { navController.navigate(RigCheckRoute.Chooser(EntryModule.TRAILER)) },
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
            ResultsScreen(breakdown = viewModel.breakdown, verdict = viewModel.verdict)
        }
    }
}
