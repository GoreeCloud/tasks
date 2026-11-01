/* Local GoreeCloud UI theme preference controller.
 * Runs before CSS to avoid a dark/incorrect-accent first paint.
 * Scope is appearance only; does not read/write task data or backups. */
(function (root) {
  'use strict';
  const MODES = Object.freeze(['light', 'dark']);
  const ACCENTS = Object.freeze(['neutral', 'lagoon', 'moss', 'ember', 'iris', 'ocean']);
  const PREF_KEY = 'goreecloud.tasks.ui.v1';
  const MODE_KEY = 'goreecloud.tasks.appearance';
  const ACCENT_KEY = 'goreecloud.tasks.accent';
  const LEGACY_MODE_KEY = 'goreecloud.tasks.theme';
  const normalized = (value, accepted, fallback) => accepted.includes(value) ? value : fallback;
  function read() {
    let mode = 'light', accent = 'neutral';
    try {
      const storage = window.localStorage;
      const packed = storage.getItem(PREF_KEY);
      if (packed !== null && packed.length <= 512) {
        const parsed = JSON.parse(packed);
        if (parsed && typeof parsed === 'object') return {
          mode: normalized(parsed.mode, MODES, 'light'),
          accent: normalized(parsed.accent, ACCENTS, 'neutral')
        };
      }
      const explicit = storage.getItem(MODE_KEY);
      // Preserve an earlier explicit dark/light choice without rewriting it.
      mode = normalized(explicit === null ? storage.getItem(LEGACY_MODE_KEY) : explicit,
        MODES, 'light');
      accent = normalized(storage.getItem(ACCENT_KEY), ACCENTS, 'neutral');
    } catch { /* Private mode: keep an in-memory, light/neutral fallback. */ }
    return { mode, accent };
  }
  function apply(next) {
    root.dataset.theme = next.mode;
    root.dataset.mode = next.mode; // Existing GC UI responsive styles use this hook.
    root.dataset.gcAccent = next.accent;
    root.style.colorScheme = next.mode;
    const chrome = document.querySelector?.('meta[name="theme-color"]');
    if (chrome) chrome.setAttribute('content', next.mode === 'dark' ? '#10131e' : '#ecf0f8');
  }
  function save(mode, accent) {
    const next = { mode: normalized(mode, MODES, 'light'),
      accent: normalized(accent, ACCENTS, 'neutral') };
    // Apply immediately; if storage is unavailable, the preference is session-only.
    apply(next);
    try {
      const storage = window.localStorage;
      storage.setItem(PREF_KEY, JSON.stringify(next));
      return true;
    } catch { return false; }
  }
  apply(read());
  window.GoreeTasksTheme = Object.freeze({ read, apply, save, MODES, ACCENTS });
})(document.documentElement);
