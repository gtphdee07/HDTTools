package com.rigcheck.app.testsupport

import androidx.test.platform.app.InstrumentationRegistry

// The scan service (#21) charges the account named by a signed-in user's
// access token, so the External suite's real scans send a real token for the
// funded Supabase test user. test-weekly.ps1 signs that user in (through
// workers/scan-proxy's `npm run live-token`, so the credentials never reach
// the device) and hands the result over two ways:
//  - the access token, as the `weeklyAccessToken` instrumentation argument -
//    readable in a test, which is all that needs it;
//  - the account id, as the text of the weekly marker file - the only channel
//    WeeklyTestApplication can read, since it runs before instrumentation
//    arguments are available (see CustomTestRunner.kt). The RevenueCat
//    customer is configured with it, so the purchase and the scans act on
//    the same balance.
const val WEEKLY_ACCESS_TOKEN_ARG = "weeklyAccessToken"

// The value for `name`, or a failure naming it: a missing token must stop the
// run here instead of sending an invalid one and reporting a misleading 401.
fun requireWeeklyArg(name: String, lookup: (String) -> String?): String {
    val value = lookup(name)
    check(!value.isNullOrBlank()) {
        "Instrumentation argument '$name' is missing - the External suite must be started by " +
            "test-weekly.ps1, which signs in the funded Supabase test user and passes it."
    }
    return value
}

fun weeklyAccessToken(): String =
    requireWeeklyArg(WEEKLY_ACCESS_TOKEN_ARG) { InstrumentationRegistry.getArguments().getString(it) }

fun weeklyAccountIdFromMarker(markerText: String): String {
    val accountId = markerText.trim()
    check(accountId.isNotEmpty()) {
        "The weekly marker file holds no account id - the External suite must be started by " +
            "test-weekly.ps1, which writes the funded Supabase test user's id into it."
    }
    return accountId
}
