package com.goreecloud.tasks

import org.json.JSONArray
import org.json.JSONObject

/** Isolated schema-4 reference: NOT wired to live task data or user actions. */
internal object SubtaskGroupManifest {
    fun verify(m: JSONObject, trash: List<JSONObject>): Boolean {
        val groupId = m.opt("groupId") as? String ?: throw IllegalArgumentException("Invalid group")
        require(Regex("^[A-Za-z0-9-]{1,128}$").matches(groupId))
        val root = m.opt("groupRootId") as? String ?: throw IllegalArgumentException("Invalid root")
        val date = m.opt("deletedAt") as? String ?: throw IllegalArgumentException("Invalid date")
        require(root.isNotEmpty() && PortableRestore.isPortableTimestamp(date))
        val array = m.opt("memberIds") as? JSONArray ?: throw IllegalArgumentException("Missing members")
        require(array.length() in 1..1000)
        val members = (0 until array.length()).map { index ->
            array.opt(index) as? String ?: throw IllegalArgumentException("Invalid member")
        }
        require(members.all { it.isNotEmpty() && it.length <= 128 })
        require(members == members.distinct().sorted() && root in members)
        val rows = trash.filter { it.optString("groupId") == groupId }
        require(rows.size == members.size) { "Manifest count mismatch" }
        val ids = rows.map { (it.opt("task") as? JSONObject)?.optString("id") ?: "" }.sorted()
        require(ids == members) { "Manifest member mismatch" }
        require(rows.all {
            it.optString("groupRootId") == root && it.optString("deletedAt") == date &&
                it.opt("groupSize") is Int && it.getInt("groupSize") == members.size
        }) { "Manifest metadata mismatch" }
        return true
    }

    fun create(trash: List<JSONObject>, groupId: String): JSONObject {
        val rows = trash.filter { it.optString("groupId") == groupId }
        require(rows.isNotEmpty()) { "Missing group" }
        val members = rows.map { it.getJSONObject("task").getString("id") }.sorted()
        val m = JSONObject().put("groupId", groupId)
            .put("groupRootId", rows.first().getString("groupRootId"))
            .put("deletedAt", rows.first().getString("deletedAt"))
            .put("memberIds", JSONArray(members))
        verify(m, trash)
        return JSONObject(m.toString())
    }
}
