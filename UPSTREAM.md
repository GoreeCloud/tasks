# Upstream provenance and licensing

## Source import

- Upstream: https://github.com/go-vikunja/vikunja
- Upstream branch: `main`
- Pinned imported revision: `6263ff12956f29bd84ed1346d9752f82e02cdd59` (verified 2026-10-10)
- Import mode: controlled source snapshot copied into the pre-existing `GoreeCloud/tasks` repository. **GitHub's native fork badge/ancestry is not established** because the destination already existed.
- Upstream GitHub Actions workflows were intentionally excluded. They must be individually security-audited before any substitution or re-enablement.
- Existing application source, compatibility identifiers, data formats, and source-level licenses were retained rather than mass renamed or removed.

## License and attribution obligations

The upstream README identifies most repository content as AGPL-3.0-or-later, while `desktop/` is GPL-3.0-or-later. Maintain the corresponding `LICENSE` files, individual copyright notices, and original author attribution. Media and other third-party dependencies may have additional notices; audit packaged artifacts before release. Modified network-served AGPL programs require appropriate Corresponding Source availability under their license terms.

Glaze visual-token CSS from `GoreeCloud/glaze`, pinned at `0798de28fe0626d6cc8bd7986dc9c4b922119c35`, is used under MIT; its original license is retained at `third_party/glaze/LICENSE`.

## Upstream maintenance

Track upstream security patches and migrations without blindly merging upstream CI or replacing GoreeCloud presentation/contract decisions. A reproducible future update procedure must compare pinned upstream revisions, licenses, schemas, and test outcomes; assess data migration/rollback; and advance through reviewable commits.

## Fork-to-Native status

The initial snapshot is deliberately only a **starting point**. Distinct identity, Glaze conformity, native platform systems, user-data portability, accessibility, migration and recovery, representative testing, and Stable gates remain to be validated and/or implemented.
