package com.goreecloud.tasks

import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime

/** Pure proposed recovery plan: not wired to SQLite or user-facing actions. */
internal data class SubtaskRecoveryPlan(
    val workspace: JSONObject,
    val trash: List<JSONObject>,
    val affectedIds: List<String>
)

internal object SubtaskRecovery {
    private val groupPattern = Regex("^[a-zA-Z0-9-]{1,128}$")
    private const val MAX_TRASH = 1000
    private const val MAX_LOCAL_BYTES = 3 * 1024 * 1024

    private fun validGroup(value: String) {
        require(groupPattern.matches(value)) { "Invalid recovery group ID" }
    }

    private fun validDeletionTime(value: String) {
        require(PortableRestore.isPortableTimestamp(value)) { "Invalid deletion timestamp" }
        val parsed = try { OffsetDateTime.parse(value).toInstant().toEpochMilli() }
        catch (error: Exception) { throw IllegalArgumentException("Invalid deletion timestamp", error) }
        require(parsed > 0) { "Invalid deletion timestamp" }
    }

    private fun graph(value: JSONObject): ProposedGraph =
        SubtaskContract.parseProposed(value.toString().toByteArray(Charsets.UTF_8))

    private fun clone(value: JSONObject): JSONObject = JSONObject(value.toString())

    private fun tasks(value: JSONObject): List<JSONObject> {
        val arr = value.getJSONArray("tasks")
        return (0 until arr.length()).map { arr.getJSONObject(it) }
    }

    private fun checkedSize(workspace: JSONObject, trash: List<JSONObject>) {
        require(trash.size <= MAX_TRASH) { "Proposed local Trash capacity exceeded" }
        val size = JSONObject().put("workspace",workspace)
            .put("trash", JSONArray(trash)).toString().toByteArray(Charsets.UTF_8).size
        require(size <= MAX_LOCAL_BYTES) { "Proposed local Trash capacity exceeded" }
    }

    fun planDelete(
        workspace: JSONObject, trash: List<JSONObject>,
        rootId: String, deletedAt: String, groupId: String
    ): SubtaskRecoveryPlan {
        graph(workspace)
        validGroup(groupId)
        validDeletionTime(deletedAt)
        require(trash.none { it.optString("groupId") == groupId }) {
            "Recovery group already exists"
        }
        val original = tasks(workspace)
        val byId = original.associateBy { it.getString("id") }
        require(rootId in byId) { "Root task no longer exists" }
        val children = HashMap<String, MutableList<String>>()
        for (item in original) {
            val parent = item.opt("parentId")
            if (parent is String) children.getOrPut(parent) { mutableListOf() }
                .add(item.getString("id"))
        }
        val pending = ArrayDeque<String>()
        pending.add(rootId)
        val ids = LinkedHashSet<String>()
        while (pending.isNotEmpty()) {
            val current = pending.removeLast()
            ids.add(current)
            children[current]?.forEach { pending.add(it) }
        }
        require(trash.none { entry ->
            (entry.opt("task") as? JSONObject)?.optString("id")?.let { it in ids } == true
        }) { "Task ID conflicts with recoverable Trash" }
        val nextWorkspace = clone(workspace)
        val remaining = JSONArray()
        val moved = ArrayList<JSONObject>()
        original.forEach { item ->
            if (item.getString("id") in ids) moved.add(item) else remaining.put(item)
        }
        nextWorkspace.put("tasks", remaining)
        val nextTrash = trash.map(::clone).toMutableList()
        moved.forEach { item ->
            nextTrash.add(JSONObject()
                .put("task", clone(item))
                .put("deletedAt", deletedAt)
                .put("groupId", groupId)
                .put("groupRootId", rootId)
                .put("groupSize", ids.size))
        }
        graph(nextWorkspace)
        checkedSize(nextWorkspace, nextTrash)
        return SubtaskRecoveryPlan(nextWorkspace, nextTrash, ids.toList())
    }

    fun planRestore(
        workspace: JSONObject, trash: List<JSONObject>, groupId: String
    ): SubtaskRecoveryPlan {
        graph(workspace)
        validGroup(groupId)
        val group = trash.filter { it.optString("groupId") == groupId }
        require(group.isNotEmpty()) { "Recovery group not found" }
        val first = group.first()
        val count = first.opt("groupSize")
        require(count is Int && count >= 1 && count == group.size && group.size <= MAX_TRASH) {
            "Incomplete recovery group"
        }
        val root = first.optString("groupRootId")
        val ids = ArrayList<String>()
        group.forEach { entry ->
            val task = entry.opt("task") as? JSONObject
                ?: throw IllegalArgumentException("Invalid recovery record")
            require(entry.opt("groupSize") == count &&
                entry.optString("groupRootId") == root && task.has("parentId")) {
                "Incomplete recovery group"
            }
            validDeletionTime(entry.getString("deletedAt"))
            ids.add(task.getString("id"))
        }
        val distinct = ids.toSet()
        require(distinct.size == ids.size && root in distinct) {
            "Duplicate or missing recovery roots"
        }
        // Group metadata must describe one connected subtree, not just N rows.
        val groupIds = distinct
        val parents = group.associate { entry ->
            val task = entry.getJSONObject("task")
            task.getString("id") to (task.opt("parentId") as? String)
        }
        require(group.all { entry ->
            val task = entry.getJSONObject("task")
            entry.getString("deletedAt") == first.getString("deletedAt") &&
                (task.getString("id") == root ||
                    (task.opt("parentId") as? String) in groupIds)
        }) { "Recovery group is not one intact subtree" }
        for (id in groupIds) {
            if (id == root) continue
            var current = id
            val seen = mutableSetOf<String>()
            while (current != root) {
                require(seen.add(current)) { "Recovery group contains a cycle" }
                current = parents[current]
                    ?: throw IllegalArgumentException("Recovery group includes an unrelated task")
            }
        }
        val active = tasks(workspace).mapTo(HashSet()) { it.getString("id") }
        require(distinct.none { it in active } &&
            trash.none { entry -> entry.optString("groupId") != groupId &&
                (entry.opt("task") as? JSONObject)?.optString("id")?.let { it in distinct } == true }) {
            "Recovery ID collision"
        }
        val nextWorkspace = clone(workspace)
        val nextTasks = nextWorkspace.getJSONArray("tasks")
        group.forEach { nextTasks.put(clone(it.getJSONObject("task"))) }
        graph(nextWorkspace) // checks recovered parents, projects, cycles and depth
        val nextTrash = trash.filter { it.optString("groupId") != groupId }.map(::clone)
        checkedSize(nextWorkspace, nextTrash)
        return SubtaskRecoveryPlan(nextWorkspace, nextTrash, ids)
    }
}
