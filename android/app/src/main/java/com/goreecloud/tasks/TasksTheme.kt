package com.goreecloud.tasks

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

/**
 * GC UI semantic palette pairs, from the first-party offline snapshot.
 * The product has no default purple accent; explicit user choices win.
 * First-launch appearance is always Light regardless of the Android OS setting.
 */
internal object TasksTheme {
    val appearances = listOf("light", "dark")
    val accents = listOf("neutral", "lagoon", "moss", "ember", "ocean", "iris")

    fun appearance(raw: String?): String = if (raw in appearances) raw!! else "light"
    fun accent(raw: String?): String = if (raw in accents) raw!! else "neutral"

    private data class Roles(
        val primary: Color, val onPrimary: Color,
        val container: Color, val onContainer: Color
    )

    private fun roles(name: String, dark: Boolean): Roles {
        return when (accent(name)) {
            "lagoon" -> if (dark)
                Roles(Color(0xFF89E1E9), Color(0xFF003B43), Color(0xFF1C4D57), Color(0xFFC8FCFF))
            else Roles(Color(0xFF087C8D), Color.White, Color(0xFFD1F4F5), Color(0xFF07565D))
            "moss" -> if (dark)
                Roles(Color(0xFFA6DFA9), Color(0xFF224B2A), Color(0xFF304E37), Color(0xFFE8F8E9))
            else Roles(Color(0xFF3F744B), Color.White, Color(0xFFD8F1D9), Color(0xFF25542D))
            "ember" -> if (dark)
                Roles(Color(0xFFFFC2AD), Color(0xFF592A20), Color(0xFF603C36), Color(0xFFFFE9E0))
            else Roles(Color(0xFFAE4D3F), Color.White, Color(0xFFFFE2D7), Color(0xFF6E3024))
            "ocean" -> if (dark)
                Roles(Color(0xFF93C5FD), Color(0xFF172554), Color(0xFF1E3A8A), Color(0xFFDBEAFE))
            else Roles(Color(0xFF1D4ED8), Color.White, Color(0xFFDBEAFE), Color(0xFF1E3A8A))
            "iris" -> if (dark)
                Roles(Color(0xFFC5BFFF), Color(0xFF241B66), Color(0xFF39316B), Color(0xFFEBE8FF))
            else Roles(Color(0xFF5145D9), Color.White, Color(0xFFE8E6FF), Color(0xFF2C227C))
            else -> if (dark)
                Roles(Color(0xFFD1D5DB), Color(0xFF111827), Color(0xFF374151), Color(0xFFF9FAFB))
            else Roles(Color(0xFF374151), Color.White, Color(0xFFE5E7EB), Color(0xFF111827))
        }
    }

    fun scheme(mode: String, accent: String): ColorScheme {
        val dark = appearance(mode) == "dark"
        val role = roles(accent, dark)
        return if (dark) darkColorScheme(
            primary = role.primary, onPrimary = role.onPrimary,
            primaryContainer = role.container, onPrimaryContainer = role.onContainer,
            background = Color(0xFF10131E), onBackground = Color(0xFFF2F2FA),
            surface = Color(0xFF1D2231), onSurface = Color(0xFFF2F2FA),
            surfaceVariant = Color(0xFF292F40), onSurfaceVariant = Color(0xFFB3B9CF),
            outline = Color(0xFF747C99),
            error = Color(0xFFFFB5BE), onError = Color(0xFF5B1827)
        ) else lightColorScheme(
            primary = role.primary, onPrimary = role.onPrimary,
            primaryContainer = role.container, onPrimaryContainer = role.onContainer,
            background = Color(0xFFECF0F8), onBackground = Color(0xFF20243A),
            surface = Color(0xFFF9FAFD), onSurface = Color(0xFF20243A),
            surfaceVariant = Color(0xFFE5EBF6), onSurfaceVariant = Color(0xFF5F657B),
            outline = Color(0xFF8990A7),
            error = Color(0xFFA73549), onError = Color.White
        )
    }
}
