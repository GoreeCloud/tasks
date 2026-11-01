package com.goreecloud.tasks

import org.junit.Assert.assertEquals
import org.junit.Test

class TaskViewsTest {
    private val tasks = listOf(
        TaskRecord("a", "Overdue project", 1, false, "2026-10-29", "p"),
        TaskRecord("b", "Later task", 4, false, "2026-11-04", null),
        TaskRecord("c", "Finished", 2, true, null, null),
        TaskRecord("d", "Inbox item", 4, false, null, null)
    )

    @Test fun filtersTodayUpcomingAndCompleted() {
        assertEquals(listOf("a"), TaskViews.select(tasks, "Today", "2026-10-31").map { it.id })
        assertEquals(listOf("b"), TaskViews.select(tasks, "Upcoming", "2026-10-31").map { it.id })
        assertEquals(listOf("c"), TaskViews.select(tasks, "Completed", "2026-10-31").map { it.id })
    }

    @Test fun projectAndSearchFiltersAreExact() {
        assertEquals(listOf("a"), TaskViews.select(tasks, "Project", "2026-10-31", "p").map { it.id })
        assertEquals(listOf("b", "d"), TaskViews.select(tasks, "Project", "2026-10-31").map { it.id })
        assertEquals(listOf("b"), TaskViews.select(tasks, "Open", "2026-10-31", search = "later").map { it.id })
        assertEquals(listOf("a"), TaskViews.select(tasks, "Priority", "2026-10-31").map { it.id })
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnknownView() {
        TaskViews.select(tasks, "Unimplemented", "2026-10-31")
    }
}
