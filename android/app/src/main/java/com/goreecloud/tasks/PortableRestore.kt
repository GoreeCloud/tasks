package com.goreecloud.tasks

import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.time.OffsetDateTime

/** Fully validated portable schema-1 data; never mutates a device database. */
internal data class RestoreProject(val id: String, val name: String)
internal data class RestoreTask(
    val id: String, val title: String, val priority: Int, val completed: Boolean,
    val dueDate: String?, val projectId: String?, val createdAt: Long,
    val completedAt: Long?
)
internal data class RestoreSnapshot(
    val projects: List<RestoreProject>, val tasks: List<RestoreTask>
)

/**
 * Read-only and fail-closed browser/Linux JSON contract parser. No credentials,
 * network or filesystem access. Import is a separate, guarded SQLite transaction.
 */
internal object PortableRestore {
    private const val MAX_RECORDS = 10_000
    private val timestampPrefix = Regex("^\\d{4}-\\d\\d-\\d\\dT")

    private fun goodUnicode(value: String): Boolean {
        var index = 0
        while (index < value.length) {
            val char = value[index]
            if (Character.isHighSurrogate(char)) {
                if (++index >= value.length || !Character.isLowSurrogate(value[index])) return false
            } else if (Character.isLowSurrogate(char)) return false
            index++
        }
        return true
    }

    private fun id(value: Any?, name: String): String {
        require(value is String && value.isNotEmpty() && value.length <= 128 &&
            goodUnicode(value) && value.none { it.code < 32 || it.code == 127 }) {
            "Invalid $name"
        }
        return value
    }

    private fun requiredString(value: Any?, label: String): String {
        require(value is String && goodUnicode(value)) { "Invalid $label" }
        return value
    }

    private fun timestamp(value: Any?, label: String): Long {
        val raw = requiredString(value, label)
        require(raw.length <= 40 && timestampPrefix.containsMatchIn(raw)) {
            "Invalid $label"
        }
        val parsed = try { OffsetDateTime.parse(raw).toInstant() }
        catch (failure: Exception) { throw IllegalArgumentException("Invalid $label", failure) }
        require(parsed.nano % 1_000_000 == 0) {
            "Timestamp exceeds the Android millisecond precision limit"
        }
        val millis = try { parsed.toEpochMilli() }
        catch (failure: ArithmeticException) {
            throw IllegalArgumentException("Timestamp is outside the supported range", failure)
        }
        require(millis > 0) { "Invalid historical timestamp" }
        return millis
    }

    private fun objectAt(collection: JSONArray, index: Int): JSONObject {
        return collection.opt(index) as? JSONObject
            ?: throw IllegalArgumentException("Backup contains an invalid record")
    }

    private fun childArray(parent: JSONObject, key: String): JSONArray {
        return parent.opt(key) as? JSONArray
            ?: throw IllegalArgumentException("Missing $key array")
    }

    /** Never read more than the accepted size from an untrusted document provider. */
    fun readLimited(source: InputStream): ByteArray {
        val buffer = ByteArray(8192)
        val output = ByteArrayOutputStream()
        while (true) {
            val count = source.read(buffer)
            if (count < 0) break
            require(count != 0) { "Document provider returned no data; retry import." }
            require(output.size() + count <= PortableBackup.MAX_BYTES) {
                "Backup exceeds the 2 MiB portable format limit."
            }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }

    fun parse(bytes: ByteArray): RestoreSnapshot {
        require(bytes.size <= PortableBackup.MAX_BYTES) {
            "Backup exceeds the 2 MiB portable format limit."
        }
        val text = try {
            Charsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(bytes)).toString()
        } catch (failure: Exception) {
            throw IllegalArgumentException("Backup is not valid UTF-8", failure)
        }
        val tokener = JSONTokener(text)
        val root = try { tokener.nextValue() as? JSONObject }
        catch (failure: Exception) {
            throw IllegalArgumentException("Backup is not valid JSON", failure)
        } ?: throw IllegalArgumentException("Backup must be a JSON object")
        require(tokener.nextClean() == '\u0000') { "Unexpected content after JSON" }
        require(root.opt("schema") is Int && root.getInt("schema") == 1) {
            "Unsupported or incomplete GoreeCloud Tasks backup schema"
        }
        val projectEntries = childArray(root, "projects")
        val taskEntries = childArray(root, "tasks")
        require(projectEntries.length() <= MAX_RECORDS && taskEntries.length() <= MAX_RECORDS) {
            "Backup contains too many records"
        }

        val projects = ArrayList<RestoreProject>(projectEntries.length())
        val projectIds = HashSet<String>()
        for (i in 0 until projectEntries.length()) {
            val item = objectAt(projectEntries, i)
            val key = id(item.opt("id"), "project ID")
            val name = requiredString(item.opt("name"), "project name")
            require(TaskRules.projectName(name) == name && projectIds.add(key)) {
                "Invalid or duplicate project"
            }
            projects.add(RestoreProject(key, name))
        }

        val tasks = ArrayList<RestoreTask>(taskEntries.length())
        val taskIds = HashSet<String>()
        for (i in 0 until taskEntries.length()) {
            val item = objectAt(taskEntries, i)
            val key = id(item.opt("id"), "task ID")
            val title = requiredString(item.opt("title"), "task title")
            require(TaskRules.title(title) == title && taskIds.add(key)) {
                "Invalid or duplicate task"
            }
            val priority = item.opt("priority")
            require(priority is Int) { "Invalid task priority" }
            TaskRules.priority(priority)
            val completed = item.opt("completed")
            require(completed is Boolean) { "Invalid completion flag" }
            val rawDue = requiredString(item.opt("due"), "due date")
            val due = if (rawDue.isEmpty()) null else TaskRules.due(rawDue)
            require(rawDue.isEmpty() || due == rawDue) { "Invalid due date" }
            require(item.has("projectId")) { "Missing task project reference" }
            val rawProject = item.opt("projectId")
            val projectId = if (rawProject === JSONObject.NULL) null
                else id(rawProject, "task project")
            require(projectId == null || projectId in projectIds) {
                "Task references a missing project"
            }
            val createdAt = timestamp(item.opt("createdAt"), "creation timestamp")
            val rawCompletion = item.opt("completedAt")
            require(item.has("completedAt")) { "Missing completion timestamp" }
            val completedAt = if (rawCompletion == JSONObject.NULL) null
                else timestamp(rawCompletion, "completion timestamp")
            require(completed == (completedAt != null)) {
                "Task completion metadata is inconsistent"
            }
            tasks.add(RestoreTask(key, title, priority, completed, due, projectId,
                                  createdAt, completedAt))
        }
        return RestoreSnapshot(projects, tasks)
    }
}
