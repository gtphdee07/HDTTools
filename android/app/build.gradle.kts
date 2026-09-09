import java.util.Properties
import org.gradle.testing.jacoco.tasks.JacocoReport

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.detekt)
    // Applied fresh for jacocoMergedCoverageReport below - AGP's own
    // testCoverage block (in the android {} section) only wires its own
    // internal createDebugAndroidTestCoverageReport task
    // (com.android.build.gradle.internal.coverage.JacocoReportTask,
    // confirmed via `./gradlew :app:help --task
    // createDebugAndroidTestCoverageReport`, 2026-09-09), which is not a
    // hook point for a second execution-data input. The plain Gradle
    // `jacoco` plugin's own JacocoReport task type is.
    id("jacoco")
}

// Matches the JaCoCo version already resolved for this Gradle version
// (confirmed present in GradleUserHome's module cache, 2026-09-09) -
// pinned explicitly so the merged report task and AGP's own
// AGP-bundled JaCoCo agent (which wrote both .ec files) never drift to
// different toolVersions, which JaCoCo's execution-data format is not
// guaranteed to merge cleanly across.
jacoco {
    toolVersion = "0.8.14"
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

// Dead-code sweep (roadmap item #10) - scoped narrow to the
// private-visibility rules the sweep actually needs, not a general lint
// adoption. Requires the Gradle daemon's own JVM to be JDK <=22 (see
// DEV_ENVIRONMENT.md's detekt gotcha) - detekt's analysis runs in-process
// in that JVM, so nothing set here can redirect it.
detekt {
    buildUponDefaultConfig = false
    config.setFrom(files("$projectDir/detekt.yml"))
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

// Merges Major's (connectedDebugAndroidTest) coverage.ec with External's
// (PaywallScreenWeeklyTest, run via ../test-weekly.ps1 and pulled
// separately - see that script) into one combined, informational report -
// roadmap item #8's follow-up
// (ClaudePlans/2026-09-09-merge-external-tier-coverage-paywallscreen.md).
// Never gates the release; scripts/coverage_gate.py's
// get_android_merged_result() reads this task's own report and returns it
// as a PlatformResult(gated=False).
//
// classDirectories/sourceDirectories below were picked by direct
// inspection, not assumption (2026-09-09): this app module is pure Kotlin
// (no app/src/main/*.java, no app/build/intermediates/javac output), and
// comparing class bytes confirmed
// app/build/intermediates/built_in_kotlinc/debug/compileDebugKotlin/classes
// holds the plain (non-instrumented) compiled classes JacocoReport expects
// as its classDirectories input, while
// app/build/intermediates/classes/debug/jacocoDebug/dirs holds a *jacoco-
// instrumented* copy (contains the literal string "jacoco" in its
// bytecode; the plain compileDebugKotlin one doesn't) - that instrumented
// copy is what actually gets dexed and run on-device, not something
// JacocoReport should be pointed at for report generation.
val externalCoverageEc: String =
    (project.findProperty("externalCoverageEc") as String?)
        ?: "build/outputs/code_coverage/debugAndroidTest/external/coverage-external.ec"

tasks.register<JacocoReport>("jacocoMergedCoverageReport") {
    group = "verification"
    description = "Merges Major's + External's coverage.ec files into one " +
        "combined, report-only JaCoCo report."

    // fileTree (not a hardcoded "medium_phone(AVD) - 16" path) so this
    // doesn't silently go stale if this machine's AVD is ever renamed or
    // recreated under a different device-folder name.
    val majorEc = fileTree("build/outputs/code_coverage/debugAndroidTest/connected") {
        include("**/coverage.ec")
    }
    val externalEc = files(externalCoverageEc).filter { it.exists() }

    executionData.setFrom(majorEc, externalEc)
    classDirectories.setFrom(
        files("build/intermediates/built_in_kotlinc/debug/compileDebugKotlin/classes"),
    )
    sourceDirectories.setFrom(files("src/main/java"))

    reports {
        html.required.set(true)
        html.outputLocation.set(layout.buildDirectory.dir("reports/coverage/androidTest/debug/merged"))
        xml.required.set(false)
        csv.required.set(false)
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
    // Camera-overlay spike (ClaudePlans/2026-08-27-android-camera-overlay-spike.md)
    // - isolated proof-of-concept only, not wired into production navigation.
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)
    implementation(libs.androidx.exifinterface)
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