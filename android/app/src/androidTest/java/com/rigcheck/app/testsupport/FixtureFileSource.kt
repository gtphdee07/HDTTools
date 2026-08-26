package com.rigcheck.app.testsupport

// Abstracts "list files under a path" / "read a file's text" so
// ScanFixturePool's discovery logic can be unit-tested against a fake,
// in-memory implementation (ScanFixturePoolTest.kt) without needing a
// real device/AssetManager - only AssetFixtureFileSource, the thin real
// adapter used by the actual instrumented tests, touches AssetManager.
interface FixtureFileSource {
    fun list(path: String): List<String>
    fun readText(path: String): String
}
