package com.goreecloud.tasks

import java.io.ByteArrayInputStream
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Offline parser contract tests; no Android device, app data or credentials. */
class PortableRestoreTest {
    private fun fixture() = """
        {
          "schema": 1,
          "projects": [{"id":"project-1","name":"Roadmap 🚀"}],
          "tasks": [
            {
              "id":"task-1","title":"Plan 🚀","priority":2,"completed":false,
              "due":"2026-11-09","projectId":"project-1",
              "createdAt":"2026-10-31T18:00:00.000Z","completedAt":null
            },
            {
              "id":"task-2","title":"Release","priority":1,"completed":true,
              "due":"","projectId":null,
              "createdAt":"2026-10-30T00:00:00Z",
              "completedAt":"2026-10-31T12:10:11.123+00:00"
            }
          ]
        }
    """.trimIndent()

    private fun parse(text: String = fixture()) = PortableRestore.parse(text.toByteArray(Charsets.UTF_8))

    @Test fun sharedTimestampContractRejectsImpossibleAndNonportableDates() {
        val contract = JSONObject(String(PortableFixture.read("timestamp-contract.json"), Charsets.UTF_8))
        val base = "2026-10-31T18:00:00.000Z"
        val accepted = contract.getJSONArray("valid")
        for (index in 0 until accepted.length()) {
            val timestamp = accepted.getString(index)
            val parsed = parse(fixture().replace(base, timestamp))
            assertEquals(timestamp, parsed.tasks[0].createdAtExact)
        }
        val rejected = contract.getJSONArray("invalid")
        for (index in 0 until rejected.length()) {
            val timestamp = rejected.getString(index)
            rejects(fixture().replace(base, timestamp))
        }
    }

    @Test fun sharedPortableContractIsLosslessIncludingUnicodeAndOffsets() {
        val bytes = PortableFixture.read()
        val parsed = PortableRestore.parse(bytes)
        assertEquals(2, parsed.projects.size)
        assertEquals(3, parsed.tasks.size)
        assertEquals("Roadmap 🚀", parsed.projects[0].name)
        assertEquals("Review release ✅", parsed.tasks[0].title)
        assertEquals("2026-10-31T20:15:42.123456-05:00", parsed.tasks[0].createdAtExact)
        assertEquals("2026-11-01T01:23:45.654321Z", parsed.tasks[0].completedAtExact)
        assertEquals("Buy groceries 🥦", parsed.tasks[1].title)
        assertEquals("2026-11-12", parsed.tasks[1].dueDate)
        assertNull(parsed.tasks[2].projectId)
    }

    @Test fun validBrowserLinuxSchemaPreservesTaskMetadata() {
        val snapshot = parse()
        assertEquals(1, snapshot.projects.size)
        assertEquals("Roadmap 🚀", snapshot.projects[0].name)
        assertEquals(2, snapshot.tasks.size)
        assertEquals("Plan 🚀", snapshot.tasks[0].title)
        assertEquals("2026-11-09", snapshot.tasks[0].dueDate)
        assertEquals("project-1", snapshot.tasks[0].projectId)
        assertNull(snapshot.tasks[0].completedAt)
        assertTrue(snapshot.tasks[1].completed)
        assertTrue(requireNotNull(snapshot.tasks[1].completedAt) > snapshot.tasks[1].createdAt)
        assertEquals(2, PortableRestore.readLimited(
            ByteArrayInputStream(byteArrayOf(1, 2))).size)
    }

    @Test fun acceptsSchema2DescriptionsAndRejectsBadUnicodeAndDowngrade() {
        val fixture = PortableFixture.read("schema2-synthetic.json")
        val restored = PortableRestore.parse(fixture)
        assertEquals(2, restored.tasks.size)
        assertEquals("Check accessibility 🧭\nFollow up on copy edits.",
            restored.tasks.single { it.id == "task-notes" }.description)
        assertEquals("", restored.tasks.single { it.id == "task-empty-notes" }.description)
        val root = JSONObject(String(fixture, Charsets.UTF_8))
        root.put("schema", 1)
        rejects(root.toString()) // schema 1 must not drop descriptions
        root.put("schema", 2)
        root.getJSONArray("tasks").getJSONObject(0).remove("description")
        rejects(root.toString()) // schema 2 requires explicit notes field
        root.getJSONArray("tasks").getJSONObject(0).put("description", "🧭".repeat(1001))
        rejects(root.toString()) // UTF-16 2000-unit cap
    }

    private fun rejects(text: String) {
        try {
            parse(text)
            throw AssertionError("Unexpectedly accepted malformed portable backup")
        } catch (_: IllegalArgumentException) {
            // Entire input must fail before the database is ever opened for writing.
        }
    }

    @Test fun preservesLinuxMicrosecondPrecisionAndTimezoneOffsets() {
        val restored = parse(fixture()
            .replace("2026-10-31T18:00:00.000Z", "2026-10-31T18:00:00.123456+00:00")
            .replace("2026-10-31T12:10:11.123+00:00", "2026-10-31T12:10:11.123456+00:00"))
        assertEquals("2026-10-31T18:00:00.123456+00:00", restored.tasks[0].createdAtExact)
        assertEquals("2026-10-31T12:10:11.123456+00:00", restored.tasks[1].completedAtExact)
        assertEquals("2026-10-31T18:00:00.123456+00:00",
            PortableBackup.timestampForExport(restored.tasks[0].createdAt,
                                              restored.tasks[0].createdAtExact))
    }

    @Test fun rejectsUnsupportedAndIncompleteSchema() {
        rejects(fixture().replace("\"schema\": 1", "\"schema\": 3"))
        rejects(fixture().replace("\"tasks\": [", "\"missing\": ["))
        rejects(fixture().replace("\"priority\":2", "\"priority\":true"))
        rejects(fixture().replace("\"completed\":false", "\"completed\":0"))
        rejects(fixture().replace("\"projectId\":null", "\"missingProject\":null"))
    }

    @Test fun rejectsInvalidReferencesDuplicatesAndBrokenDates() {
        rejects(fixture().replace("\"projectId\":\"project-1\"", "\"projectId\":\"missing\""))
        rejects(fixture().replace("\"id\":\"task-2\"", "\"id\":\"task-1\""))
        rejects(fixture().replace("2026-11-09", "2026-02-30"))
        rejects(fixture().replace("\"completedAt\":null",
                                   "\"completedAt\":\"2026-10-31T00:00:00Z\""))
        rejects(fixture().replace("2026-10-31T12:10:11.123+00:00",
                                   "2026-13-31T12:10:11.123456Z"))
    }

    @Test fun rejectsInvalidUnicodeControlAndPadding() {
        rejects(fixture().replace("Plan 🚀", "Bad " + "\\" + "ud800"))
        rejects(fixture().replace("\"task-1\"", "\"bad\\u0001id\""))
        rejects(fixture().replace("Plan 🚀", "  whitespace  "))
        rejects(fixture() + " INVALID TRAILER")
    }

    @Test fun refusesOversizedAndMalformedUtf8Inputs() {
        try {
            PortableRestore.readLimited(
                ByteArrayInputStream(ByteArray(PortableBackup.MAX_BYTES + 1)))
            throw AssertionError("Oversized stream should be rejected")
        } catch (_: IllegalArgumentException) { }
        try {
            PortableRestore.parse(byteArrayOf(0xC3.toByte(), 0x28))
            throw AssertionError("Malformed UTF-8 should be rejected")
        } catch (_: IllegalArgumentException) { }
    }
}
