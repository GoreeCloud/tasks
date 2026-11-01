# Android physical-device recovery acceptance — development evidence

**Test date:** 2026-10-31 (America/Chicago) / 2026-11-01 UTC
**Source commit:** `20066a0d0d6bf24c4ee94ae60980c8f34a7382f7`
**CI run:** https://github.com/GoreeCloud/tasks/actions/runs/41274898845 (all 3 jobs passed)
**Device:** OnePlus N200 (DE2117), Android 16 / API 36, connected to authorized developer laptop
**App package:** `com.goreecloud.tasks`, 0.1.0-dev, Android min SDK 26 / target SDK 35
**Debug APK SHA-256:** `454b9bcd6f212309c14acaf9c39863f16654ade927c96d1f5cb6bdd6fbc977ae`

## Scope and data protection

This was a **temporary physical-device smoke test**, not a release-signing or production acceptance. ADB confirmed the package was **not installed** before testing, so there was no existing GoreeCloud Tasks database to modify. The debug APK was built by the repository's GitHub Actions workflow, extracted from its internal transport ZIP, SHA-256 checked, and verified with Android `apksigner` (APK Signature Scheme v2, one signer). `aapt` verified the app identity, SDK levels, and absence of Internet permission. The source and APK were inspected before installation.

Only one clearly labeled synthetic task (`GC_QA_SYNTHETIC_20066A0`) and its local JSON backup were used. No personal task content, third-party app data, account credentials, network synchronization, or production system was accessed. The Android document picker was used without inspecting unrelated documents. The test package and synthetic backup were **removed afterward**, and ADB verified both absent. The developer laptop's local extracted APK is an internal test artifact, **not delivered** to the user.

## Observed results

| Check | Observed result |
| --- | --- |
| Install previously absent debug package on API 36 | **PASS**: streaming install succeeded |
| Launch native Jetpack Compose main activity | **PASS**: process alive, top/resumed activity confirmed |
| Read native Android accessibility tree | **PASS**: capture, search, task filters, export/import actions present |
| Export an empty workspace through Android CreateDocument | **PASS**: verified schema-1 JSON, zero tasks/projects |
| Reopen empty JSON through Android OpenDocument | **PASS**: explicit 0-task/0-project confirmation and completion notice |
| Create one synthetic task on-device | **PASS**: task visible, 1 open task |
| Export populated workspace through the system document picker | **PASS**: schema-1 JSON with eight task fields, exact synthetic title |
| Reject import into populated workspace | **PASS**: user-facing guard; existing synthetic task unchanged |
| Clear **only newly created synthetic app data** and reopen | **PASS**: app started empty, backup remained intact |
| Open saved one-task backup and confirm import | **PASS**: native confirmation of 1 task, 0 projects |
| Verify recovered task in native UI | **PASS**: exact synthetic title, 1 open task, import success notice |
| Clean up test installation and backup | **PASS**: package and synthetic JSON file absent on device |

## Not yet accepted

- Real device import/export of completed task and project metadata, including precision-preserving timestamps; these are covered by JVM/Robolectric tests, **not** this phone test.
- Rotation, process interruption, low storage, document-provider failures, repeated import attempts, accessibility navigation, dark-mode visuals and other devices/Android versions.
- Production keystore/release-signing process and update-in-place with **existing** user data.
- Directly installable, standalone `.apk` in `GoreeCloud/Artifacts` on Google Drive, with readback. The internal GitHub artifact ZIP does not satisfy the founder delivery rule.
- Secure identity, multi-user authorization, and real native client synchronization (all remain **disabled**).

**Release status remains development.** Do not treat this smoke test as complete Android or Stable acceptance.
