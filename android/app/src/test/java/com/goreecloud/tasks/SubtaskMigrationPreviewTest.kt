package com.goreecloud.tasks

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SubtaskMigrationPreviewTest {
    @Test fun everySupportedLegacySchemaPreviewsIndependentRoots() {
        for (name in listOf("schema1-synthetic.json", "schema2-synthetic.json", "schema3-synthetic.json")) {
            val original = PortableFixture.read(name)
            val projected = SubtaskMigrationPreview.legacyAsRoots(original)
            assertEquals(4, projected.getInt("schema"))
            val tasks = projected.getJSONArray("tasks")
            assertEquals(PortableRestore.parse(original).tasks.size, tasks.length())
            for (i in 0 until tasks.length()) {
                val task = tasks.getJSONObject(i)
                assertSame(JSONObject.NULL, task.get("parentId"))
                assertTrue(task.has("description"))
                assertTrue(task.has("labels"))
                if (name == "schema1-synthetic.json") assertEquals(0, task.getJSONArray("labels").length())
            }
            if (name == "schema3-synthetic.json") {
                val completed = (0 until tasks.length()).map { tasks.getJSONObject(it) }
                    .first { it.getString("id") == "task-notes" }
                assertEquals("2026-11-01T01:23:45.654321Z",completed.getString("completedAt"))
                assertEquals(listOf("Work", "Design 🧭"),
                    (0 until completed.getJSONArray("labels").length()).map {
                        completed.getJSONArray("labels").getString(it)
                    })
            }
            val graph = SubtaskContract.parseProposed(projected.toString().toByteArray(Charsets.UTF_8))
            assertTrue(graph.depths.values.all { it == 1 })
        }
    }

    @Test fun unsupportedV4InputCannotBeSilentlyRewrittenAsRoots() {
        try {
            SubtaskMigrationPreview.legacyAsRoots(PortableFixture.read("schema4-proposed-synthetic.json"))
            fail("Existing parent graph was silently flattened")
        } catch (_: IllegalArgumentException) { }
    }
}
