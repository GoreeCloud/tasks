package com.goreecloud.tasks

import android.content.Context
import android.database.sqlite.SQLiteConstraintException
import android.database.sqlite.SQLiteDatabase
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

/**
 * Real SQLiteOpenHelper and SQLite transaction tests running under Robolectric.
 * Only a fresh test context is used; no actual device or user data is touched.
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class RestoreDatabaseTest {
    private lateinit var context: Context
    private lateinit var db: TasksDatabase

    @Before fun setUp() {
        context = RuntimeEnvironment.getApplication()
        context.deleteDatabase("goreecloud-tasks.db")
        db = TasksDatabase(context)
    }

    @After fun tearDown() {
        db.close()
        context.deleteDatabase("goreecloud-tasks.db")
    }

    private fun fixture() = """
        {
          "schema":1,
          "projects":[{"id":"project-1","name":"Delivery 🚀"}],
          "tasks":[
            {"id":"task-1","title":"Schedule release","priority":1,
             "completed":false,"due":"2026-11-09","projectId":"project-1",
             "createdAt":"2026-10-31T18:00:00.123456+00:00","completedAt":null},
            {"id":"task-2","title":"Review","priority":3,
             "completed":true,"due":"","projectId":null,
             "createdAt":"2026-10-29T09:00:00.000000+00:00",
             "completedAt":"2026-10-31T12:10:11.654321+00:00"}
          ]
        }
    """.trimIndent()

    private fun snapshot() = PortableRestore.parse(fixture().toByteArray(Charsets.UTF_8))

    private fun counts(): Pair<Long, Long> {
        val database = db.readableDatabase
        return android.database.DatabaseUtils.queryNumEntries(database, "tasks") to
            android.database.DatabaseUtils.queryNumEntries(database, "projects")
    }


    @Test fun atomicBulkActionsPreserveMetadataAndMoveToRecoverableTrash() {
        val source = snapshot()
        db.restorePortableBackup(source)
        assertEquals(2, db.bulkEdit(listOf("task-1", "task-2"), "complete"))
        val completed = PortableRestore.parse(db.exportPortableBackup()).tasks
        assertTrue(completed.all { it.completed })
        val existingTimestamp = completed.single { it.id == "task-2" }.completedAtExact
        db.bulkEdit(listOf("task-1", "task-2"), "complete")
        assertEquals(existingTimestamp, PortableRestore.parse(db.exportPortableBackup())
            .tasks.single { it.id == "task-2" }.completedAtExact)
        assertEquals(2, db.bulkEdit(listOf("task-1", "task-2"), "priority", "1"))
        assertTrue(db.listTasks().all { it.priority == 1 })
        db.bulkEdit(listOf("task-1", "task-2"), "project", "project-1")
        assertTrue(db.listTasks().all { it.projectId == "project-1" })
        db.bulkEdit(listOf("task-1", "task-2"), "project", null)
        db.bulkEdit(listOf("task-1", "task-2"), "reopen")
        assertTrue(db.listTasks().all { !it.completed && it.projectId == null })
        db.bulkEdit(listOf("task-1", "task-2"), "trash")
        assertTrue(db.listTasks().isEmpty())
        assertEquals(setOf("task-1", "task-2"), db.listDeletedTasks().map { it.id }.toSet())
        db.close()
        db = TasksDatabase(context)
        assertEquals(2, db.listDeletedTasks().size)
        assertTrue(db.restoreDeletedTask("task-1"))
        assertTrue(db.restoreDeletedTask("task-2"))
        assertEquals(2, db.listTasks().size)
    }

    @Test fun invalidBulkActionsAndCollisionsRollbackEveryRow() {
        db.restorePortableBackup(snapshot())
        val source = PortableRestore.parse(db.exportPortableBackup())
        val invalid = listOf(
            Triple(emptyList<String>(), "complete", null),
            Triple(listOf("task-1", "task-1"), "complete", null),
            Triple(listOf("task-1", "absent"), "complete", null),
            Triple(listOf("task-1", "task-2"), "priority", "9"),
            Triple(listOf("task-1", "task-2"), "project", "absent"),
            Triple(listOf("task-1", "task-2"), "unknown", null),
            Triple(listOf("task-1", "task-2"), "complete", "extra"),
            Triple(List(201) { "synthetic-$it" }, "complete", null)
        )
        for ((ids, action, value) in invalid) {
            try {
                db.bulkEdit(ids, action, value)
                throw AssertionError("Invalid batch was accepted: $action")
            } catch (_: IllegalArgumentException) { }
            assertEquals(source, PortableRestore.parse(db.exportPortableBackup()))
        }
        // An existing Trash ID for the second item triggers a mid-batch SQL
        // exception. The earlier transfer must be rolled back.
        db.writableDatabase.execSQL(
            "INSERT INTO deleted_tasks (id,title,priority,completed,created_at,deleted_at) " +
                "VALUES (?,?,?,?,?,?)",
            arrayOf("task-2", "Older Trash", 4, 0, System.currentTimeMillis(),
                System.currentTimeMillis())
        )
        try {
            db.bulkEdit(listOf("task-1", "task-2"), "trash")
            throw AssertionError("Trash collision was not detected")
        } catch (_: SQLiteConstraintException) { }
        assertEquals(source, PortableRestore.parse(db.exportPortableBackup()))
        assertEquals(listOf("task-2"), db.listDeletedTasks().map { it.id })
    }

    @Test fun sharedPortableFixtureRestoresAndExportsExactSourceMetadata() {
        val source = PortableRestore.parse(PortableFixture.read())
        db.restorePortableBackup(source)
        assertEquals(3L to 2L, counts())
        val exported = PortableRestore.parse(db.exportPortableBackup())
        assertEquals(source.projects.sortedBy { it.id }, exported.projects.sortedBy { it.id })
        assertEquals(source.tasks.sortedBy { it.id }, exported.tasks.sortedBy { it.id })
        val completed = exported.tasks.single { it.id == "task-completed" }
        assertEquals("2026-11-01T01:23:45.654321Z", completed.completedAtExact)
        assertEquals("2026-10-31T20:15:42.123456-05:00", completed.createdAtExact)
    }

    @Test fun emptyStoreRestoreThenExportRetainsExactPortableFields() {
        assertTrue(db.isEmptyForRestore())
        db.restorePortableBackup(snapshot())
        assertEquals(2L to 1L, counts())
        assertFalse(db.isEmptyForRestore())
        val parsed = PortableRestore.parse(db.exportPortableBackup())
        assertEquals(snapshot(), parsed)
        assertEquals("2026-10-31T18:00:00.123456+00:00",
            parsed.tasks[0].createdAtExact)
        assertEquals("2026-10-31T12:10:11.654321+00:00",
            parsed.tasks[1].completedAtExact)
    }

    @Test fun populatedTasksCannotBeOverwritten() {
        db.add("Device-local task", 4, null, null)
        val original = db.listTasks().single()
        assertFalse(db.isEmptyForRestore())
        try {
            db.restorePortableBackup(snapshot())
            throw AssertionError("Existing user task was overwritten")
        } catch (_: IllegalArgumentException) { }
        assertEquals(1L to 0L, counts())
        assertEquals(original, db.listTasks().single())
    }

    @Test fun projectOnlyWorkspaceAlsoBlocksRestore() {
        val projectId = db.addProject("Local project")
        try {
            db.restorePortableBackup(snapshot())
            throw AssertionError("Existing user project was overwritten")
        } catch (_: IllegalArgumentException) { }
        assertEquals(0L to 1L, counts())
        assertEquals(projectId, db.listProjects().single().id)
    }

    @Test fun constraintFailureRollsBackAllProjectsAndTasks() {
        val valid = snapshot()
        // Bypass parser deliberately to exercise a mid-transaction SQL failure.
        val corrupt = valid.copy(tasks = valid.tasks + valid.tasks[0])
        try {
            db.restorePortableBackup(corrupt)
            throw AssertionError("Duplicate task ID should fail")
        } catch (_: SQLiteConstraintException) { }
        assertEquals(0L to 0L, counts())
        assertTrue(db.isEmptyForRestore())
        // The same database remains usable after the transaction rollback.
        db.restorePortableBackup(valid)
        assertEquals(2L to 1L, counts())
    }

    @Test fun completionTogglesDiscardStaleImportedCompletionTimestamp() {
        db.restorePortableBackup(snapshot())
        db.setCompleted("task-2", false)
        var parsed = PortableRestore.parse(db.exportPortableBackup())
        assertFalse(parsed.tasks[1].completed)
        assertEquals(null, parsed.tasks[1].completedAtExact)
        db.setCompleted("task-2", true)
        parsed = PortableRestore.parse(db.exportPortableBackup())
        assertTrue(parsed.tasks[1].completed)
        val newCompletion = requireNotNull(parsed.tasks[1].completedAt)
        assertTrue(newCompletion > 0L)
        assertEquals(PortableBackup.timestamp(newCompletion), parsed.tasks[1].completedAtExact)
        // The original imported microsecond timestamp must not survive a new
        // local completion. Only the fresh millisecond timestamp is exported.
        assertFalse(parsed.tasks[1].completedAtExact ==
            "2026-10-31T12:10:11.654321+00:00")
        db.readableDatabase.rawQuery(
            "SELECT completed_at_exact FROM tasks WHERE id='task-2'", null
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertTrue(cursor.isNull(0))
        }
    }

    @Test fun localTrashPreservesExactBackupMetadataAcrossRestart() {
        val source = snapshot()
        db.restorePortableBackup(source)
        assertTrue(db.delete("task-2"))
        assertFalse(db.delete("task-2"))
        assertEquals(listOf("task-2"), db.listDeletedTasks().map { it.id })
        assertEquals(listOf("task-1"), db.listTasks().map { it.id })
        assertEquals(listOf("task-1"),
            PortableRestore.parse(db.exportPortableBackup()).tasks.map { it.id })
        db.close()
        db = TasksDatabase(context)
        assertEquals(listOf("task-2"), db.listDeletedTasks().map { it.id })
        assertTrue(db.restoreDeletedTask("task-2"))
        assertFalse(db.restoreDeletedTask("task-2"))
        assertTrue(db.listDeletedTasks().isEmpty())
        assertEquals(source.tasks.sortedBy { it.id },
            PortableRestore.parse(db.exportPortableBackup()).tasks.sortedBy { it.id })
    }

    @Test fun emptyActiveWorkspaceWithTrashRejectsPortableImport() {
        db.add("Synthetic deleted task", 2, null, null)
        val id = db.listTasks().single().id
        assertTrue(db.delete(id))
        assertEquals(0L to 0L, counts())
        assertFalse(db.isEmptyForRestore())
        try {
            db.restorePortableBackup(snapshot())
            throw AssertionError("Protected Trash should block import")
        } catch (_: IllegalArgumentException) { }
        assertEquals(listOf(id), db.listDeletedTasks().map { it.id })
        assertEquals(0L to 0L, counts())
    }

    @Test fun trashCollisionRollsBackBothRows() {
        db.add("Original synthetic", 4, null, null)
        val id = db.listTasks().single().id
        assertTrue(db.delete(id))
        db.writableDatabase.execSQL(
            "INSERT INTO tasks(id,title,priority,completed,created_at) VALUES(?,?,?,?,?)",
            arrayOf(id, "Different active row", 2, 0, System.currentTimeMillis())
        )
        try {
            db.restoreDeletedTask(id)
            throw AssertionError("Duplicate task ID should block restore")
        } catch (_: SQLiteConstraintException) { }
        assertEquals("Different active row", db.listTasks().single().title)
        assertEquals("Original synthetic", db.listDeletedTasks().single().title)
        try {
            db.delete(id)
            throw AssertionError("Duplicate Trash ID should block deletion")
        } catch (_: SQLiteConstraintException) { }
        assertEquals("Different active row", db.listTasks().single().title)
        assertEquals("Original synthetic", db.listDeletedTasks().single().title)
    }

    @Test fun missingProjectFailsClosedWithoutLosingTrash() {
        db.restorePortableBackup(snapshot())
        assertTrue(db.delete("task-1"))
        db.writableDatabase.delete("projects", "id=?", arrayOf("project-1"))
        try {
            db.restoreDeletedTask("task-1")
            throw AssertionError("Deleted project should block restoration")
        } catch (_: IllegalArgumentException) { }
        assertEquals(listOf("task-1"), db.listDeletedTasks().map { it.id })
        assertEquals(listOf("task-2"), db.listTasks().map { it.id })
    }

    @Test fun versionFourUpgradeAddsTrashWithoutReplacingExistingRows() {
        db.close()
        context.deleteDatabase("goreecloud-tasks.db")
        val legacy = SQLiteDatabase.openOrCreateDatabase(
            context.getDatabasePath("goreecloud-tasks.db"), null
        )
        legacy.execSQL("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        legacy.execSQL(
            "CREATE TABLE tasks (id TEXT PRIMARY KEY,title TEXT NOT NULL," +
                "priority INTEGER NOT NULL,completed INTEGER NOT NULL," +
                "created_at INTEGER NOT NULL,completed_at INTEGER," +
                "created_at_exact TEXT,completed_at_exact TEXT," +
                "due_date TEXT,project_id TEXT)"
        )
        legacy.execSQL(
            "INSERT INTO tasks(id,title,priority,completed,created_at,created_at_exact) " +
                "VALUES('historical','Existing task',2,0,1761904800123," +
                "'2026-10-31T12:00:00.123456+00:00')"
        )
        legacy.version = 4
        legacy.close()
        db = TasksDatabase(context)
        assertEquals("Existing task", db.listTasks().single().title)
        assertTrue(db.listDeletedTasks().isEmpty())
        assertTrue(db.delete("historical"))
        assertTrue(db.restoreDeletedTask("historical"))
        db.readableDatabase.rawQuery(
            "SELECT created_at_exact FROM tasks WHERE id='historical'", null
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("2026-10-31T12:00:00.123456+00:00", cursor.getString(0))
        }
    }

    @Test fun versionThreeUpgradeRetainsExistingTaskAndAddsExactColumns() {
        db.close()
        context.deleteDatabase("goreecloud-tasks.db")
        val legacy = SQLiteDatabase.openOrCreateDatabase(
            context.getDatabasePath("goreecloud-tasks.db"), null
        )
        legacy.execSQL("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        legacy.execSQL(
            "CREATE TABLE tasks (" +
            "id TEXT PRIMARY KEY,title TEXT NOT NULL,priority INTEGER NOT NULL," +
            "completed INTEGER NOT NULL,created_at INTEGER NOT NULL,completed_at INTEGER," +
            "due_date TEXT,project_id TEXT)"
        )
        legacy.execSQL(
            "INSERT INTO tasks(id,title,priority,completed,created_at,completed_at) " +
            "VALUES('historical','Preserved',2,1,1761904800123,1761904800456)"
        )
        legacy.version = 3
        legacy.close()
        db = TasksDatabase(context)
        assertEquals("Preserved", db.listTasks().single().title)
        assertEquals(1L to 0L, counts())
        db.readableDatabase.rawQuery("PRAGMA table_info(tasks)", null).use { columns ->
            val names = mutableSetOf<String>()
            while (columns.moveToNext()) names.add(columns.getString(1))
            assertTrue("created_at_exact" in names)
            assertTrue("completed_at_exact" in names)
        }
        assertEquals(1L to 0L, counts())
    }
}
