package com.goreecloud.tasks

import org.json.JSONArray
import org.json.JSONObject

/** Disposable read-only schema 1-3 to v4 roots preview; no live import pathway. */
internal object SubtaskMigrationPreview {
    fun legacyAsRoots(bytes: ByteArray): JSONObject {
        val legacy = PortableRestore.parse(bytes) // strict validation first
        val projects = JSONArray()
        for (project in legacy.projects) {
            projects.put(JSONObject().put("id", project.id).put("name", project.name))
        }
        val tasks = JSONArray()
        for (task in legacy.tasks) {
            tasks.put(JSONObject()
                .put("id", task.id)
                .put("title", task.title)
                .put("projectId", task.projectId ?: JSONObject.NULL)
                .put("due", task.dueDate ?: "")
                .put("priority", task.priority)
                .put("completed", task.completed)
                .put("createdAt", task.createdAtExact)
                .put("completedAt", task.completedAtExact ?: JSONObject.NULL)
                .put("description", task.description)
                .put("labels", JSONArray(task.labels))
                .put("parentId", JSONObject.NULL))
        }
        val projected = JSONObject().put("schema", 4).put("projects", projects).put("tasks", tasks)
        SubtaskContract.parseProposed(projected.toString().toByteArray(Charsets.UTF_8))
        return projected
    }
}
