package com.rigcheck.app.ui.experiments.cameraoverlay

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.rigcheck.app.ui.theme.RigCheckTheme

// Standalone entry point for the camera-overlay research spike
// (ClaudePlans/2026-08-27-android-camera-overlay-spike.md). Deliberately not
// reached from MainActivity/RigCheckNavHost - launch it directly, e.g.:
//   adb shell am start -n com.rigcheck.app/.ui.experiments.cameraoverlay.CameraOverlaySpikeActivity
// This activity (and the whole ui/experiments/cameraoverlay package) is a
// feasibility spike, not a production screen; see the plan's report for the
// go/no-go recommendation before wiring anything here into real navigation.
class CameraOverlaySpikeActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            RigCheckTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    CameraOverlaySpikeScreen()
                }
            }
        }
    }
}
