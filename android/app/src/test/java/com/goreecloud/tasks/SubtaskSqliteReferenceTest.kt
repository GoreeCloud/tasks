package com.goreecloud.tasks

import android.database.sqlite.SQLiteDatabase
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class SubtaskSqliteReferenceTest {
    private lateinit var db: SQLiteDatabase
    private lateinit var repo: SubtaskSqliteReference
    private val deletionTime = "2026-11-02T14:00:00Z"
    private fun fixture() = JSONObject(String(PortableFixture.read("schema4-proposed-synthetic.json")))
    @Before fun setUp() {
        db = SQLiteDatabase.create(null)
        repo = SubtaskSqliteReference(db)
        repo.seed(fixture())
    }
    @After fun tearDown() { db.close() }

    @Test fun rejectsFileBackedDatabasesBeforeCreatingReferenceTables() {
        val path = java.io.File.createTempFile("tasks-subtree-reference-", ".sqlite")
        val disk = SQLiteDatabase.openOrCreateDatabase(path, null)
        try {
            try {
                SubtaskSqliteReference(disk)
                fail("Reference accepted a persistent database")
            } catch (_: IllegalArgumentException) { }
            val count = disk.rawQuery(
                "SELECT count(*) FROM sqlite_master WHERE name LIKE 'proposed_%'", null
            ).use { it.moveToFirst(); it.getInt(0) }
            assertEquals(0, count)
        } finally {
            disk.close()
            path.delete()
        }
    }

    @Test fun fullGroupRoundTripRetainsExactMetadata() {
        val before = repo.workspace().toString()
        assertEquals(3, repo.deleteSubtree("task-notes", deletionTime, "whole").size)
        assertEquals(0, repo.workspace().getJSONArray("tasks").length())
        assertEquals(3, repo.trash().size)
        assertEquals(3, repo.restoreGroup("whole").size)
        assertEquals(before, repo.workspace().toString())
        assertTrue(repo.trash().isEmpty())
    }

    @Test fun childBranchDoesNotRemoveParent() {
        assertEquals(2, repo.deleteSubtree("task-empty-notes", deletionTime, "child").size)
        assertEquals(1, repo.workspace().getJSONArray("tasks").length())
        assertEquals("task-notes", repo.workspace().getJSONArray("tasks").getJSONObject(0).getString("id"))
        assertEquals(2, repo.restoreGroup("child").size)
        assertEquals(3, repo.workspace().getJSONArray("tasks").length())
    }

    @Test fun injectedMidDeletionFailureRollsBackAllRows() {
        db.execSQL("CREATE TRIGGER break_delete AFTER INSERT ON proposed_trash " +
            "WHEN NEW.id='task-grandchild' BEGIN SELECT RAISE(ABORT,'injected'); END")
        val before = repo.workspace().toString()
        try {
            repo.deleteSubtree("task-notes", deletionTime, "whole")
            fail("Mid-delete SQL exception was ignored")
        } catch (_: android.database.SQLException) { }
        assertEquals(before, repo.workspace().toString())
        assertTrue(repo.trash().isEmpty())
    }

    @Test fun injectedMidRestoreFailureRollsBackAllRows() {
        repo.deleteSubtree("task-notes", deletionTime, "whole")
        db.execSQL("CREATE TRIGGER break_restore AFTER INSERT ON proposed_tasks " +
            "WHEN NEW.id='task-grandchild' BEGIN SELECT RAISE(ABORT,'injected'); END")
        val before = repo.trash().map { it.toString() }
        try {
            repo.restoreGroup("whole")
            fail("Mid-restore SQL exception was ignored")
        } catch (_: android.database.SQLException) { }
        assertEquals(0, repo.workspace().getJSONArray("tasks").length())
        assertEquals(before, repo.trash().map { it.toString() })
    }
}
