package com.goreecloud.tasks

import java.time.LocalDate

/** Shared pure validation for Android task creation and editing. */
internal object TaskRules {
    private fun hasValidSurrogates(value: String): Boolean {
        var index = 0
        while (index < value.length) {
            val current = value[index]
            if (Character.isHighSurrogate(current)) {
                if (index + 1 >= value.length || !Character.isLowSurrogate(value[index + 1])) {
                    return false
                }
                index += 2
            } else if (Character.isLowSurrogate(current)) {
                return false
            } else {
                index++
            }
        }
        return true
    }

    fun projectName(value: String): String {
        val cleaned = value.trim()
        require(cleaned.isNotEmpty() && cleaned.length <= 100 && hasValidSurrogates(cleaned)) {
            "Project name must be 1–100 valid Unicode characters"
        }
        return cleaned
    }

    fun title(value: String): String {
        val cleaned = value.trim()
        require(cleaned.isNotEmpty() && cleaned.length <= 240 && hasValidSurrogates(cleaned)) {
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
