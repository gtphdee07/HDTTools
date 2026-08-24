import java.util.Properties

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

// An idle/sleeping emulator screen makes instrumented Compose tests fail
// with a misleading "No compose hierarchies found in the app" error
// instead of a clear one (see ARCHIVE_TESTING.md) - this has caused real
// flakiness on ./gradlew connectedDebugAndroidTest runs.
// test-weekly.ps1 has its own explicit wake step since it drives `adb`
// directly, but a raw connectedDebugAndroidTest invocation (no wrapper
// script) had no such protection - wired in as a task dependency instead
// so it's automatic regardless of how the Daily tier gets invoked.
val adbExecutable: File = run {
    val sdkDir = System.getenv("ANDROID_SDK_ROOT")
        ?: System.getenv("ANDROID_HOME")
        ?: run {
            val localProperties = File(rootDir, "local.properties")
            val props = Properties()
            if (localProperties.exists()) {
                localProperties.inputStream().use { props.load(it) }
            }
            props.getProperty("sdk.dir")
                ?: throw GradleException(
                    "Can't resolve the Android SDK dir for wakeEmulatorForInstrumentedTests - " +
                        "set ANDROID_SDK_ROOT/ANDROID_HOME or ensure android/local.properties has sdk.dir.",
                )
        }
    val candidate = File(sdkDir, "platform-tools/adb.exe")
    if (candidate.exists()) candidate else File(sdkDir, "platform-tools/adb")
}

// Exec (not a doLast { project.exec {...} } block) - the latter isn't
// configuration-cache compatible, since task actions can't safely close
// over `project`. A single adb shell invocation runs both commands
// (adb shell concatenates every argument after "shell" with spaces into
// one remote command line), so one Exec task is enough.
tasks.register<Exec>("wakeEmulatorForInstrumentedTests") {
    commandLine(
        adbExecutable.path, "shell",
        "input", "keyevent", "KEYCODE_WAKEUP;",
        "svc", "power", "stayon", "true",
    )
}

afterEvaluate {
    tasks.findByName("connectedDebugAndroidTest")?.dependsOn("wakeEmulatorForInstrumentedTests")
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