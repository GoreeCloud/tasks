package com.goreecloud.tasks

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SubtaskRecoveryTest {
    private fun fixture(): JSONObject =
        JSONObject(String(PortableFixture.read("schema4-proposed-synthetic.json"), Charsets.UTF_8))
    private val deletionTime = "2026-11-02T14:00:00Z"

    @Test fun fullThreeLevelDeleteAndRestorePreservesExactMetadata() {
        val original = fixture()
        val before = original.toString()
        val plan = SubtaskRecovery.planDelete(original, emptyList(), "task-notes", deletionTime, "group-1")
        assertEquals(before, original.toString())
        assertEquals(0, plan.workspace.getJSONArray("tasks").length())
        assertEquals(3, plan.trash.size)
        assertTrue(plan.trash.all { it.getInt("groupSize") == 3 })
        val restored = SubtaskRecovery.planRestore(plan.workspace, plan.trash, "group-1")
        assertEquals(original.toString(), restored.workspace.toString())
        assertTrue(restored.trash.isEmpty())
        assertEquals("2026-11-01T01:23:45.654321Z",
            restored.workspace.getJSONArray("tasks").getJSONObject(0).getString("completedAt"))
    }

    @Test fun aChildBranchDoesNotRemoveItsParent() {
        val plan = SubtaskRecovery.planDelete(fixture(), emptyList(),
            "task-empty-notes", deletionTime, "child-1")
        assertEquals(1, plan.workspace.getJSONArray("tasks").length())
        assertEquals("task-notes", plan.workspace.getJSONArray("tasks").getJSONObject(0).getString("id"))
        val restored = SubtaskRecovery.planRestore(plan.workspace, plan.trash, "child-1")
        assertEquals(3, restored.workspace.getJSONArray("tasks").length())
    }

    @Test fun partialGroupOrphanAndCollisionRefuseRecovery() {
        val plan = SubtaskRecovery.planDelete(fixture(), emptyList(),
            "task-empty-notes", deletionTime, "child-1")
        val incomplete = plan.trash.dropLast(1)
        try {
            SubtaskRecovery.planRestore(plan.workspace, incomplete, "child-1")
            fail("Accepted incomplete group")
        } catch (_: IllegalArgumentException) { }
        val orphan = JSONObject(plan.workspace.toString())
        orphan.put("tasks", org.json.JSONArray())
        try {
            SubtaskRecovery.planRestore(orphan, plan.trash, "child-1")
            fail("Accepted orphaned group")
        } catch (_: IllegalArgumentException) { }
        val collided = JSONObject(plan.workspace.toString())
        val alias = JSONObject(plan.trash.last().getJSONObject("task").toString())
        alias.put("parentId", "task-notes")
        collided.getJSONArray("tasks").put(alias)
        try {
            SubtaskRecovery.planRestore(collided, plan.trash, "child-1")
            fail("Accepted ID collision")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun duplicateGroupMissingRootAndInvalidDatesRefuseDeletion() {
        val source=fixture()
        fun refuses(root: String, whenDate: String, group: String, trash: List<JSONObject>) {
            try {
                SubtaskRecovery.planDelete(source, trash, root, whenDate, group)
                fail("Unsafe deletion accepted")
            } catch (_: IllegalArgumentException) { }
        }
        refuses("missing", deletionTime, "fresh", emptyList())
        refuses("task-notes", "invalid", "fresh", emptyList())
        refuses("task-notes", deletionTime, "", emptyList())
        refuses("task-notes", deletionTime, "duplicate",
            listOf(JSONObject().put("groupId", "duplicate")))
        assertEquals(3, source.getJSONArray("tasks").length())
    }
}
