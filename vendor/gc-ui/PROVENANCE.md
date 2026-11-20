# GoreeCloud UI vendor provenance

- **Upstream:** https://github.com/GoreeCloud/gc-ui
- **Exact reviewed snapshot:** `42965f8682c22973b4247d58238e68aa63d86523` (2026-11-20)
- **License:** MIT, unmodified, at `vendor/gc-ui/LICENSE`; copyright (c) 2026 GoreeCloud.
- **Included files:** `compose-multiplatform/`, `android/material3-expressive/`, `gc.tokens.json`, CSS token/component snapshots in `web/src/vendor/gc-ui/`.
- **Purpose:** Committed, reproducible build dependencies and approved design tokens, not fictitious published Maven packages. Android uses the actual modules in Gradle composite source builds; Material 3 Expressive is the outer theme.
- **Known limits:** Upstream alpha and no automatic upstream update. Before refresh, review code, license, dependencies, vulnerabilities, token generation, interoperability and consumer builds. Upstream is the design authority; local snapshots may lag. No native runtime/accessibility certification is implied.
