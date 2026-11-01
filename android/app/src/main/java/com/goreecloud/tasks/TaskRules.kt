package com.goreecloud.tasks

import java.time.LocalDate

/** Shared pure validation for Android task creation and editing. */
internal object TaskRules {
    fun title(value: String): String {
        val cleaned = value.trim()
        require(cleaned.isNotEmpty() && cleaned.length <= 240) {
            "Task title must be 1–240 characters"
        }
        return cleaned
    }

    fun priority(value: Int): Int {
        require(value in 1..4) { "Priority must be P1–P4" }
        return value
    }

    fun due(value: String?): String? {
        if (value == null || value.isBlank()) return null
        require(LocalDate.parse(value).toString() == value) {
            "Due date must be a valid ISO calendar date"
        }
        return value
    }
}
