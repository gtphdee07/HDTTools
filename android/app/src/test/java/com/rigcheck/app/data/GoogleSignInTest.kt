package com.rigcheck.app.data

import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Supabase checks a Google ID token against the *raw* nonce, but Google
// must be given its SHA-256 (hex) - getting either side wrong makes every
// Google sign-in fail with a nonce mismatch that only shows up live.
class GoogleSignInTest {

    private fun sha256Hex(text: String): String =
        MessageDigest.getInstance("SHA-256").digest(text.toByteArray()).joinToString("") { "%02x".format(it) }

    @Test
    fun `the hashed nonce is the SHA-256 hex of the raw nonce`() {
        val nonce = GoogleNonce.create()

        assertEquals(sha256Hex(nonce.raw), nonce.hashed)
    }

    @Test
    fun `each sign-in gets a fresh unguessable nonce`() {
        val first = GoogleNonce.create()
        val second = GoogleNonce.create()

        assertNotEquals(first.raw, second.raw)
        assertTrue(first.raw.length >= 32)
    }

    @Test
    fun `a cancelled or missing Google account maps to a plain explanation, not a stack trace`() {
        assertEquals(
            null,
            googleFailureMessage(GoogleSignInCancelled()),
        )
        assertEquals(
            "No Google account is set up on this device.",
            googleFailureMessage(GoogleAccountMissing()),
        )
        assertEquals("boom", googleFailureMessage(IllegalStateException("boom")))
    }
}
