package com.goreecloud.tasks

import android.database.sqlite.SQLiteDatabase
import org.json.JSONArray
import org.json.JSONObject

/** In-memory-only SQLite reference; NOT connected to TasksDatabase or user actions. */
internal class SubtaskSqliteReference(private val db: SQLiteDatabase) {
    init {
        require(db.path == ":memory:") { "Refusing file-backed SQLite" }
        db.execSQL("CREATE TABLE proposed_meta (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        db.execSQL("CREATE TABLE proposed_tasks (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        db.execSQL("CREATE TABLE proposed_trash (id TEXT PRIMARY KEY, payload TEXT NOT NULL, " +
            "deleted_at TEXT NOT NULL, group_id TEXT NOT NULL, group_root_id TEXT NOT NULL, " +
            "group_size INTEGER NOT NULL)")
    }

    fun seed(source: JSONObject) {
        SubtaskContract.parseProposed(source.toString().toByteArray(Charsets.UTF_8))
        db.beginTransaction()
        try {
            db.execSQL("INSERT INTO proposed_meta VALUES ('projects',?)",
                arrayOf(source.getJSONArray("projects").toString()))
            val tasks = source.getJSONArray("tasks")
            for (i in 0 until tasks.length()) {
                val task = tasks.getJSONObject(i)
                db.execSQL("INSERT INTO proposed_tasks VALUES (?,?)",
                    arrayOf(task.getString("id"),task.toString()))
            }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    fun workspace(): JSONObject {
        val projects = db.rawQuery("SELECT data FROM proposed_meta WHERE id='projects'",null)
            .use { cursor ->
                require(cursor.moveToFirst()) { "Unseeded reference" }
                JSONArray(cursor.getString(0))
            }
        val tasks=JSONArray()
        db.rawQuery("SELECT payload FROM proposed_tasks ORDER BY rowid",null).use { cursor ->
            while (cursor.moveToNext()) tasks.put(JSONObject(cursor.getString(0)))
        }
        return JSONObject().put("schema",4).put("projects",projects).put("tasks",tasks)
    }

    fun trash(): List<JSONObject> {
        val result=ArrayList<JSONObject>()
        db.rawQuery("SELECT payload,deleted_at,group_id,group_root_id,group_size " +
            "FROM proposed_trash ORDER BY rowid",null).use { cursor ->
            while (cursor.moveToNext()) result.add(JSONObject()
                .put("task",JSONObject(cursor.getString(0)))
                .put("deletedAt",cursor.getString(1))
                .put("groupId",cursor.getString(2))
                .put("groupRootId",cursor.getString(3))
                .put("groupSize",cursor.getInt(4)))
        }
        return result
    }

    private fun validateWorkspace() {
        SubtaskContract.parseProposed(workspace().toString().toByteArray(Charsets.UTF_8))
    }

    fun deleteSubtree(root: String, at: String, group: String): List<String> {
        require(!db.inTransaction()) { "Reference requires a fresh transaction" }
        db.beginTransactionNonExclusive()
        try {
            val plan=SubtaskRecovery.planDelete(workspace(),trash(),root,at,group)
            for (entry in plan.trash.filter { it.getString("groupId") == group }) {
                val task=entry.getJSONObject("task")
                val id=task.getString("id")
                db.execSQL("INSERT INTO proposed_trash VALUES (?,?,?,?,?,?)",
                    arrayOf(id,task.toString(),entry.getString("deletedAt"),
                        group,entry.getString("groupRootId"),entry.getInt("groupSize")))
                require(db.delete("proposed_tasks","id=?",arrayOf(id)) == 1) {
                    "Task changed during deletion"
                }
            }
            validateWorkspace()
            db.setTransactionSuccessful()
            return plan.affectedIds
        } finally { db.endTransaction() }
    }

    fun restoreGroup(group: String): List<String> {
        require(!db.inTransaction()) { "Reference requires a fresh transaction" }
        db.beginTransactionNonExclusive()
        try {
            val plan=SubtaskRecovery.planRestore(workspace(),trash(),group)
            for (entry in trash().filter { it.getString("groupId") == group }) {
                val task=entry.getJSONObject("task")
                val id=task.getString("id")
                db.execSQL("INSERT INTO proposed_tasks VALUES (?,?)",arrayOf(id,task.toString()))
                require(db.delete("proposed_trash","id=?",arrayOf(id)) == 1) {
                    "Trash changed during restoration"
                }
            }
            validateWorkspace()
            db.setTransactionSuccessful()
            return plan.affectedIds
        } finally { db.endTransaction() }
    }
}
