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

// RevenueCat public SDK key per build type (#166). It is public (extractable from any APK), so this is a
// release-process guard, not a secret: the Test Store key ("test_...") makes purchases fake, so a release
// built with it would sell nothing and grant entitlements for free. Debug uses the Test Store key (the
// RevenueCat dashboard's "Install the SDK" screen). Release reads the production key from the Gradle
// property revenueCatReleaseKey or the environment variable REVENUECAT_RELEASE_API_KEY, with no default.
val revenueCatTestStoreKey = "test_LFhGCYRgSfTFUpYRaWkEakLWOdS"
val revenueCatReleaseKey: String =
    providers.gradleProperty("revenueCatReleaseKey")
        .orElse(providers.environmentVariable("REVENUECAT_RELEASE_API_KEY"))
        .getOrElse("")
        .trim()

// Beta signing (#174): three values from Gradle properties (the owner's user-level gradle.properties) or
// environment variables, with no defaults. The file is PKCS12, so the store and key passwords are one value.
fun betaSetting(property: String, environment: String): String =
    providers.gradleProperty(property).orElse(providers.environmentVariable(environment)).getOrElse("").trim()

val betaKeystoreFile = betaSetting("betaKeystoreFile", "BETA_KEYSTORE_FILE")
val betaKeyAlias = betaSetting("betaKeyAlias", "BETA_KEY_ALIAS")
val betaKeystorePassword = betaSetting("betaKeystorePassword", "BETA_KEYSTORE_PASSWORD")
// Raised by hand for each beta APK that is sent out; a build that does not set it gets 1.
val appVersionCode: Int = providers.gradleProperty("appVersionCode").map { it.trim().toInt() }.getOrElse(1)

android {
    namespace = "com.rigcheck.app"
    compileSdk {
        version = release(37)
    }

    // The beta signing config (#174). The values come from outside the repo. A blank value is accepted here
    // (so a build that never packages a beta APK needs none of them) and verifyBetaSigning refuses a beta
    // build that lacks one. storeFile is left unset when the path is blank, never given a default.
    signingConfigs {
        create("beta") {
            if (betaKeystoreFile.isNotBlank()) storeFile = file(betaKeystoreFile)
            keyAlias = betaKeyAlias
            storePassword = betaKeystorePassword
            keyPassword = betaKeystorePassword
            // minSdk 26 would sign with v2 only; `keytool -printcert -jarfile <apk>`, which the owner uses to
            // check the key, reads only the v1 (JAR) signature.
            enableV1Signing = true
        }
    }

    defaultConfig {
        applicationId = "com.rigcheck.app"
        minSdk = 26
        targetSdk = 37
        // Testers update in place only if versionCode rises with each APK (#174): raise the Gradle
        // property appVersionCode by hand before building the next beta APK.
        versionCode = appVersionCode
        versionName = "1.0"
        buildConfigField("boolean", "IS_BETA", "false")

        testInstrumentationRunner = "com.rigcheck.app.CustomTestRunner"

        // PaywallScreenWeeklyTest needs real network + the funded test
        // account (marker file and -e weeklyAccessToken, only test-weekly.ps1
        // supplies them) and would
        // otherwise be picked up by ./gradlew connectedDebugAndroidTest's
        // unfiltered run too, since JUnit discovers every @Test class in
        // the androidTest source set regardless of which tier "owns" it -
        // confirmed hands-on 2026-08-23 when the Daily tier's run tried to
        // execute it. testInstrumentationRunnerArguments only applies to
        // Gradle-invoked runs (test-weekly.ps1's raw `adb shell am
        // instrument` is unaffected), so this excludes it from Daily only.
        testInstrumentationRunnerArguments["notClass"] = "com.rigcheck.app.ui.screens.PaywallScreenWeeklyTest"
        // The same for every per-surface External class (#39): the ones tagged
        // @ExternalSurface need the marker file and a real network, which only
        // android/test-external.ps1 sets up.
        testInstrumentationRunnerArguments["notAnnotation"] = "com.rigcheck.app.testsupport.ExternalSurface"
    }

    buildTypes {
        debug {
            testCoverage {
                enableUnitTestCoverage = true
                enableAndroidTestCoverage = true
            }
            buildConfigField("String", "REVENUECAT_PUBLIC_API_KEY", "\"$revenueCatTestStoreKey\"")
        }
        release {
            optimization {
                enable = false
            }
            // No default: an unset key is "" here and verifyRevenueCatReleaseKey fails the build (#166).
            buildConfigField("String", "REVENUECAT_PUBLIC_API_KEY", "\"$revenueCatReleaseKey\"")
        }
        // The APK sent to beta testers (#174): signed with the owner's upload key, not debuggable, and the
        // only non-debug build allowed the Test Store key (beta uses test payments). It keeps the release
        // package name, so Google sign-in works on it, and so a debug build cannot be updated by it.
        create("beta") {
            initWith(getByName("release"))
            isDebuggable = false
            signingConfig = signingConfigs.getByName("beta")
            versionNameSuffix = "-beta"
            buildConfigField("String", "REVENUECAT_PUBLIC_API_KEY", "\"$revenueCatTestStoreKey\"")
            buildConfigField("boolean", "IS_BETA", "true")
        }
    }

    // Beta is only ever packaged: no unit-test or device-test variant of it.
    androidComponents {
        beforeVariants(selector().withBuildType("beta")) { variant ->
            variant.hostTests[com.android.build.api.variant.HostTestBuilder.UNIT_TEST_TYPE]?.enable = false
            variant.androidTest.enable = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        buildConfig = true
        compose = true
    }
}

// The release guard (#166). The rule is inline in doLast, not a script function: a task action that calls a build-script function
// captures the script object, which the configuration cache (on in gradle.properties) cannot serialize.
// The message names the key and where to set it but never prints its value.
val verifyRevenueCatReleaseKey = tasks.register("verifyRevenueCatReleaseKey") {
    group = "verification"
    description = "Fails unless the release RevenueCat public key is set and is not a Test Store (test_) key."
    val key = revenueCatReleaseKey
    // No declared outputs, so Gradle never treats this task as up to date: it checks the key on every build.
    doLast {
        val where = "Gradle property revenueCatReleaseKey or environment variable REVENUECAT_RELEASE_API_KEY"
        if (key.isBlank()) {
            throw GradleException(
                "The RevenueCat release API key is missing: set the $where to the production public SDK key.",
            )
        }
        if (key.startsWith("test_", ignoreCase = true)) {
            throw GradleException(
                "The RevenueCat release API key is a Test Store key (it starts with test_): purchases made " +
                    "with it are fake. Set the $where to the production public SDK key.",
            )
        }
    }
}

// The tasks that produce a shippable APK or bundle. Not preReleaseBuild: that would also fail
// testReleaseUnitTest, which a plain ./gradlew test runs without any release key.
tasks.matching {
    it.name in setOf("assembleRelease", "bundleRelease", "packageRelease", "packageReleaseBundle")
}.configureEach {
    dependsOn(verifyRevenueCatReleaseKey)
}
// And run first, so a bad key fails the build in seconds, not after the release variant has compiled.
// mustRunAfter only orders the two when both are in the graph, so it does not pull the guard into
// testReleaseUnitTest (which also depends on preReleaseBuild).
tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    mustRunAfter(verifyRevenueCatReleaseKey)
}

