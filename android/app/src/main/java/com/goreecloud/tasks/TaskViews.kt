package com.goreecloud.tasks

import java.time.LocalDate

/** Pure, UI-independent native Android task filtering rules. */
internal object TaskViews {
    val names = listOf("Open", "Today", "Upcoming", "Priority", "Completed", "Project")

    fun select(
        tasks: List<TaskRecord>,
        view: String,
        today: String = LocalDate.now().toString(),
        projectId: String? = null,
        search: String = ""
    ): List<TaskRecord> {
        require(view in names) { "Unknown task view" }
        val query = search.trim()
        return tasks.filter { task ->
            val visible = when (view) {
                "Completed" -> task.completed
                "Today" -> !task.completed && task.dueDate != null && task.dueDate <= today
                "Upcoming" -> !task.completed && task.dueDate != null && task.dueDate > today
                "Priority" -> !task.completed && task.priority <= 2
                "Project" -> !task.completed && task.projectId == projectId
                else -> !task.completed
            }
            visible && (query.isEmpty() || task.title.contains(query, ignoreCase = true))
        }
    }
}
