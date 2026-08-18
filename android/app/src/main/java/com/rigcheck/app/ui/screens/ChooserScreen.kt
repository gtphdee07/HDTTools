package com.rigcheck.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rigcheck.app.ui.components.ScanOrManualChooser
import com.rigcheck.app.ui.navigation.EntryModule

private data class ChooserCopy(val title: String, val prompt: String)

private fun copyFor(module: EntryModule): ChooserCopy = when (module) {
    EntryModule.TRUCK -> ChooserCopy("Truck Tag", "How do you want to enter your truck's compliance-label values?")
    EntryModule.TRAILER -> ChooserCopy("Trailer Tag", "How do you want to enter your trailer's compliance-label values?")
    EntryModule.SCALE -> ChooserCopy("Scale Ticket", "How do you want to enter your CAT Scale ticket values?")
}

@Composable
fun ChooserScreen(
    module: EntryModule,
    onChooseManual: () -> Unit,
) {
    val copy = copyFor(module)
    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        Text(copy.title, style = MaterialTheme.typography.headlineMedium)
        Text(
            copy.prompt,
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 24.dp, bottom = 16.dp),
        )
        ScanOrManualChooser(onChooseManual = onChooseManual)
        Text(
            "This same choice appears again before the trailer tag and scale ticket screens.",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(top = 16.dp),
        )
    }
}
