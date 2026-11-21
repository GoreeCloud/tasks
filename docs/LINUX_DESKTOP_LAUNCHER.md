# Linux Qt Quick source-only development launcher (not a release package)

## Scope and authority

This milestone gives GoreeCloud Tasks an optional native Qt Quick 6.12 Linux sign-in screen and an opt-in **XDG desktop entry generator**, built entirely from the first-party repository. The Python generator writes a new .desktop file in a user-specified directory; it **does not install it, change XDG configuration, modify a user's applications menu, deploy a service, or install dependencies**. Qt 6.12.0/PySide6 remains the approved graphical framework; no Electron, Tauri, unapproved branding icon or third-party runtime code was added.

The generated launcher has only a name, description, icon-free category and quoted absolute paths for an existing Python interpreter and linux/main.py. It does not include an API token, password, server hostname, bearer header or other user secret. It escapes percent field codes, reserved characters and paths with spaces; source files and the Python interpreter must already exist. Output uses exclusive creation and refuses to replace an existing file or final symlink.

## Local developer verification

Work from a trusted copy of this repository and an existing, isolated Python environment with the pinned linux/requirements.txt installed. Run the offscreen Qt Quick smoke test to load the true UI without network requests, verify the masked token entry, navigate into a synthetic in-memory workspace and disconnect. Run the unittest suite for backend, private session reset, URL policy and no-overwrite entry generation checks.

Generate a new .desktop file **in a disposable directory you control** with:

    QT_QPA_PLATFORM=offscreen python linux/smoke.py
    QT_QPA_PLATFORM=offscreen python -m unittest discover -s linux/tests -v
    python linux/desktop_launcher.py --output /path/to/existing/disposable-directory/goreecloud-tasks.desktop
    desktop-file-validate /path/to/existing/disposable-directory/goreecloud-tasks.desktop

The third command does not overwrite an existing file; the fourth uses optional desktop-file-utils on systems with the validator installed. Inspect the generated file before taking any further step. An entry is only useful if the referenced Python interpreter still has PySide6 installed, main.py remains at its emitted absolute path and Main.qml is adjacent to it. Moving the source tree or deleting its venv invalidates the entry; regenerate separately rather than silently editing a user-owned launcher. No installation/uninstallation commands are executed or accepted as tested by this milestone.

## In-memory authentication

On launch without an API token environment variable, the native sign-in screen accepts an HTTPS server URL (loopback HTTP permitted only for local development) and a 32–512 character printable ASCII development bearer token. Tokens are masked by QML TextInput.Password and cleared from the input after submission. The backend verifies URL safety (no embedded credentials/queries) and keeps the token only in process memory while connected. Existing developer invocation with an environment variable remains supported.

The explicit **Disconnect** button closes private task/habit dialogs, clears draft text fields and cached task/project/habit/history records, aborts in-flight network replies and refuses late callbacks using a connection generation check. It does not remove tokens from an invoking shell's environment, clipboard, OS memory dumps, temporary system snapshots or backups, and does not constitute secure memory zeroization or a multi-user Identity/logout framework. No secret is persisted in the generated file or localStorage.

## Acceptance and outstanding work

Verified source-only: 67 API tests, 16 Qt backend/launcher tests, native Qt Quick offscreen login/workspace/logout, real authenticated synthetic localhost Qt networking followed by an aborted late reply, true desktop entry syntax through desktop-file-validate, and safe new-file/no-symlink behavior. **Not verified:** actual interactive GNOME/KDE, X11/Wayland, packaging/install/upgrade/uninstall, icon/branding approval, keyboard and screen reader validation, physical laptop install, OS secret storage, signed release, Qt LGPL redistribution obligations, or distribution reproducibility. Do not label this stable or deploy it to a VPS. GoreeShield governs privacy; Wardveil cybersecurity; Identity/multi-user authentication remains a separate project-wide gate.
