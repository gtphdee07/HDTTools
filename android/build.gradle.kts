// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.detekt) apply false
}

// detekt's default source set leaves out src/androidTest (#150): an unused private member in an instrumented
// test was never reported. Added here, not in app/build.gradle.kts, because that file pins the
// revenuecat-android-sdk External surface and an edit to it would mark the surface stale.
subprojects {
    pluginManager.withPlugin("io.gitlab.arturbosch.detekt") {
        extensions.configure<io.gitlab.arturbosch.detekt.extensions.DetektExtension> {
            source.from("src/androidTest/java")
        }
    }
}