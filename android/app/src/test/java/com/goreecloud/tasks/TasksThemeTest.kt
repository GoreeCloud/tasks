package com.goreecloud.tasks

import androidx.compose.ui.graphics.Color
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TasksThemeTest {
    @Test fun freshAndInvalidChoicesStartLightNeutral() {
        assertEquals("light", TasksTheme.appearance(null))
        assertEquals("neutral", TasksTheme.accent(null))
        assertEquals("light", TasksTheme.appearance("system"))
        assertEquals("neutral", TasksTheme.accent("purple"))
        assertEquals("light", TasksTheme.appearance(""))
        assertTrue(TasksTheme.accents.containsAll(listOf("neutral", "moss", "lagoon", "ember", "iris")))
    }

    @Test fun explicitDarkAndAccentUseGCUIReadablePairs() {
        val light = TasksTheme.scheme("light", "neutral")
        assertEquals(Color(0xFF374151), light.primary)
        assertEquals(Color.White, light.onPrimary)
        assertEquals(Color(0xFFECF0F8), light.background)
        val dark = TasksTheme.scheme("dark", "lagoon")
        assertEquals(Color(0xFF89E1E9), dark.primary)
        assertEquals(Color(0xFF003B43), dark.onPrimary)
        assertEquals(Color(0xFF10131E), dark.background)
        val violet = TasksTheme.scheme("light", "iris")
        assertEquals(Color(0xFF5145D9), violet.primary)
        assertEquals(Color(0xFFE8E6FF), violet.primaryContainer)
        assertEquals(Color(0xFF2C227C), violet.onPrimaryContainer)
    }

    @Test fun userAccentNeverChangesLightDarkSemanticSurfaceDefaults() {
        for (accent in TasksTheme.accents) {
            assertEquals(Color(0xFFECF0F8), TasksTheme.scheme("light", accent).background)
            assertEquals(Color(0xFF10131E), TasksTheme.scheme("dark", accent).background)
            assertEquals(Color.White, TasksTheme.scheme("light", accent).onPrimary)
        }
    }
}
