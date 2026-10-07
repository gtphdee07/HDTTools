package com.rigcheck.app.testsupport

// The scan service (#21) charges the account named by a signed-in user's
// access token, so the External suite's real scans need a real token for a
// funded Supabase test user. That wiring (sign the test user in from
// test-weekly.ps1's credentials, and make the RevenueCat customer the
// weekly suite buys against the same account id) is not built yet, so
// these tests fail loudly here instead of sending an invalid token and
// reporting a misleading 401. Replace the body when it is.
fun weeklyAccessToken(): String = error(
    "The Android External suite has no Supabase test-account token yet - its real scans cannot be " +
        "authenticated. See the #22 follow-up on wiring test-weekly.ps1 to a funded test user.",
)
