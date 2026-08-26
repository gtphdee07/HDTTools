package com.rigcheck.app.testsupport

import android.content.res.AssetManager

// The real adapter ScanFixturePool.discover()/resolveRandom() use in the
// actual instrumented tests - a thin wrapper over AssetManager, exercised
// for real only there. ScanFixturePoolTest.kt tests the discovery logic
// itself against a fake in-memory FixtureFileSource instead.
class AssetFixtureFileSource(private val assets: AssetManager) : FixtureFileSource {
    override fun list(path: String): List<String> = assets.list(path)?.toList() ?: emptyList()
    override fun readText(path: String): String = assets.open(path).bufferedReader().use { it.readText() }
}
