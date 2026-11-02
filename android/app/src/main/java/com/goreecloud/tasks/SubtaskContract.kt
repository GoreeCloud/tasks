package com.goreecloud.tasks

import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

/** Proposed v4 relationship check. Not connected to production import or SQLite. */
internal data class ProposedGraph(
    val validated: RestoreSnapshot,
    val parents: Map<String, String?>,
    val depths: Map<String, Int>
)

internal object SubtaskContract {
    fun parseProposed(bytes: ByteArray): ProposedGraph {
        require(bytes.size <= PortableBackup.MAX_BYTES) { "Proposed backup is too large" }
        val text = Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(bytes)).toString()
        val tokener = JSONTokener(text)
        val root = tokener.nextValue() as? JSONObject
            ?: throw IllegalArgumentException("Expected proposed schema-4 object")
        require(tokener.nextClean() == '\u0000' && root.opt("schema") == 4) {
            "Expected proposed schema 4"
        }
        val original = root.opt("tasks") as? JSONArray
            ?: throw IllegalArgumentException("Missing task array")
        require(original.length() <= 10000) { "Too many tasks" }
        val legacy = JSONObject(root.toString())
        legacy.put("schema", 3)
        val stripped = JSONArray()
        val parents = LinkedHashMap<String, String?>()
        for (i in 0 until original.length()) {
            val source = original.opt(i) as? JSONObject
                ?: throw IllegalArgumentException("Invalid task record")
            require(source.has("parentId")) { "Missing parentId" }
            val rawParent = source.opt("parentId")
            val parent = when (rawParent) {
                JSONObject.NULL -> null
                is String -> {
                    require(rawParent.isNotEmpty() && rawParent.length <= 128 &&
                        rawParent.none { it.code < 32 || it.code == 127 } &&
                        validUnicode(rawParent)) { "Invalid parentId" }
                    rawParent
                }
                else -> throw IllegalArgumentException("Invalid parentId")
            }
            val key = source.opt("id") as? String
                ?: throw IllegalArgumentException("Invalid task ID")
            parents[key] = parent
            val copy = JSONObject(source.toString())
            copy.remove("parentId")
            stripped.put(copy)
        }
        legacy.put("tasks", stripped)
        // Full title, project, ID uniqueness, notes, labels, completion and
        // timestamp validation is delegated to the existing strict v3 reader.
        val validated = PortableRestore.parse(legacy.toString().toByteArray(Charsets.UTF_8))
        val lookup = validated.tasks.associateBy { it.id }
        val counts = HashMap<String?, Int>()
        val depths = LinkedHashMap<String, Int>()
        for (task in validated.tasks) {
            counts[task.projectId] = (counts[task.projectId] ?: 0) + 1
            require(counts[task.projectId]!! <= 300) { "Project exceeds 300 tasks" }
            var current: String? = task.id
            val seen = HashSet<String>()
            var depth = 0
            while (current != null) {
                require(seen.add(current)) { "Subtask cycle" }
                depth++
                require(depth <= 3) { "Subtask nesting exceeds three levels" }
                val node = lookup[current] ?: throw IllegalArgumentException("Missing parent task")
                require(node.projectId == task.projectId) { "Cross-project subtask" }
                current = parents[current]
            }
            depths[task.id] = depth
        }
        return ProposedGraph(validated, parents.toMap(), depths)
    }

    private fun validUnicode(value: String): Boolean {
        var i = 0
        while (i < value.length) {
            val ch = value[i]
            if (Character.isHighSurrogate(ch)) {
                if (++i == value.length || !Character.isLowSurrogate(value[i])) return false
            } else if (Character.isLowSurrogate(ch)) return false
            i++
        }
        return true
    }
}
