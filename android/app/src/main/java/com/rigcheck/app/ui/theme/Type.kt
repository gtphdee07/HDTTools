package com.rigcheck.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.unit.sp
import com.rigcheck.app.R

// Fetched at runtime via the Downloadable Fonts API rather than bundled as
// .ttf files - both are open Google Fonts, so this avoids a licensing/
// bundling question. Requires res/values/font_certs.xml (verbatim from
// Google's own sample, see that file's comment).
private val GoogleFontsProvider = GoogleFont.Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = R.array.com_google_android_gms_fonts_certs,
)

private val QuicksandFont = GoogleFont("Quicksand")
private val KarlaFont = GoogleFont("Karla")

// Ported from web/src/design-system/tokens.css: Quicksand (headings/
// display, weight 600-700), Karla (body text).
val QuicksandFamily = FontFamily(
    Font(googleFont = QuicksandFont, fontProvider = GoogleFontsProvider, weight = FontWeight.Medium),
    Font(googleFont = QuicksandFont, fontProvider = GoogleFontsProvider, weight = FontWeight.SemiBold),
    Font(googleFont = QuicksandFont, fontProvider = GoogleFontsProvider, weight = FontWeight.Bold),
)

val KarlaFamily = FontFamily(
    Font(googleFont = KarlaFont, fontProvider = GoogleFontsProvider, weight = FontWeight.Normal),
    Font(googleFont = KarlaFont, fontProvider = GoogleFontsProvider, weight = FontWeight.Medium),
    Font(googleFont = KarlaFont, fontProvider = GoogleFontsProvider, weight = FontWeight.Bold),
)

val Typography = Typography(
    displayLarge = TextStyle(fontFamily = QuicksandFamily, fontWeight = FontWeight.Bold, fontSize = 45.sp, lineHeight = 52.sp),
    headlineLarge = TextStyle(fontFamily = QuicksandFamily, fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 40.sp),
    headlineMedium = TextStyle(fontFamily = QuicksandFamily, fontWeight = FontWeight.Bold, fontSize = 28.sp, lineHeight = 36.sp),
    titleLarge = TextStyle(fontFamily = QuicksandFamily, fontWeight = FontWeight.SemiBold, fontSize = 22.sp, lineHeight = 28.sp),
    titleMedium = TextStyle(fontFamily = QuicksandFamily, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 24.sp),
    titleSmall = TextStyle(fontFamily = QuicksandFamily, fontWeight = FontWeight.Medium, fontSize = 16.sp, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontFamily = KarlaFamily, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp, letterSpacing = 0.15.sp),
    bodyMedium = TextStyle(fontFamily = KarlaFamily, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp, letterSpacing = 0.25.sp),
    bodySmall = TextStyle(fontFamily = KarlaFamily, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.4.sp),
    labelLarge = TextStyle(fontFamily = KarlaFamily, fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 20.sp, letterSpacing = 0.1.sp),
    labelMedium = TextStyle(fontFamily = KarlaFamily, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.5.sp),
    labelSmall = TextStyle(fontFamily = KarlaFamily, fontWeight = FontWeight.Medium, fontSize = 11.sp, lineHeight = 16.sp, letterSpacing = 0.5.sp),
)
