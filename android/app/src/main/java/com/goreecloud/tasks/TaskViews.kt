package com.goreecloud.tasks

import java.time.LocalDate

/** Pure, UI-independent native Android task filtering rules. */
internal object TaskViews {
    val names = listOf("Open", "Today", "Next 7 days", "Overdue", "Upcoming", "Priority", "Completed", "Project")

    /** Search deleted task titles and notes; leave Trash ordering and recovery untouched. */
    fun selectTrash(tasks: List<TaskRecord>, search: String = ""): List<TaskRecord> {
        val query = search.trim()
        return if (query.isEmpty()) tasks else tasks.filter { task ->
            task.title.contains(query, ignoreCase = true) ||
                task.description.contains(query, ignoreCase = true)
        }
    }

    fun select(
        tasks: List<TaskRecord>,
        view: String,
        today: String = LocalDate.now().toString(),
        projectId: String? = null,
        search: String = "",
        priorityFilter: Int? = null,
        sortBy: String = "Smart"
    ): List<TaskRecord> {
        require(view in names) { "Unknown task view" }
        require(priorityFilter == null || priorityFilter in 1..4) { "Invalid priority filter" }
        require(sortBy in listOf("Smart", "Due date", "Title")) { "Unknown task sort" }
        val query = search.trim()
        // Include today through the sixth following date; use calendar arithmetic,
        // not elapsed milliseconds, to remain stable across daylight-saving time.
        val weekEnd = if (view == "Next 7 days") LocalDate.parse(today).plusDays(6).toString() else null
        val filtered = tasks.filter { task ->
            val visible = when (view) {
                "Completed" -> task.completed
                "Today" -> !task.completed && task.dueDate != null && task.dueDate <= today
                "Overdue" -> !task.completed && task.dueDate != null && task.dueDate < today
                "Next 7 days" -> !task.completed && task.dueDate != null &&
                    task.dueDate >= today && task.dueDate <= weekEnd!!
                "Upcoming" -> !task.completed && task.dueDate != null && task.dueDate > today
                "Priority" -> !task.completed && task.priority <= 2
                "Project" -> !task.completed && task.projectId == projectId
                else -> !task.completed
            }
            visible && (priorityFilter == null || task.priority == priorityFilter) &&
                (query.isEmpty() || task.title.contains(query, ignoreCase = true) ||
                    task.description.contains(query, ignoreCase = true))
        }
        return when (sortBy) {
            "Due date" -> filtered.sortedWith(compareBy<TaskRecord> { it.dueDate ?: "9999-12-31" }
                .thenBy { it.priority }.thenBy { it.title.lowercase(java.util.Locale.ROOT) })
            "Title" -> filtered.sortedWith(compareBy<TaskRecord> { it.title.lowercase(java.util.Locale.ROOT) }
                .thenBy { it.priority })
            else -> filtered  // Keep the existing on-device SQL ordering.
        }
    }
}
