package com.rigcheck.app.testsupport

import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.delay

// Takes the device offline for an External test through airplane mode, which
// turns off Wi-Fi and mobile data together (on the emulator `svc wifi disable`
// alone leaves the mobile-data path up). The shell command runs under
// UiAutomation's shell identity; its output has to be read to the end or the
// command may not have finished when it returns.
private fun shell(command: String): String {
    val descriptor = InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(command)
    return android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor).use { it.readBytes().decodeToString() }
}

private suspend fun setAirplaneMode(enabled: Boolean) {
    shell("cmd connectivity airplane-mode ${if (enabled) "enable" else "disable"}")
    // The setting flips at once but the radios take a moment to follow.
    delay(if (enabled) 6_000 else 8_000)
}

// Runs `block` with no network and always brings it back, even when the block
// throws, so a failed offline test cannot leave the emulator offline for the
// next one (test-external.ps1 also switches airplane mode off after the run).
suspend fun <T> whileOffline(block: suspend () -> T): T {
    setAirplaneMode(true)
    try {
        return block()
    } finally {
        setAirplaneMode(false)
    }
}
