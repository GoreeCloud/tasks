# GoreeCloud Tasks — owner-supplied UI inspiration direction

**Status:** Browser list-first visual pass under draft PR #5; this is a UI direction and tested source change, **not** Stable acceptance. This record references the five owner-supplied task-manager screenshots supplied in conversation. The screenshots are **not** copied into the public repo, and no third-party icons, trademarks, layouts or artwork are distributed.

## Visual and functional direction

The owner reference images emphasize (1) a restrained, light, readable task workspace; (2) a navigable Inbox/Today/Upcoming/Projects rail; (3) clean, separated task rows with an unmistakable completion circle, contextual priority, date, and project metadata; (4) lightweight task capture and detail editing; (5) dedicated mobile bottom navigation and an accessible add control; and eventually (6) sections, subtasks, labels, recurring reminders and project collaboration.

**GC UI remains the authority:** Use semantic GC UI color and contrast roles, first-launch Light/Neutral, explicit personal accents, first-party controls and accessible focus. Do **not** clone the red branding or copy proprietary artwork from the examples.

## Implemented in browser source

- A list-first desktop workspace replaces the tall marketing-style hero with a compact page heading, smaller metrics, a clear projects sidebar, and a persistent **Add task** action. Sidebar project items display open-task counts; the selected view remains visible.
- Task rows are compact, separated and readable; priority is expressed on the completion circle without depending on color alone. Selection is distinct from completion; title, due date, project, priority, Edit and Delete remain available.
- **Mobile** provides a persistent Today / Inbox / Add / Search / Browse navigation dock. Browse is an actual dialog offering other task views and project selection/creation, not a mock control.
- Floating Add on mobile opens a focusable, collapsible validated task composer. The form is visible without JavaScript as a progressive fallback; with JavaScript, saving closes it. Desktop retains inline Add and the `N` shortcut.
- Project editing, local schema-one backups, recoverable Trash, local-only data and accessibility semantics remain unchanged; no migration or new network dependency.
- CSS uses the pinned first-party GC UI semantic snapshot, selected accent, light/dark color role pairs, forced-colors handling, reduced motion, keyboard focus and 200% effective zoom fallback. The permanent mobile dock reserves safe-area spacing.

## Verified and remaining review

Automated local Chromium/Firefox browser QA covers task creation/edit, bulk actions, Trash restoration, browser-profile-separated schema-one import/export, theme persistence, keyboard actions, mobile tabs, Browse menu, project creation, mobile Add, desktop/mobile axe-core and effective-zoom reflow. Reference-derived **Light** screenshots are captured separately from explicit Dark screenshots by synthetic QA only. Axe incomplete/manual-review findings and full real browser toolbar zoom, physical mobile, AT, high-contrast review remain release gates.

**Future work, not implemented by these screenshots:** nested subtasks/projects, sections, labels, date-time scheduling and recurrence, comments/assignments and shared workspaces, voice/natural-language capture, AI assistant, mobile OS-native bottom navigation, Android/GTK screenshot acceptance. These require model/schema design, security and backward-compatibility work instead of fictitious UI.

The browser remains the current screenshot-reviewed visual reference. Android Compose and Linux GTK4 now have **list-first navigation implemented in source** (native bottom navigation/FAB/context actions and GTK sidebar/collapsible capture); see [native UI increment](NATIVE_LIST_FIRST_UI.md). They still require Android compilation, actual device visual and assistive-technology QA, and GTK full rendered/Orca acceptance before claiming native visual parity. **No visual reference automatically authorizes a new task schema, account migration, or production deployment.**
