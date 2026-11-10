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

    fun description(value: String): String {
        require(value.length <= 2000 && hasValidSurrogates(value)) {
            "Description must be valid Unicode text, at most 2000 characters"
        }
        return value
    }

    /** Ordered, unique, plain-text labels; compatible with browser and Linux. */
    fun labels(values: List<String>): List<String> {
        require(values.size <= 8) { "Up to 8 labels per task" }
        val seen = mutableSetOf<String>()
        values.forEach { label ->
            require(label.isNotEmpty() && label == label.trim() && label.length <= 32 &&
                hasValidSurrogates(label) && label.none {
                    it == ',' || it.code < 32 || it.code == 127
                } && seen.add(label)) {
                "Labels must be unique 1–32 character text without commas or controls"
            }
        }
        return values.toList()
    }

    fun parseLabels(raw: String): List<String> =
        labels(if (raw.isBlank()) emptyList() else raw.split(',').map { it.trim() })

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
