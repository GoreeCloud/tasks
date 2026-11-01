# GC UI appearance integration — GoreeCloud Tasks

**Status:** Development branch; no Stable/release or visual acceptance claim.

The default is **Light + Neutral** rather than OS-Dark or Iris violet. Each of the browser, GTK4 and Compose clients offers explicit Light/Dark and Neutral, Lagoon, Moss, Ember, Ocean, Iris accents. The foreground/on-color roles come from the GC UI product-theme contract, not an app-invented palette. No automatic system-following mode is enabled.

**Browser:** `theme-bootstrap.js` loads before CSS; the UI uses the GC UI semantic snapshot with `theme-overrides.css`. Source: `GoreeCloud/gc-ui/integrations/themes/gc-app-semantic.css` at revision `ec72b5a5759adbcb22c31f455d29479c509dd542`, copied SHA-256 `e3885c2df30fa02ad98c915d8be44d27f0d45387d4c44742a41b30dfa237cede`. Browser appearance/accent settings are stored separately from tasks. Existing explicit legacy Light/Dark choice is retained until changed; invalid settings fall back safely.

**Android:** `TasksTheme.kt` maps the same GC UI role pairs to Compose. Explicit choices live in device-private SharedPreferences, not task SQLite. **Linux:** `theme.py` stores validated preferences in a private, atomically written XDG config file and applies libadwaita Light/Dark schemes with theme-specific GTK CSS.

**Verification:** Run `node --test web/*.test.mjs`, `python3 -m unittest discover -s linux/tests -q`, `xvfb-run -a /usr/bin/python3 linux/tests/gui_smoke.py`, and GitHub Actions Android Gradle tests/build. Theme-specific tests cover defaults, valid choices, persistence, invalid preferences and refusal of symlinked Linux configuration. The GTK smoke uses a disposable data/config profile.

**Boundaries:** No new task fields, portable backup schema, storage migration, network permissions, synchronization or deployment. Visual, high-contrast, zoom/reflow, keyboard, screen-reader, Android-device theme persistence and all-platform preference acceptance remain open. Native accent preferences are device-local and do not sync.
