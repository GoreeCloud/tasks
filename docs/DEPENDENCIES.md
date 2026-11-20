# Dependency inventory and provenance (development stage)

Review date: November 20, 2026. Do not represent this document as a substitute for a full SBOM, vulnerability scan, legal review or deployment acceptance.

| Component | Purpose | Upstream / reported license | Source |
| --- | --- | --- | --- |
| FastAPI | Typed REST server | MIT | https://github.com/fastapi/fastapi |
| Uvicorn | ASGI server | BSD-3-Clause | https://github.com/encode/uvicorn |
| python-dateutil | Calendar month arithmetic | BSD-3-Clause or Apache-2.0 | https://github.com/dateutil/dateutil |
| SQLite | Local embedded database | Public domain | https://www.sqlite.org/copyright.html |
| React / React DOM | Web rendering | MIT | https://github.com/facebook/react |
| Vite | Web build and dev server | MIT | https://github.com/vitejs/vite |
| TypeScript | Typed JavaScript | Apache-2.0 | https://github.com/microsoft/TypeScript |
| PySide6 (Qt for Python) | Native Linux Qt Quick 6.12 | LGPLv3/GPLv3/commercial and applicable component-specific terms | https://doc.qt.io/qtforpython-6/licenses.html |
| Kotlin / Compose | Native Android UI | Apache-2.0 and upstream-specific | https://github.com/JetBrains/kotlin |
| GoreeCloud UI source | Shared design tokens, Kotlin Compose and Android Expressive adapter | MIT, upstream LICENSE preserved | https://github.com/GoreeCloud/gc-ui |

No external competitor project source is imported. All dependencies are installed by the specified build system; distribution/license compliance remains a separate gate for packaging and downloads. **Pin/review transitive dependencies, generate SBOM, check advisories, verify licenses and scan builds before releases.**

Imported upstream GC UI revision: 42965f8682c22973b4247d58238e68aa63d86523. See vendor/gc-ui/PROVENANCE.md. Product code in this repo does not represent upstream dependencies as original code. Any GPL/LGPL obligations must be fulfilled before distributing Linux installers and associated Qt binaries.
