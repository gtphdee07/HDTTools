package com.rigcheck.app.data

import androidx.datastore.core.DataStore
import androidx.datastore.core.okio.OkioStorage
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.PreferencesSerializer
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import okio.FileSystem
import okio.Path.Companion.toOkioPath
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

// Saved Rigs through a real Preferences DataStore on a temporary folder: no
// device, no Robolectric. DataStore's Okio storage is used rather than its
// default file storage, whose second write fails on Windows ("Unable to rename
// ...tmp"; in unit tests its Android build moves the file with File.renameTo
// because Build.VERSION.SDK_INT is 0). The stored JSON is written straight into the store
// where a test needs "a Rig saved by an older (or newer) app".
class RecentRigsRepositoryTest {
    @get:Rule
    val folder = TemporaryFolder()

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val storedKey = stringPreferencesKey("recent_rigs")

    private lateinit var dataStore: DataStore<Preferences>
    private lateinit var repository: RecentRigsRepository

    @Before
    fun setUp() {
        val path = folder.root.resolve("rigcheck_prefs.preferences_pb").toOkioPath()
        dataStore = PreferenceDataStoreFactory.create(
            storage = OkioStorage(FileSystem.SYSTEM, PreferencesSerializer) { path },
            scope = scope,
        )
        repository = RecentRigsRepository(dataStore)
    }

    @After
    fun tearDown() {
        scope.cancel()
    }

    private suspend fun store(json: String) = dataStore.edit { it[storedKey] = json }

    private val truck = TruckTag(name = "F-350", gvwrLb = 11_500.0, frontGawrLb = 5_500.0, rearGawrLb = 6_500.0)
    private val trailer = TrailerTag(name = "Fifth wheel", gvwrLb = 14_000.0, gawrPerAxleLb = 7_000.0, axleCount = 2)

    @Test
    fun aSavedRigLoadsBackEqual() = runTest {
        val saved = repository.saveRecentRig("Weekender", truck, trailer)

        val loaded = repository.recentRigs.first()

        assertEquals(saved, loaded)
        assertEquals(listOf(RecentRig("Weekender", truck, trailer, loaded[0].lastUsedAt)), loaded)
    }

    @Test
    fun nothingSavedLoadsAsAnEmptyList() = runTest {
        assertEquals(emptyList<RecentRig>(), repository.recentRigs.first())
    }

    @Test
    fun rigsComeBackMostRecentFirstAndCappedAtFive() = runTest {
        (1..7).forEach { repository.saveRecentRig("Rig $it", truck, trailer) }

        val names = repository.recentRigs.first().map { it.nickname }

        assertEquals(listOf("Rig 7", "Rig 6", "Rig 5", "Rig 4", "Rig 3"), names)
    }

    @Test
    fun theSavedListReturnedMatchesWhatIsStored() = runTest {
        (1..6).forEach { repository.saveRecentRig("Rig $it", truck, trailer) }

        val returned = repository.saveRecentRig("Rig 7", truck, trailer)

        assertEquals(repository.recentRigs.first(), returned)
        assertEquals(5, returned.size)
    }

    @Test
    fun aNicknameInAnotherLetterCaseReplacesTheOldEntry() = runTest {
        repository.saveRecentRig("Weekender", truck, trailer)
        repository.saveRecentRig("Other", truck, trailer)

        val otherTrailer = TrailerTag(name = "Bumper pull")
        repository.saveRecentRig("WEEKENDER", truck, otherTrailer)

        val loaded = repository.recentRigs.first()
        assertEquals(listOf("WEEKENDER", "Other"), loaded.map { it.nickname })
        assertEquals(otherTrailer, loaded[0].trailer)
    }

    @Test
    fun aStoredRigMissingAFieldTheModelDefaultsLoadsWithTheDefault() = runTest {
        // Neither Rig has the truck's standaloneWeightLb or the trailer's uvwLb,
        // which stand in for a field added after the Rig was saved.
        store(
            """
            [
              {"nickname":"Old","truck":{"name":"F-350","gvwrLb":11500.0},
               "trailer":{"name":"Fifth wheel","axleCount":2},"lastUsedAt":"2026-01-01T00:00:00Z"},
              {"nickname":"Older","truck":{},"trailer":{"name":"Pop-up"},"lastUsedAt":"2025-01-01T00:00:00Z"}
            ]
            """.trimIndent(),
        )

        val loaded = repository.recentRigs.first()

        assertEquals(listOf("Old", "Older"), loaded.map { it.nickname })
        assertEquals(TruckTag(name = "F-350", gvwrLb = 11_500.0), loaded[0].truck)
        assertNull(loaded[0].truck.standaloneWeightLb)
        assertEquals(TrailerTag(name = "Fifth wheel", axleCount = 2), loaded[0].trailer)
        assertEquals(TruckTag(), loaded[1].truck)
    }

    @Test
    fun aStoredRigWithAnUnknownExtraFieldLoadsIgnoringIt() = runTest {
        store(
            """
            [
              {"nickname":"Newer","truck":{"name":"F-350","gcwrLb":24000.0},
               "trailer":{"name":"Fifth wheel"},"lastUsedAt":"2026-01-01T00:00:00Z","color":"blue"}
            ]
            """.trimIndent(),
        )

        val loaded = repository.recentRigs.first()

        assertEquals(
            listOf(RecentRig("Newer", TruckTag(name = "F-350"), TrailerTag(name = "Fifth wheel"), "2026-01-01T00:00:00Z")),
            loaded,
        )
    }

    @Test
    fun corruptStoredJsonLoadsAsAnEmptyList() = runTest {
        store("{not json")

        assertEquals(emptyList<RecentRig>(), repository.recentRigs.first())
    }

    @Test
    fun savingOverCorruptStoredJsonStartsAFreshList() = runTest {
        store("{not json")

        val saved = repository.saveRecentRig("Weekender", truck, trailer)

        assertEquals(listOf("Weekender"), saved.map { it.nickname })
        assertEquals(saved, repository.recentRigs.first())
    }
}
