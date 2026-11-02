package com.goreecloud.tasks

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SubtaskContractTest {
    private fun source(): JSONObject =
        JSONObject(String(PortableFixture.read("schema4-proposed-synthetic.json"), Charsets.UTF_8))

    private fun reject(change: (JSONObject) -> Unit) {
        val snapshot = source()
        change(snapshot)
        try {
            SubtaskContract.parseProposed(snapshot.toString().toByteArray(Charsets.UTF_8))
            fail("Invalid proposed graph accepted")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun validatesThreeLevelsWithoutEnablingProductionRestore() {
        val bytes = PortableFixture.read("schema4-proposed-synthetic.json")
        val graph = SubtaskContract.parseProposed(bytes)
        assertEquals(3, graph.validated.tasks.size)
        assertEquals(1, graph.depths["task-notes"])
        assertEquals(2, graph.depths["task-empty-notes"])
        assertEquals(3, graph.depths["task-grandchild"])
        assertEquals(listOf("Work", "Design 🧭"), graph.validated.tasks.first().labels)
        try {
            PortableRestore.parse(bytes)
            fail("Production importer must reject v4")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun refusesMissingParentsCyclesCrossProjectAndInvalidFields() {
        reject { it.getJSONArray("tasks").getJSONObject(1).put("parentId", "absent") }
        reject { it.getJSONArray("tasks").getJSONObject(0).put("parentId", "task-grandchild") }
        reject { it.getJSONArray("tasks").getJSONObject(1).put("parentId", "task-empty-notes") }
        reject { it.getJSONArray("tasks").getJSONObject(1).put("projectId", JSONObject.NULL) }
        reject { it.getJSONArray("tasks").getJSONObject(1).remove("parentId") }
        reject { it.getJSONArray("tasks").getJSONObject(1).put("parentId", 23) }
        reject { it.getJSONArray("tasks").getJSONObject(0).put("priority", 5) }
    }

    @Test fun enforcesDepthAndPerProjectCap() {
        reject {
            val list = it.getJSONArray("tasks")
            val fourth = JSONObject(list.getJSONObject(2).toString())
            fourth.put("id", "fourth")
            fourth.put("parentId", "task-grandchild")
            list.put(fourth)
        }
        reject {
            val list = it.getJSONArray("tasks")
            repeat(299) { n ->
                val extra = JSONObject(list.getJSONObject(1).toString())
                extra.put("id", "extra-$n")
                list.put(extra)
            }
        }
    }
}
