package com.rigcheck.app.ui.util

import android.content.Intent
import android.net.Uri

// The one place the tester feedback address lives on Android (#182). Web's betaKit.ts and
// docs/BETA_TESTER_GUIDE.md carry the same address, and tests/test_beta_feedback_address.py fails if the
// three differ. The crash-capture ticket reuses this constant.
const val FEEDBACK_EMAIL = "WTIAppDev@gmail.com"

// The subject matches Web's FEEDBACK_MAILTO.
const val FEEDBACK_MAILTO = "mailto:$FEEDBACK_EMAIL?subject=RigCheck%20feedback"

// ACTION_SENDTO with a mailto: Uri offers only mail apps (ACTION_SEND would offer every sharing target).
fun feedbackIntent(): Intent = Intent(Intent.ACTION_SENDTO, Uri.parse(FEEDBACK_MAILTO))
