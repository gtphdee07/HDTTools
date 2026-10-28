package com.rigcheck.app.ui.theme

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// The app icon, the splash screen and the bundled fonts are resources, which no screen test reaches. These read the
// resource files themselves, so a launcher icon that lost its themed (one-colour) layer, a splash that is not the
// design's teal, or a missing font file fails here without a device.
class ResourcesTest {

    private val res: File = generateSequence(File("").absoluteFile) { it.parentFile }
        .map { File(it, "src/main/res") }.first { it.isDirectory }

    private fun text(path: String): String = File(res, path).readText()

    private fun attr(xml: String, tag: String, name: String): String? =
        Regex("<$tag[^>]*android:$name=\"([^\"]*)\"").find(xml)?.groupValues?.get(1)

    private fun tealToken(): String {
        val tokens = generateSequence(File("").absoluteFile) { it.parentFile }
            .map { File(it, "docs/android-redesign/design-return/tokens.json") }.first { it.exists() }
        val brand = Json.parseToJsonElement(tokens.readText()).jsonObject.getValue("colors").jsonObject.getValue("brand").jsonArray
        return brand.map { it.jsonObject }.single { it.getValue("name").jsonPrimitive.content == "teal" }
            .getValue("hex").jsonPrimitive.content
    }

    @Test
    fun bothLauncherIconsHaveABackgroundAForegroundAndADistinctOneColourLayer() {
        for (file in listOf("mipmap-anydpi/ic_launcher.xml", "mipmap-anydpi/ic_launcher_round.xml")) {
            val xml = text(file)
            val background = attr(xml, "background", "drawable")
            val foreground = attr(xml, "foreground", "drawable")
            val monochrome = attr(xml, "monochrome", "drawable")
            assertEquals(file, "@drawable/ic_launcher_background", background)
            assertEquals(file, "@drawable/ic_launcher_foreground", foreground)
            // The themed icon is tinted by the launcher: pointing it at the colour layer would paint a flat blob.
            assertEquals(file, "@drawable/ic_launcher_monochrome", monochrome)
            assertNotEquals(file, foreground, monochrome)
        }
    }

    @Test
    fun theMonochromeLayerUsesOneColourOnly() {
        val colours = Regex("android:fillColor=\"(#[0-9A-Fa-f]+)\"").findAll(text("drawable/ic_launcher_monochrome.xml"))
            .map { it.groupValues[1].uppercase() }.toSet()
        assertEquals(setOf("#FF000000"), colours)
    }

    @Test
    fun theLauncherBackgroundIsTheSkyGradientOfTheDesign() {
        val stops = Regex("<item android:offset=\"(\\d)\" android:color=\"(#[0-9A-Fa-f]{8})\"").findAll(text("drawable/ic_launcher_background.xml"))
            .map { it.groupValues[1] to it.groupValues[2].uppercase() }.toList()
        assertEquals(listOf("0" to "#FF7B3FE4", "1" to "#FFFF7A1A"), stops)
        assertEquals(SkyGradientTop, DesignColors.getValue("purple"))
        assertEquals(SkyGradientBottom, DesignColors.getValue("orange"))
    }

    @Test
    fun theSplashScreenIsTheBrandTealWithTheMarkOnItsGradientDisc() {
        assertEquals(tealToken().uppercase(), "#" + text("values/colors.xml").let {
            Regex("<color name=\"splash_background\">#FF([0-9A-Fa-f]{6})</color>").find(it)!!.groupValues[1].uppercase()
        })
        for (file in listOf("values-v31/themes.xml")) {
            val xml = text(file)
            assertTrue(xml.contains("<item name=\"android:windowSplashScreenBackground\">@color/splash_background</item>"))
            assertTrue(xml.contains("<item name=\"android:windowSplashScreenAnimatedIcon\">@drawable/ic_splash_icon</item>"))
        }
        // Android 8 to 11 have no splash attributes: the window background is the splash there.
        assertTrue(text("values/themes.xml").contains("<item name=\"android:windowBackground\">@drawable/splash_window_background</item>"))
        assertTrue(text("drawable/splash_window_background.xml").contains("@drawable/ic_splash_icon"))
        val splash = text("drawable/ic_splash_icon.xml")
        assertTrue("the splash icon carries the gradient disc", splash.contains("#FF7B3FE4") && splash.contains("#FFFF7A1A"))
        assertTrue("the splash icon carries the mark", splash.contains("M54,24L78,64L30,64Z"))
    }

    @Test
    fun theBundledFontFilesAreThereForBothFamilies() {
        for (file in listOf("font/outfit_variable.ttf", "font/dm_sans_variable.ttf")) {
            val font = File(res, file)
            assertTrue("$file is missing", font.isFile)
            // A TrueType file starts with the version 1.0 tag.
            val header = font.inputStream().use { stream -> ByteArray(4).also { stream.read(it) } }
            assertEquals(listOf<Byte>(0, 1, 0, 0), header.toList())
        }
        assertTrue("the licences ship with the fonts", File(res.parentFile.parentFile.parentFile.parentFile, "font-licenses/Outfit-OFL.txt").isFile)
    }
}
