package com.goreecloud.tasks

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.time.LocalDate
import java.util.UUID

data class ProjectItem(val id: String, val name: String)

data class HabitItem(
    val id:String, val name:String, val description:String,
    val version:Int, val checkedInToday:Boolean, val currentStreak:Int,
    val totalCheckins:Int
)

data class TaskItem(
    val id: String,
    val title: String,
    val description: String,
    val dueDate: String?,
    val priority: Int,
    val version: Int,
    val projectId: String?,
    val parentId: String?,
    val recurrence: String,
    val tags: List<String>,
    val completedAt: String?
) {
    val done: Boolean get() = completedAt != null
}

/** Each operation uses an explicit user-supplied server, with TLS by default. */
class TaskApi(private val base: String, private val token: String) {
    init {
        require(token.length >= 32) { "API token must contain at least 32 characters" }
        val url = URL(base)
        require(url.protocol == "https" ||
            (BuildConfig.DEBUG && url.protocol == "http" && url.host == "10.0.2.2")) {
            "HTTPS is required outside the Android debug emulator"
        }
        require(url.userInfo == null && url.query == null && url.ref == null &&
            (url.path.isEmpty() || url.path == "/")) {
            "Enter a server origin without a path, query or embedded credentials"
        }
    }

    private suspend fun request(path: String, method: String = "GET",
                                body: JSONObject? = null,
                                idempotencyKey: String? = null): String = withContext(Dispatchers.IO) {
        val connection = (URL(base.trimEnd('/') + "/api/v1" + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 15_000
            instanceFollowRedirects = false
            setRequestProperty("Authorization", "Bearer " + token)
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Content-Type", "application/json")
            if (idempotencyKey != null) setRequestProperty("Idempotency-Key", idempotencyKey)
            if (body != null) {
                doOutput = true
                outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
        }
        try {
            val status = connection.responseCode
            if (status == 409) throw IllegalStateException("Task changed on the server; refresh and retry")
            if (status !in 200..299) throw IllegalStateException("Server returned HTTP " + status)
            if (status == 204) "" else connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    private fun parseTask(json: JSONObject): TaskItem {
        val tagsArray = json.optJSONArray("tags") ?: JSONArray()
        return TaskItem(
            id = json.getString("id"),
            title = json.getString("title"),
            description = json.optString("description"),
            dueDate = json.optString("due_date").takeIf { it.isNotBlank() && it != "null" },
            priority = json.getInt("priority"),
            version = json.getInt("version"),
            projectId = json.optString("project_id").takeIf { it.isNotBlank() && it != "null" },
            parentId = json.optString("parent_id").takeIf { it.isNotBlank() && it != "null" },
            recurrence = json.optString("recurrence", "none"),
            tags = (0 until tagsArray.length()).map { tagsArray.getString(it) },
            completedAt = json.optString("completed_at").takeIf { it.isNotBlank() && it != "null" }
        )
    }

    suspend fun listTasks(): List<TaskItem> {
        val json = JSONArray(request("/tasks?status=all"))
        return (0 until json.length()).map { parseTask(json.getJSONObject(it)) }
    }

    suspend fun listProjects(): List<ProjectItem> {
        val json = JSONArray(request("/projects"))
        return (0 until json.length()).map { index ->
            val project = json.getJSONObject(index)
            ProjectItem(project.getString("id"), project.getString("name"))
        }
    }

    suspend fun createProject(name: String): ProjectItem {
        require(name.isNotBlank()) { "Enter a project name" }
        val json = JSONObject(request("/projects", "POST",
            JSONObject().put("name", name.trim()), UUID.randomUUID().toString()))
        return ProjectItem(json.getString("id"), json.getString("name"))
    }

    private fun validateDueDate(value: String?) {
        if (!value.isNullOrBlank()) {
            try { LocalDate.parse(value.trim()) }
            catch (_: Exception) { throw IllegalArgumentException("Date must be YYYY-MM-DD") }
        }
    }

    private fun toJson(title: String, description: String, dueDate: String?, priority: Int,
                       projectId: String?, parentId: String?, recurrence: String, tags: List<String>): JSONObject {
        require(title.trim().length in 1..240) { "Task title must contain 1–240 characters" }
        require(priority in 1..4) { "Priority must be P1 to P4" }
        require(recurrence in listOf("none", "daily", "weekly", "monthly")) { "Unknown recurrence" }
        require(recurrence == "none" || !dueDate.isNullOrBlank()) {
            "Recurring tasks need a due date"
        }
        validateDueDate(dueDate)
        return JSONObject()
            .put("title", title.trim())
            .put("description", description)
            .put("due_date", if (dueDate.isNullOrBlank()) JSONObject.NULL else dueDate.trim())
            .put("priority", priority)
            .put("project_id", if (projectId == null) JSONObject.NULL else projectId)
            .put("parent_id", if (parentId == null) JSONObject.NULL else parentId)
            .put("recurrence", recurrence)
            .put("tags", JSONArray(tags.map { it.trim() }.filter { it.isNotBlank() }))
    }

    suspend fun createTask(title: String, description: String, dueDate: String?,
                           priority: Int, projectId: String?, parentId: String?, recurrence: String,
                           tags: List<String>): TaskItem {
        val content = toJson(title, description, dueDate, priority, projectId, parentId, recurrence, tags)
        return parseTask(JSONObject(request("/tasks", "POST", content, UUID.randomUUID().toString())))
    }

    suspend fun updateTask(previous: TaskItem, title: String, description: String,
                           dueDate: String?, priority: Int, projectId: String?,
                           parentId: String?, recurrence: String, tags: List<String>): TaskItem {
        val content = toJson(title, description, dueDate, priority, projectId, parentId, recurrence, tags)
            .put("expected_version", previous.version)
        return parseTask(JSONObject(request("/tasks/" + encoded(previous.id), "PATCH", content)))
    }

    suspend fun completeTask(task: TaskItem) {
        request("/tasks/" + encoded(task.id) + "/complete", "POST",
            JSONObject().put("expected_version", task.version), UUID.randomUUID().toString())
    }

    suspend fun reopenTask(task: TaskItem) {
        request("/tasks/" + encoded(task.id) + "/reopen", "POST",
            JSONObject().put("expected_version", task.version))
    }

    suspend fun deleteTask(task: TaskItem) {
        request("/tasks/" + encoded(task.id) + "?expected_version=" + task.version, "DELETE")
    }

    private fun parseHabit(data: JSONObject): HabitItem = HabitItem(
        id = data.getString("id"),
        name = data.getString("name"),
        description = data.optString("description", ""),
        version = data.getInt("version"),
        checkedInToday = data.getBoolean("checked_in_today"),
        currentStreak = data.getInt("current_streak"),
        totalCheckins = data.getInt("total_checkins")
    )

    suspend fun listHabits(localDay:String):List<HabitItem> {
        val result = JSONArray(request("/habits?as_of="+encoded(localDay)))
        return (0 until result.length()).map { parseHabit(result.getJSONObject(it)) }
    }

    suspend fun createHabit(name:String, description:String):HabitItem {
        require(name.isNotBlank() && name.length <= 120) { "Habit name must be 1–120 characters" }
        return parseHabit(JSONObject(request("/habits","POST",
            JSONObject().put("name",name.trim()).put("description",description))))
    }

    suspend fun checkIn(habit:HabitItem, localDay:String) {
        request("/habits/"+encoded(habit.id)+"/checkins","POST",
            JSONObject().put("day",localDay).put("expected_version",habit.version))
    }

    suspend fun undoCheckIn(habit:HabitItem, localDay:String) {
        request("/habits/"+encoded(habit.id)+"/checkins/"+encoded(localDay)+
            "?expected_version="+habit.version,"DELETE")
    }

    suspend fun deleteHabit(habit:HabitItem) {
        request("/habits/"+encoded(habit.id)+"?expected_version="+habit.version,"DELETE")
    }

    private fun encoded(id: String): String = URLEncoder.encode(id, "UTF-8")
}
