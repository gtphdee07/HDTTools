package com.rigcheck.app.testsupport

// Tags an instrumented test class with the External-suite surface it checks
// (ADR-0008: "annotation for Android"). Two readers depend on the exact
// spelling `@ExternalSurface("<surface name from the manifest>")`:
//  - android/test-external.ps1 -> scripts/external_wrapper.py looks for the tag
//    text to refuse a stale surface that has no tests;
//  - scripts/run_external_android.py reads the same text to pick the classes of
//    the stale surfaces and to write each surface's results.
// build.gradle.kts keeps every tagged class out of connectedDebugAndroidTest
// (notAnnotation): they need the marker file and a real network.
@Target(AnnotationTarget.CLASS)
@Retention(AnnotationRetention.RUNTIME)
annotation class ExternalSurface(val name: String)
