package com.goreecloud.tasks

import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

/** Isolated schema-4 reference: NOT wired to live task data or user actions. */
internal object SubtaskGroupManifest {
    private fun digest(task: JSONObject): String = MessageDigest.getInstance("SHA-256")
        .digest(task.toString().toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(it.toInt() and 0xff) }

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
        val signatures = m.opt("memberDigests") as? JSONArray
            ?: throw IllegalArgumentException("Missing content digests")
        require(signatures.length() == members.size)
        val expectedDigests = (0 until signatures.length()).map { index ->
            signatures.opt(index) as? String ?: throw IllegalArgumentException("Invalid digest")
        }
        require(expectedDigests.all { Regex("^[a-f0-9]{64}$").matches(it) })
        val rows = trash.filter { it.optString("groupId") == groupId }
        require(rows.size == members.size) { "Manifest count mismatch" }
        val ids = rows.map { (it.opt("task") as? JSONObject)?.optString("id") ?: "" }.sorted()
        require(ids == members) { "Manifest member mismatch" }
        require(rows.all {
            it.optString("groupRootId") == root && it.optString("deletedAt") == date &&
                it.opt("groupSize") is Int && it.getInt("groupSize") == members.size
        }) { "Manifest metadata mismatch" }
        val byId = rows.associateBy { it.getJSONObject("task").getString("id") }
        val actualDigests = members.map { digest(byId.getValue(it).getJSONObject("task")) }
        require(actualDigests == expectedDigests) { "Manifest content digest mismatch" }
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
            .put("memberDigests", JSONArray(members.map { id ->
                digest(rows.single { it.getJSONObject("task").getString("id") == id }.getJSONObject("task"))
            }))
        verify(m, trash)
        return JSONObject(m.toString())
    }
}
