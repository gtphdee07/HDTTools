package com.rigcheck.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.rigcheck.app.ui.navigation.RigCheckNavHost
import com.rigcheck.app.ui.theme.RigCheckTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            RigCheckTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    RigCheckNavHost()
                }
            }
        }
    }
}
