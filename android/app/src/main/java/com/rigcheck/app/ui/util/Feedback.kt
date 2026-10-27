package com.rigcheck.app.ui.util

import android.content.Intent
import android.net.Uri

// The one place the tester feedback address lives on Android (#182). Web's betaKit.ts and
// docs/BETA_TESTER_GUIDE.md carry the same address, and tests/test_beta_feedback_address.py fails if the
// three differ. The crash report prompt (#184) sends to it too.
const val FEEDBACK_EMAIL = "WTIAppDev@gmail.com"

// The subject matches Web's FEEDBACK_MAILTO.
const val FEEDBACK_MAILTO = "mailto:$FEEDBACK_EMAIL?subject=RigCheck%20feedback"

// ACTION_SENDTO with a mailto: Uri offers only mail apps (ACTION_SEND would offer every sharing target).
fun feedbackIntent(): Intent = Intent(Intent.ACTION_SENDTO, Uri.parse(FEEDBACK_MAILTO))

const val CRASH_REPORT_SUBJECT = "RigCheck crash report"

// The saved crash report as an email to the feedback address. The report goes in the body as an extra, not in
// the Uri, so its length and line breaks need no URL encoding. It opens the mail app's draft: nothing is sent
// until the tester taps Send there.
fun crashReportIntent(report: String): Intent =
    Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:$FEEDBACK_EMAIL")).apply {
        putExtra(Intent.EXTRA_SUBJECT, CRASH_REPORT_SUBJECT)
        putExtra(Intent.EXTRA_TEXT, report)
    }
