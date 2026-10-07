package com.rigcheck.app.data

import android.app.Activity
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import java.security.MessageDigest
import java.security.SecureRandom

// The OAuth *Web application* client id from the Google Cloud project that
// Supabase's Google provider is configured with (not the Android client id).
// Public by design, like the other client config. Blank until the owner
// creates it - scripts/wizard_android_sign_in.sh walks through that.
internal const val GOOGLE_WEB_CLIENT_ID = ""

class GoogleSignInCancelled : Exception("Google sign-in was cancelled")
class GoogleAccountMissing : Exception("No Google account is set up on this device.")

class GoogleNonce private constructor(val raw: String, val hashed: String) {
    companion object {
        fun create(): GoogleNonce {
            val bytes = ByteArray(32).also { SecureRandom().nextBytes(it) }
            val raw = bytes.toHex()
            val hashed = MessageDigest.getInstance("SHA-256").digest(raw.toByteArray()).toHex()
            return GoogleNonce(raw, hashed)
        }

        private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
    }
}

class GoogleIdentity(val idToken: String, val rawNonce: String)

// null = the user backed out, which needs no message.
fun googleFailureMessage(error: Throwable): String? = when (error) {
    is GoogleSignInCancelled -> null
    else -> error.message ?: "Google sign-in failed."
}

// Asks Android's Credential Manager for a Google ID token. Needs an
// Activity because it shows the account chooser.
suspend fun requestGoogleIdentity(activity: Activity): GoogleIdentity {
    check(GOOGLE_WEB_CLIENT_ID.isNotBlank()) { "Google sign-in isn't set up yet." }
    val nonce = GoogleNonce.create()
    val option = GetGoogleIdOption.Builder()
        .setFilterByAuthorizedAccounts(false)
        .setServerClientId(GOOGLE_WEB_CLIENT_ID)
        .setNonce(nonce.hashed)
        .build()
    val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
    val credential = try {
        CredentialManager.create(activity).getCredential(activity, request).credential
    } catch (_: GetCredentialCancellationException) {
        throw GoogleSignInCancelled()
    } catch (_: NoCredentialException) {
        throw GoogleAccountMissing()
    }
    check(credential is CustomCredential && credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
        "Google returned an unexpected credential."
    }
    return GoogleIdentity(GoogleIdTokenCredential.createFrom(credential.data).idToken, nonce.raw)
}
