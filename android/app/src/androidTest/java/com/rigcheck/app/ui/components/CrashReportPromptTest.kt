package com.rigcheck.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.StateRestorationTester
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.data.CrashReportStore
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import com.rigcheck.app.ui.UiTags
import androidx.compose.ui.test.onNodeWithTag
import com.rigcheck.app.testsupport.onNodeWithTagText

// #184: the question after a crash. startActivity is faked, so no mail app opens and none is needed on the
// emulator; the store is the real one, on a folder of its own that each test empties. Recreating the
// composition (StateRestorationTester) stands for the next launch or a turn of the screen: it reads the store again.
@RunWith(AndroidJUnit4::class)
class CrashReportPromptTest {

    @get:Rule
    val composeRule = createComposeRule()

    private lateinit var folder: File
    private lateinit var store: CrashReportStore

    @Before
    fun emptyStore() {
        folder = File(ApplicationProvider.getApplicationContext<Context>().cacheDir, "crash-prompt-test")
        folder.deleteRecursively()
        store = CrashReportStore(folder)
    }

    @After
    fun removeStore() {
        folder.deleteRecursively()
    }

    private val question = "RigCheck closed unexpectedly last time. Send details?"

    @Test
    fun withNoSavedCrashNothingIsAsked() {
        composeRule.setContent { CrashReportPrompt(store, startActivity = {}) }

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_QUESTION).assertDoesNotExist()
    }

    @Test
    fun theQuestionSendsNothingUntilTheTesterTapsSendThenOpensTheEmailAndDoesNotReturn() {
        store.save("the report text")
        val fired = mutableListOf<Intent>()
        val restoration = StateRestorationTester(composeRule)
        restoration.setContent { CrashReportPrompt(store, startActivity = { fired += it }) }

        composeRule.onNodeWithTagText(UiTags.CRASH_PROMPT_QUESTION, question).assertIsDisplayed()
        assertEquals("nothing sent just by asking", 0, fired.size)
        assertEquals("the report waits", "the report text", store.pending())

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_SEND).performClick()

        assertEquals(1, fired.size)
        assertEquals(Intent.ACTION_SENDTO, fired[0].action)
        assertEquals("mailto:WTIAppDev@gmail.com", fired[0].dataString)
        assertEquals("the report is the body", "the report text", fired[0].getStringExtra(Intent.EXTRA_TEXT))
        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_QUESTION).assertDoesNotExist()
        assertNull("sent once, so removed", store.pending())

        restoration.emulateSavedInstanceStateRestore()

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_QUESTION).assertDoesNotExist()
        assertEquals("still only the one email", 1, fired.size)
    }

    @Test
    fun notNowRemovesTheReportSendsNothingAndTheQuestionDoesNotReturn() {
        store.save("the report text")
        val fired = mutableListOf<Intent>()
        val restoration = StateRestorationTester(composeRule)
        restoration.setContent { CrashReportPrompt(store, startActivity = { fired += it }) }

        composeRule.onNodeWithTagText(UiTags.CRASH_PROMPT_DISMISS, "Not now").performClick()

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_QUESTION).assertDoesNotExist()
        assertEquals(0, fired.size)
        assertNull(store.pending())

        restoration.emulateSavedInstanceStateRestore()

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_QUESTION).assertDoesNotExist()
        assertEquals(0, fired.size)
    }

    @Test
    fun unansweredTheQuestionComesBackWithTheSameReportAfterTheScreenIsRecreated() {
        store.save("the report text")
        val restoration = StateRestorationTester(composeRule)
        restoration.setContent { CrashReportPrompt(store, startActivity = {}) }

        restoration.emulateSavedInstanceStateRestore()

        composeRule.onNodeWithTagText(UiTags.CRASH_PROMPT_QUESTION, question).assertIsDisplayed()
        assertEquals("the report text", store.pending())
    }

    @Test
    fun aPhoneWithNoMailAppIsToldSoAndAskedNoMore() {
        store.save("the report text")
        composeRule.setContent {
            CrashReportPrompt(store, startActivity = { throw ActivityNotFoundException("no mail app") })
        }

        composeRule.onNodeWithTag(UiTags.CRASH_PROMPT_SEND).performClick()

        composeRule.onNodeWithTagText(UiTags.CRASH_PROMPT_NO_MAIL_APP, "This phone has no email app. Write to WTIAppDev@gmail.com instead.")
            .assertIsDisplayed()
        composeRule.onNodeWithTagText(UiTags.CRASH_PROMPT_DISMISS, "OK").performClick()
        composeRule.onNodeWithTagText(UiTags.CRASH_PROMPT_DISMISS, "OK").assertDoesNotExist()
        assertNull(store.pending())
    }
}
