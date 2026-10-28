package com.rigcheck.app.ui.navigation

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.test.core.app.ApplicationProvider
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.espresso.Espresso.pressBack
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.Account
import com.rigcheck.app.data.AccountBackend
import com.rigcheck.app.data.AccountResult
import com.rigcheck.app.data.AccountState
import com.rigcheck.app.data.BackendStatus
import com.rigcheck.app.data.GarageBackend
import com.rigcheck.app.data.GarageFullException
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.testsupport.nodesWithTagShowing
import com.rigcheck.app.testsupport.onRigCard
import com.rigcheck.app.testsupport.onRigDeleteButton
import com.rigcheck.app.testsupport.rigCardCount
import com.rigcheck.app.ui.RigCheckViewModel
import com.rigcheck.app.ui.UiTags
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// A signed-in account, with nothing to sign in or out of.
private class SignedInAccount : AccountBackend {
    override val status: Flow<BackendStatus> =
        MutableStateFlow(BackendStatus.Authenticated(Account("account-1", "rig@example.com")))
    override suspend fun accessToken(): String? = "token"
    private val notExercised = AccountResult.Failure("not used by these tests")
    override suspend fun signUp(email: String, password: String) = notExercised
    override suspend fun signIn(email: String, password: String) = notExercised
    override suspend fun signInWithGoogle(idToken: String, rawNonce: String) = notExercised
    override suspend fun signInWithApple() = notExercised
    override suspend fun requestPasswordReset(email: String) = notExercised
    override suspend fun signOut() = notExercised
}

// The account's Garage on a pretend server: a cap, and Rigs that "another device" can add behind the app's back.
private class PretendGarage(private val cap: Int) : GarageBackend {
    private val lock = Any()
    private val rigs = mutableListOf<RecentRig>()
    private var nextId = 1

    fun addedElsewhere(nickname: String) = synchronized(lock) {
        rigs += RecentRig(nickname, TruckTag(), TrailerTag(), "2026-10-20T00:00:00Z", id = "elsewhere-${nextId++}")
    }

    fun nicknames(): List<String> = synchronized(lock) { rigs.map { it.nickname } }

    override suspend fun list(): List<RecentRig> = synchronized(lock) { rigs.sortedByDescending { it.lastUsedAt } }

    override suspend fun addRig(idempotencyKey: String, rig: RecentRig, isPro: Boolean?) = synchronized(lock) {
        if (rigs.size >= cap) throw GarageFullException(cap)
        rigs += rig.copy(id = "rig-${nextId++}")
        Unit
    }

    override suspend fun updateRig(rig: RecentRig) = synchronized(lock) {
        val at = rigs.indexOfFirst { it.id == rig.id }
        check(at >= 0) { "rig_not_found" }
        rigs[at] = rig
    }

    override suspend fun deleteRig(id: String) = synchronized(lock) {
        rigs.removeAll { it.id == id }
        Unit
    }
}

// #31: the Rig picker over the account's Garage, through the real nav host and view model. The account is a fake
// signed in, and the Garage a pretend server, so what is checked is what the user sees: Rigs saved on another
// device are in the picker, a finished check saves its Rig to the account, and a full Garage still shows the check.
@RunWith(AndroidJUnit4::class)
class GarageNavigationTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<ComponentActivity>()

    private lateinit var viewModel: RigCheckViewModel

    private fun showApp(garage: PretendGarage) {
        composeRule.runOnUiThread {
            viewModel = RigCheckViewModel(ApplicationProvider.getApplicationContext(), SignedInAccount(), garage)
        }
        composeRule.setContent { RigCheckNavHost(viewModel = viewModel) }
        composeRule.waitUntil(timeoutMillis = 10_000) {
            var state: AccountState? = null
            composeRule.runOnUiThread { state = viewModel.accountState.value }
            state is AccountState.SignedIn
        }
    }

    private fun waitForRig(nickname: String) = composeRule.waitUntil(timeoutMillis = 10_000) {
        composeRule.rigCardCount(nickname) > 0
    }

    // Same recipe as RigCheckNavHostTest (#125): leave the soft keyboard really closed.
    private fun enterNickname(nickname: String) {
        composeRule.onNodeWithTag(UiTags.PICKER_NEW_RIG_INPUT).performTextInput(nickname)
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

    private fun checkNewRigThroughToResults(nickname: String) {
        enterNickname(nickname)
        composeRule.onNodeWithTag(UiTags.PICKER_CREATE_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).performClick()
        composeRule.onNodeWithTag(UiTags.TRUCK_NEXT_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).performClick()
        composeRule.onNodeWithTag(UiTags.TRAILER_NEXT_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.CHOOSER_MANUAL_CARD).performClick()
        composeRule.onNodeWithTag(UiTags.SCALE_CHECK_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.DISCLAIMER_ACCEPT_BUTTON).performClick()
        composeRule.onNodeWithTag(UiTags.RESULTS_START_ANOTHER_BUTTON).assertIsDisplayed()
    }

    @Test
    fun aRigAddedOnAnotherDeviceIsInThePicker() {
        val garage = PretendGarage(cap = 5).apply { addedElsewhere("Added on Web") }

        showApp(garage)

        waitForRig("Added on Web")
        composeRule.onRigCard("Added on Web").assertIsDisplayed()
    }

    @Test
    fun aFinishedCheckSavesItsRigToTheAccount() {
        val garage = PretendGarage(cap = 5)
        showApp(garage)

        checkNewRigThroughToResults("Big Blue")

        composeRule.waitUntil(timeoutMillis = 10_000) { garage.nicknames() == listOf("Big Blue") }
        assertEquals(listOf("Big Blue"), garage.nicknames())
    }

    @Test
    fun aRigAddedOnAnotherDeviceDuringACheckIsInThePickerOnReturning() {
        val garage = PretendGarage(cap = 5)
        showApp(garage)
        checkNewRigThroughToResults("Big Blue")

        garage.addedElsewhere("Added on Web")
        pressBack()

        waitForRig("Added on Web")
        waitForRig("Big Blue")
    }

    // #169: the picker's delete control reaches the account's Garage through the nav host and view model.
    @Test
    fun aRigDeletedFromThePickerIsGoneFromTheAccountAndThePicker() {
        val garage = PretendGarage(cap = 5).apply { addedElsewhere("Old rig"); addedElsewhere("Keeper") }
        showApp(garage)
        waitForRig("Old rig")

        composeRule.onRigDeleteButton("Old rig").performClick()
        composeRule.onNodeWithTag(UiTags.DELETE_RIG_CONFIRM).performClick()

        composeRule.waitUntil(timeoutMillis = 10_000) {
            composeRule.rigCardCount("Old rig") == 0
        }
        assertEquals(listOf("Keeper"), garage.nicknames())
    }

    @Test
    fun aFullGarageStillShowsTheCheckAndSaysTheRigWasNotSaved() {
        val garage = PretendGarage(cap = 1).apply { addedElsewhere("Already here") }
        showApp(garage)

        checkNewRigThroughToResults("One too many")

        composeRule.waitUntil(timeoutMillis = 10_000) {
            composeRule.nodesWithTagShowing(UiTags.GARAGE_NOTICE, "\"One too many\" wasn't saved", substring = true) > 0
        }
        composeRule.onNodeWithTag(UiTags.GARAGE_NOTICE).assertIsDisplayed()
        composeRule.onNodeWithTag(UiTags.RESULTS_START_ANOTHER_BUTTON).assertIsDisplayed()
        assertEquals(listOf("Already here"), garage.nicknames())
    }
}
