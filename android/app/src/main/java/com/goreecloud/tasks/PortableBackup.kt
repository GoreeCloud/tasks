package com.goreecloud.tasks

import android.database.sqlite.SQLiteDatabase
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.OffsetDateTime

/**
 * Browser/Linux-compatible schema-1 JSON export for an already-open Android DB.
 * This contains only user projects/tasks (never credentials or app-private config).
 * A read transaction prevents mixed task and project snapshots.
 */
internal object PortableBackup {
    const val MAX_BYTES = 2 * 1024 * 1024
    private const val MAX_RECORDS = 10_000

    fun timestamp(milliseconds: Long): String {
        require(milliseconds > 0) { "Missing historical timestamp; export cancelled." }
        return Instant.ofEpochMilli(milliseconds).toString()
    }

    /** Preserve precise portable timestamps; normalize older nonportable source strings. */
    fun timestampForExport(milliseconds: Long, original: String?): String {
        if (original == null) return timestamp(milliseconds)
        require(original.length <= 40) { "Invalid restored timestamp" }
        val parsed = try { OffsetDateTime.parse(original).toInstant().toEpochMilli() }
        catch (failure: Exception) {
            throw IllegalArgumentException("Invalid restored timestamp", failure)
        }
        require(parsed == milliseconds) { "Stored timestamp and original disagree" }
        // Earlier Android parsers accepted some OffsetDateTime strings without
        // seconds. Emit a portable timestamp rather than an unrestorable backup.
        return if (PortableRestore.isPortableTimestamp(original)) original else timestamp(milliseconds)
    }

    fun completionTimestamp(completed: Boolean, completedAt: Long?): Any {
        require(completed == (completedAt != null)) {
            "Some completed tasks predate accurate completion history. Reopen and complete those tasks before exporting."
        }
        return if (completed) timestamp(requireNotNull(completedAt)) else JSONObject.NULL
    }

    fun encode(database: SQLiteDatabase): ByteArray {
        val projects = JSONArray()
        val tasks = JSONArray()
        val projectIds = mutableSetOf<String>()
        database.beginTransactionNonExclusive()
        try {
            database.rawQuery("SELECT id,name FROM projects ORDER BY id", null).use { cursor ->
                while (cursor.moveToNext()) {
                    require(projects.length() < MAX_RECORDS) { "Too many projects to export." }
                    val id = cursor.getString(0)
                    val name = cursor.getString(1)
                    require(id.isNotBlank() && id.length <= 128 && projectIds.add(id))
                    require(TaskRules.projectName(name) == name)
                    projects.put(JSONObject().put("id", id).put("name", name))
                }
            }
            val taskIds = mutableSetOf<String>()
            database.rawQuery(
                "SELECT id,title,priority,completed,due_date,project_id,created_at,completed_at, " +
                    "created_at_exact,completed_at_exact " +
                    "FROM tasks ORDER BY id", null
            ).use { cursor ->
                while (cursor.moveToNext()) {
                    require(tasks.length() < MAX_RECORDS) { "Too many tasks to export." }
                    val id = cursor.getString(0)
                    val title = cursor.getString(1)
                    val priority = cursor.getInt(2)
                    val flag = cursor.getInt(3)
                    val completed = flag == 1
                    val due = if (cursor.isNull(4)) "" else cursor.getString(4)
                    val projectId = if (cursor.isNull(5)) null else cursor.getString(5)
                    val created = cursor.getLong(6)
                    val completedAt = if (cursor.isNull(7)) null else cursor.getLong(7)
                    val createdExact = if (cursor.isNull(8)) null else cursor.getString(8)
                    val completedExact = if (cursor.isNull(9)) null else cursor.getString(9)
                    require(id.isNotBlank() && id.length <= 128 && taskIds.add(id))
                    require(TaskRules.title(title) == title)
                    TaskRules.priority(priority)
                    require(flag == 0 || flag == 1)
                    require(due.isEmpty() || TaskRules.due(due) == due)
                    require(projectId == null || projectId in projectIds)
                    val task = JSONObject()
                        .put("id", id)
                        .put("title", title)
                        .put("priority", priority)
                        .put("completed", completed)
                        .put("due", due)
                        .put("projectId", projectId ?: JSONObject.NULL)
                        .put("createdAt", timestampForExport(created, createdExact))
                        .put("completedAt", if (completedAt == null) {
                            completionTimestamp(completed, null)
                        } else {
                            require(completed) { "Completion metadata is inconsistent" }
                            timestampForExport(completedAt, completedExact)
                        })
                    tasks.put(task)
                }
            }
            val backup = JSONObject()
                .put("schema", 1)
                .put("projects", projects)
                .put("tasks", tasks)
            val bytes = backup.toString(2).toByteArray(Charsets.UTF_8)
            require(bytes.size <= MAX_BYTES) { "Backup exceeds the 2 MiB portable format limit." }
            database.setTransactionSuccessful()
            return bytes
        } finally {
            database.endTransaction()
        }
    }
}
