package com.goreecloud.tasks

import org.junit.Assert.assertEquals
import org.junit.Test

/** Pure validation tests; no Android filesystem, provider, or user data. */
class PortableBackupTest {
    @Test fun preservesExactEpochMillisecondsAsUtcIsoTimestamp() {
        assertEquals("1970-01-01T00:00:00.001Z", PortableBackup.timestamp(1L))
        assertEquals("2026-01-01T00:00:00Z", PortableBackup.timestamp(1767225600000L))
    }

    @Test fun previouslyImportedTimestampWithoutSecondsExportsAsRecoverableIso() {
        // OffsetDateTime accepted this in older builds, while portable
        // browser/Linux backups require explicit seconds.
        val old = "2026-11-01T12:00Z"
        val millis = java.time.OffsetDateTime.parse(old).toInstant().toEpochMilli()
        val normalized = PortableBackup.timestampForExport(millis, old)
        assertEquals("2026-11-01T12:00:00Z", normalized)
        assertEquals(true, PortableRestore.isPortableTimestamp(normalized))
    }

    @Test fun originalTimestampRoundTripsWithoutLosingMicroseconds() {
        val original = "2026-10-31T18:00:00.123456+00:00"
        val millis = java.time.OffsetDateTime.parse(original).toInstant().toEpochMilli()
        assertEquals(original, PortableBackup.timestampForExport(millis, original))
        assertEquals(PortableBackup.timestamp(millis),
            PortableBackup.timestampForExport(millis, null))
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsMismatchedStoredTimestamp() {
        PortableBackup.timestampForExport(1L, "2026-10-31T00:00:00.123456Z")
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
