package com.rigcheck.app.ui.navigation

import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.core.graphics.Insets
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.revenuecat.purchases.PackageType
import com.rigcheck.app.testsupport.fakePackage
import com.rigcheck.app.ui.screens.PaywallScreen
import com.rigcheck.app.ui.screens.RigPickerScreen
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// #186: the app draws edge to edge, so the window reaches behind the status bar and the
// navigation bar, and RigCheckApp is the one place that pushes every screen inside them.
// These tests mount real screens under RigCheckApp in an edge-to-edge Activity, read the
// window's real system-bar insets, and check the controls' bounds against them. The
// insets are whatever the device is set to, so the same tests cover 3-button and gesture
// navigation: run them once with each (android/TESTING.md, "System bars"). Without
// RigCheckApp's padding the bottom-most control sits under the bar and these fail.
@RunWith(AndroidJUnit4::class)
class SystemBarsTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    // MainActivity does this before setContent; the test Activity has to as well.
    @Before
    fun drawEdgeToEdge() {
        composeRule.activityRule.scenario.onActivity { it.enableEdgeToEdge() }
    }

    private fun systemBars(): Insets {
        var insets: Insets = Insets.NONE
        composeRule.runOnUiThread {
            insets = ViewCompat.getRootWindowInsets(composeRule.activity.window.decorView)
                ?.getInsets(WindowInsetsCompat.Type.systemBars()) ?: Insets.NONE
        }
        return insets
    }

    private fun windowHeightPx(): Int {
        var height = 0
        composeRule.runOnUiThread { height = composeRule.activity.window.decorView.height }
        return height
    }

    // Each control lies fully between the status bar and the navigation bar. Both bars
    // must really be there, or the test would pass without proving anything. Every
    // control is checked before the test fails, so one failure does not hide another.
    private fun assertClearOfTheSystemBars(vararg controls: Pair<String, SemanticsNodeInteraction>) {
        val bars = systemBars()
        assertTrue("the device shows no navigation bar inset ($bars), so this proves nothing", bars.bottom > 0)
        assertTrue("the device shows no status bar inset ($bars), so this proves nothing", bars.top > 0)

        val usableBottom = windowHeightPx() - bars.bottom
        val problems = buildList {
            for ((name, control) in controls) {
                control.assertIsDisplayed()
                val bounds = control.fetchSemanticsNode().boundsInWindow
                if (bounds.bottom > usableBottom) {
                    add("$name ends at ${bounds.bottom}px, under the navigation bar that starts at ${usableBottom}px")
                }
                if (bounds.top < bars.top) {
                    add("$name starts at ${bounds.top}px, under the status bar that ends at ${bars.top}px")
                }
            }
        }
        assertTrue(problems.joinToString("; "), problems.isEmpty())
    }

    // Same recipe as RigCheckNavHostTest (#125): leave the soft keyboard really closed, so
    // the bounds are read in the layout the user sees when the keyboard is away.
    private fun enterNickname(nickname: String) {
        composeRule.onNodeWithText("Rig nickname").performTextInput(nickname)
        composeRule.waitUntil(timeoutMillis = 30_000) { isKeyboardVisible() }
        closeSoftKeyboard()
        composeRule.waitUntil(timeoutMillis = 30_000) { !isKeyboardVisible() }
    }

    private fun isKeyboardVisible(): Boolean {
        var visible = false
        composeRule.runOnUiThread {
            visible = ViewCompat.getRootWindowInsets(composeRule.activity.window.decorView)
                ?.isVisible(WindowInsetsCompat.Type.ime()) == true
        }
        return visible
    }

    @Test
    fun theRigPickersCreateButtonLiesAboveTheNavigationBarAndCanBeTapped() {
        var created: String? = null
        composeRule.setContent {
            RigCheckApp {
                RigPickerScreen(
                    recentRigs = emptyList(),
                    creditBalance = 3,
                    onSelectRecentRig = { },
                    onStartNewRig = { created = it },
                    onOpenPaywall = { },
                )
            }
        }
        // Create is disabled until a nickname is typed.
        enterNickname("Big Blue")

        // The RigCheck title is the first thing under the status bar, Create the last above the navigation bar.
        assertClearOfTheSystemBars(
            "the RigCheck title" to composeRule.onNodeWithText("RigCheck"),
            "the Create button" to composeRule.onNodeWithText("Create"),
        )
        composeRule.onNodeWithText("Create").performClick()
        assertEquals("Big Blue", created)
    }

    // Enough scan packs that the Paywall is taller than any phone, so "Restore purchase",
    // its last control, is reached by scrolling to the end and rests at the bottom edge of
    // the screen's usable area: the position where the navigation bar used to cover it.
    @Test
    fun thePaywallsRestorePurchaseLiesAboveTheNavigationBarAndCanBeTapped() {
        var restored = false
        val packs = (1..12).map { fakePackage("pack-$it", PackageType.CUSTOM, "Pack $it", "\$$it.99") }
        composeRule.setContent {
            RigCheckApp {
                PaywallScreen(
                    creditBalance = 0,
                    onPurchase = { _, _ -> },
                    onRestore = { restored = true },
                    onDone = { },
                    isPro = true,
                    loadPackages = { packs },
                )
            }
        }
        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onAllNodesWithText("Pack 1", substring = true).fetchSemanticsNodes().isNotEmpty()
        }

        composeRule.onNodeWithText("Restore purchase").performScrollTo()

        assertClearOfTheSystemBars(
            "Restore purchase" to composeRule.onNodeWithText("Restore purchase"),
            "the Back button" to composeRule.onNodeWithTag("paywall_back"),
        )

        composeRule.onNodeWithText("Restore purchase").performClick()
        assertTrue("tapping Restore purchase should have asked for the restore", restored)
    }
}
