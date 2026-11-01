package com.goreecloud.tasks

/**
 * UI-only routing for the first-party Compose client. Does not change the
 * task database, the portable backup format or shared repository state.
 */
internal object TasksNavigation {
    fun tabFor(view: String): String = when (view) {
        "Open" -> "Inbox"
        "Today" -> "Today"
        else -> "Browse"
    }

    fun title(view: String, projectName: String): String = when (view) {
        "Open" -> "Inbox"
        "Project" -> projectName
        else -> view
    }
}
