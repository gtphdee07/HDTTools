package com.rigcheck.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.rigcheck.app.data.AUTH_REDIRECT_SCHEME
import com.rigcheck.app.data.SupabaseAccountBackend
import com.rigcheck.app.ui.navigation.RigCheckNavHost
import com.rigcheck.app.ui.theme.RigCheckTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Only the launch that started this Activity: after a rotation the
        // original intent is still attached and must not be handled again.
        if (savedInstanceState == null) handleSignInRedirect(intent)
        enableEdgeToEdge()
        setContent {
            RigCheckTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    RigCheckNavHost()
                }
            }
        }
    }

    // Apple sign-in opens a browser tab and comes back as a rigcheck://login
    // deep link carrying the session; Supabase's client completes it. The
    // Activity is singleTop so that return reaches this instance (and its
    // ViewModel) instead of starting a second one.
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleSignInRedirect(intent)
    }

    private fun handleSignInRedirect(intent: Intent?) {
        if (intent?.data?.scheme == AUTH_REDIRECT_SCHEME) {
            SupabaseAccountBackend.get()?.handleDeepLink(intent)
        }
    }
}
