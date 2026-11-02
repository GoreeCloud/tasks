package com.goreecloud.tasks

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Pure manifest tests; no local database, user records or production migration. */
class SubtaskGroupManifestTest {
    private fun plan(): SubtaskRecoveryPlan {
        val source = JSONObject(String(PortableFixture.read("schema4-proposed-synthetic.json"), Charsets.UTF_8))
        return SubtaskRecovery.planDelete(source, emptyList(), "task-notes", "2026-11-02T14:00:00Z", "g-1")
    }

    @Test fun capturesThreeLevelGroupWithoutChangingTrash() {
        val p=plan()
        val before=p.trash.map { it.toString() }
        val m=SubtaskGroupManifest.create(p.trash,"g-1")
        assertTrue(SubtaskGroupManifest.verify(m,p.trash))
        assertEquals(3,m.getJSONArray("memberIds").length())
        assertEquals(before,p.trash.map { it.toString() })
    }

    @Test fun survivingCountsCannotHideMissingGrandchild() {
        val p=plan()
        val m=SubtaskGroupManifest.create(p.trash,"g-1")
        val damaged=p.trash.filter { it.getJSONObject("task").getString("id") != "task-grandchild" }
            .map { JSONObject(it.toString()).put("groupSize",2) }
        try {
            SubtaskGroupManifest.verify(m,damaged)
            fail("Accepted incomplete group")
        } catch (_: IllegalArgumentException) { }
        assertTrue(SubtaskGroupManifest.verify(m,p.trash))
    }

    @Test fun swappedMemberAndRootAreRejected() {
        val p=plan()
        val m=SubtaskGroupManifest.create(p.trash,"g-1")
        val bad=JSONObject(m.toString()).put("groupRootId","not-a-root")
        try { SubtaskGroupManifest.verify(bad,p.trash); fail("Changed root") }
        catch (_: IllegalArgumentException) { }
    }
}