// The beta signing guard (#174): same shape and same reasons as the release guard above (inline in doLast,
// no declared outputs). It names each missing setting's property and variable, and never prints a value.
val verifyBetaSigning = tasks.register("verifyBetaSigning") {
    group = "verification"
    description = "Fails unless the beta keystore path, key alias and password are all set."
    val settings = mapOf(
        "betaKeystoreFile (or BETA_KEYSTORE_FILE)" to betaKeystoreFile,
        "betaKeyAlias (or BETA_KEY_ALIAS)" to betaKeyAlias,
        "betaKeystorePassword (or BETA_KEYSTORE_PASSWORD)" to betaKeystorePassword,
    )
    doLast {
        val missing = settings.filterValues { it.isBlank() }.keys
        if (missing.isNotEmpty()) {
            throw GradleException(
                "The beta signing settings are missing: set the Gradle property (in your user-level " +
                    "gradle.properties) or environment variable for ${missing.joinToString(", ")}.",
            )
        }
    }
}
tasks.matching {
    it.name in setOf("assembleBeta", "bundleBeta", "packageBeta", "packageBetaBundle")
}.configureEach {
    dependsOn(verifyBetaSigning)
}
tasks.matching { it.name == "preBetaBuild" }.configureEach {
    mustRunAfter(verifyBetaSigning)
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

// The unit tests read the shared fixtures in test-vectors/ by path at run
// time, so Gradle does not know a changed fixture matters: without this,
// editing one leaves testDebugUnitTest "UP-TO-DATE" and the tests that check
// the app against it do not run (found while checking that
// ScanOutcomesFixtureTest fails when a row disagrees).
tasks.withType<Test>().configureEach {
    inputs.dir(rootProject.layout.projectDirectory.dir("../test-vectors"))
        .withPropertyName("sharedTestVectors")
        .withPathSensitivity(PathSensitivity.RELATIVE)
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
    // Shared account (#22): Supabase Auth over Ktor's OkHttp engine, with
    // Google sign-in through Credential Manager. Postgrest reads and writes the
    // account's Garage (#31).
    implementation(libs.supabase.auth)
    implementation(libs.supabase.postgrest)
    implementation(libs.ktor.client.okhttp)
    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play.services.auth)
    implementation(libs.google.googleid)
    // Camera-overlay spike (ClaudePlans/2026-08-27-android-camera-overlay-spike.md)
    // - isolated proof-of-concept only, not wired into production navigation.
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)
    implementation(libs.androidx.exifinterface)
    testImplementation(libs.junit)
    testImplementation(libs.mockk)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.ktor.client.mock)
    testImplementation(libs.kotlinx.coroutines.test)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.uiautomator)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}