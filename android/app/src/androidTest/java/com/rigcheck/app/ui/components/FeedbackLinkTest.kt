package com.rigcheck.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Intent
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.testsupport.onNodeWithTagText
import com.rigcheck.app.ui.UiTags
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

// "Send feedback" (#182): the intent it fires, and a phone with no mail app. startActivity is faked, so
// no mail app opens and none is needed on the emulator.
@RunWith(AndroidJUnit4::class)
class FeedbackLinkTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val link = Modifier.testTag(UiTags.PICKER_FEEDBACK_LINK)

    @Test
    fun tappingSendsAnEmailIntentToTheFeedbackAddress() {
        val fired = mutableListOf<Intent>()
        composeRule.setContent { FeedbackLink(linkModifier = link, startActivity = { fired += it }) }

        composeRule.onNodeWithTag(UiTags.PICKER_FEEDBACK_LINK).performClick()

        assertEquals(1, fired.size)
        assertEquals(Intent.ACTION_SENDTO, fired[0].action)
        assertEquals("mailto:WTIAppDev@gmail.com?subject=RigCheck%20feedback", fired[0].dataString)
        composeRule.onNodeWithTag(UiTags.SEND_FEEDBACK_NO_MAIL_APP).assertDoesNotExist()
    }

    @Test
    fun aPhoneWithNoMailAppGetsAMessageNotACrash() {
        composeRule.setContent {
            FeedbackLink(linkModifier = link, startActivity = { throw ActivityNotFoundException("no mail app") })
        }

        composeRule.onNodeWithTag(UiTags.PICKER_FEEDBACK_LINK).performClick()

        composeRule.onNodeWithTagText(UiTags.SEND_FEEDBACK_NO_MAIL_APP, "This phone has no email app. Write to WTIAppDev@gmail.com instead.")
            .assertIsDisplayed()
    }
}
