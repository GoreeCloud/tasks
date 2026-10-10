# GoreeCloud Tasks

**GoreeCloud Tasks** is GoreeCloud's in-development, self-hostable task-management application and intended long-term alternative to Todoist.

## Current development status

**Fork-to-Native — Development / not Stable.** This repository imports the Vikunja v2.7 development snapshot and starts the controlled migration to a distinct GoreeCloud experience. It is **not** a completed native rebuild, accepted deployment, production service, or approved replacement for Todoist.

## Foundation

- Vikunja task engine and applications: task management, projects, subtasks, labels, dates, recurring work, filters, views, sharing, import/export, and platform clients inherited from upstream; each workflow requires GoreeCloud regression validation.
- First GoreeCloud changes: product naming in the web application, an original text-based wordmark in place of the upstream navigation logo, a self-hosted/server-first desktop login, and an initial Glaze token-based visual layer.
- The first Glaze layer is an **integration candidate**, not a claim of full Glaze conformance.
- Upstream's unattended GitHub workflows are not imported; GoreeCloud-owned, least-privilege safety checks replace them.

## Development

The imported code retains the upstream application structure, toolchain, and legacy compatibility identifiers. See [upstream documentation](https://vikunja.io/docs/development/) for build dependencies during the transition.

- Frontend: `cd frontend && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test:unit`
- Backend: `go test ./...` (integration tests may require configured dependencies)
- Production deployment is **not authorized by this README**. Configuration and safety gates must be reviewed first.

## Governance and migration

See [Upstream provenance](UPSTREAM.md), [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md), and [Todoist migration gate](docs/TODOIST_MIGRATION.md). The current live task authority remains the designated Todoist/legacy transition source until full verified GoreeCloud Tasks Stable migration and governance cutover.

## Licensing

Vikunja-derived source is primarily **AGPL-3.0-or-later**; its `desktop/` component is **GPL-3.0-or-later**. Preserve original license and attribution notices, including relevant upstream media attribution. Vendored Glaze CSS is MIT-licensed. See [UPSTREAM.md](UPSTREAM.md), [LICENSE](LICENSE), [desktop/LICENSE](desktop/LICENSE), [frontend/LICENSE](frontend/LICENSE), and [third_party/glaze/LICENSE](third_party/glaze/LICENSE).

**GoreeCloud identity does not remove upstream software license obligations.**
