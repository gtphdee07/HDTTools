plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "com.rigcheck.app"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.rigcheck.app"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "com.rigcheck.app.CustomTestRunner"

        // PaywallScreenWeeklyTest needs real network + weekly-test-user
        // (via -e weekly true, only test-weekly.ps1 passes it) and would
        // otherwise be picked up by ./gradlew connectedDebugAndroidTest's
        // unfiltered run too, since JUnit discovers every @Test class in
        // the androidTest source set regardless of which tier "owns" it -
        // confirmed hands-on 2026-08-23 when the Daily tier's run tried to
        // execute it. testInstrumentationRunnerArguments only applies to
        // Gradle-invoked runs (test-weekly.ps1's raw `adb shell am
        // instrument` is unaffected), so this excludes it from Daily only.
        testInstrumentationRunnerArguments["notClass"] = "com.rigcheck.app.ui.screens.PaywallScreenWeeklyTest"
    }

    buildTypes {
        debug {
            testCoverage {
                enableUnitTestCoverage = true
                enableAndroidTestCoverage = true
            }
        }
        release {
            optimization {
                enable = false
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.androidx.compose.ui.text.google.fonts)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.revenuecat.purchases)
    implementation(libs.okhttp)
    testImplementation(libs.junit)
    testImplementation(libs.mockk)
    testImplementation(libs.kotlinx.coroutines.test)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.uiautomator)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}