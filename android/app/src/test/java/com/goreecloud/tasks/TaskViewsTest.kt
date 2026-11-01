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


    @Test fun dueViewsAgreeOnSevenCalendarDaysAndExcludeCompleted() {
        val cases = listOf(
            TaskRecord("before", "Before", 1, false, "2026-10-31", null),
            TaskRecord("today", "Today", 2, false, "2026-11-01", null),
            TaskRecord("end", "Sixth day", 3, false, "2026-11-07", null),
            TaskRecord("beyond", "Seventh day", 4, false, "2026-11-08", null),
            TaskRecord("undated", "Undated", 1, false, null, null),
            TaskRecord("done", "Completed", 1, true, "2026-11-04", null)
        )
        assertEquals(listOf("before"),
            TaskViews.select(cases, "Overdue", "2026-11-01").map { it.id })
        assertEquals(listOf("before", "today"),
            TaskViews.select(cases, "Today", "2026-11-01").map { it.id })
        assertEquals(listOf("today", "end"),
            TaskViews.select(cases, "Next 7 days", "2026-11-01").map { it.id })
        assertEquals(listOf("end", "beyond"),
            TaskViews.select(cases, "Upcoming", "2026-11-01").map { it.id })
        assertEquals(listOf("end"),
            TaskViews.select(cases, "Next 7 days", "2026-11-01", search = "Sixth").map { it.id })
    }

    @Test fun priorityAndSortFiltersUseOnlyKnownModes() {
        assertEquals(listOf("a"), TaskViews.select(tasks, "Open", "2026-10-31",
            priorityFilter = 1).map { it.id })
        assertEquals(listOf("a", "b", "d"), TaskViews.select(tasks, "Open", "2026-10-31",
            sortBy = "Due date").map { it.id })
        assertEquals(listOf("d", "b", "a"), TaskViews.select(tasks, "Open", "2026-10-31",
            sortBy = "Title").map { it.id })
        assertEquals(listOf("a", "b", "d"), TaskViews.select(tasks, "Open", "2026-10-31").map { it.id })
        try {
            TaskViews.select(tasks, "Open", priorityFilter = 5)
            throw AssertionError("Invalid priority was accepted")
        } catch (_: IllegalArgumentException) { }
        try {
            TaskViews.select(tasks, "Open", sortBy = "SELECT * FROM tasks")
            throw AssertionError("Invalid sort was accepted")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun dueViewsCrossYearBoundary() {
        val dates = listOf(
            TaskRecord("a", "December", 3, false, "2026-12-31", null),
            TaskRecord("b", "January", 2, false, "2027-01-04", null),
            TaskRecord("c", "Beyond", 1, false, "2027-01-05", null)
        )
        assertEquals(listOf("a", "b"),
            TaskViews.select(dates, "Next 7 days", "2026-12-29").map { it.id })
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnknownView() {
        TaskViews.select(tasks, "Unimplemented", "2026-10-31")
    }
}
