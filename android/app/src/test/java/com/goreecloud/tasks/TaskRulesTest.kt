package com.goreecloud.tasks

import org.junit.Assert.assertEquals
import org.junit.Test

class TaskRulesTest {
    @Test fun normalizesTitleAndDate() {
        assertEquals("Take action", TaskRules.title("  Take action  "))
        assertEquals("2028-02-29", TaskRules.due("2028-02-29"))
        assertEquals(null, TaskRules.due(""))
        assertEquals(null, TaskRules.due(null))
    }

    @Test fun preservesEmojiInNativeNames() {
        assertEquals("Plan 🚀", TaskRules.title("  Plan 🚀  "))
        assertEquals("Launch 🎯", TaskRules.projectName(" Launch 🎯 "))
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnpairedTaskSurrogate() {
        TaskRules.title("bad " + 0xD800.toChar())
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnpairedProjectSurrogate() {
        TaskRules.projectName("bad " + 0xDC00.toChar())
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsEmptyTitle() { TaskRules.title("  ") }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsExcessiveTitle() { TaskRules.title("x".repeat(241)) }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsBadPriority() { TaskRules.priority(0) }

    @Test(expected = java.time.format.DateTimeParseException::class)
    fun rejectsInvalidCalendarDate() { TaskRules.due("2026-02-30") }
}
