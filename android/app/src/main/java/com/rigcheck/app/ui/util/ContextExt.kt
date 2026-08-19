package com.rigcheck.app.ui.util

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper

// Compose's LocalContext.current is sometimes a ContextWrapper (theming,
// test harnesses) rather than the Activity itself - unwrap to find it,
// rather than assuming a direct cast always works.
tailrec fun Context.findActivity(): Activity = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> error("No Activity found in this Context chain.")
}
