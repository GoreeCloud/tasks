package com.goreecloud.tasks

import org.junit.Assert.assertEquals
import org.junit.Test

/** Pure validation tests; no Android filesystem, provider, or user data. */
class PortableBackupTest {
    @Test fun preservesExactEpochMillisecondsAsUtcIsoTimestamp() {
        assertEquals("1970-01-01T00:00:00.001Z", PortableBackup.timestamp(1L))
        assertEquals("2026-01-01T00:00:00Z", PortableBackup.timestamp(1767225600000L))
    }

    @Test(expected = IllegalArgumentException::class)
    fun refusesUnknownCreationTimestamp() {
        PortableBackup.timestamp(0)
    }

    @Test(expected = IllegalArgumentException::class)
    fun refusesLegacyCompletedTaskWithoutCompletionTime() {
        PortableBackup.completionTimestamp(true, null)
    }

    @Test(expected = IllegalArgumentException::class)
    fun refusesIncompleteTaskWithStaleCompletionTime() {
        PortableBackup.completionTimestamp(false, 1L)
    }

    @Test fun preservesAccurateCompletionInstant() {
        assertEquals("1970-01-01T00:00:00.001Z",
            PortableBackup.completionTimestamp(true, 1L))
    }
}
