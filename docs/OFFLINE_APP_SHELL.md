# Opt-in public app shell for offline encrypted drafting (development source)

The web Vite production build emits dist/offline-sw.js from an in-repository Node-only generator, without a third-party service-worker dependency or unapproved branding. Its versioned static cache is **not** a task cache, encrypted vault, backup, sync engine, or installable production PWA.

## Activation and removal

1. Serve the production web/dist contents from a same-origin HTTPS site (or localhost test) with /offline-sw.js accessible at the root. Initialize the passphrase-encrypted vault using an authenticated server connection.
2. Deliberately select **Enable offline app shell** in the Offline workspace. This user action installs a service worker and caches the current public /index.html and the exact bundler-generated static files under /assets/. It does not persist task/API data or automatically sign in.
3. Disconnect from the network. Reopen the same origin in the same browser profile and select **Open encrypted vault without server token** from the login screen. Enter the vault passphrase to view stored tasks and draft locally. No API calls are permitted; reconnect and authenticate before manually syncing or comparing server conflicts.
4. Select **Remove offline app shell** to unregister the worker and delete only CacheStorage entries with the GoreeCloud Tasks public-shell cache prefix. The encrypted IndexedDB vault and unsent drafts remain; their erasure is a separate user-confirmed action. Eviction may still prevent future offline reopening.

## Threat model and constraints

- Worker fetch handlers ignore non-GET, Authorization-bearing, cross-origin, query-string and /api/* requests. Only exact static bundle URLs are cache-first. Origin root/index navigation is network-first with a cached public index fallback. No private API response, user task, token, key, envelope or third-party URL is stored by the worker.
- Build output is restricted to index plus allowlisted generated files from dist/assets. The Node generator fails closed if root/index/JS/CSS is missing. New builds generate a new versioned name; activation evicts only older app-shell static caches. Proxy/CDN must serve expected origin paths and appropriate headers.
- Browser support, storage quota, eviction, CacheStorage lifecycle, service-worker update timing and offline startup vary. There is no background sync, periodic fetch, push, alarms, notification permission, identity-bound keys, signed package or device lifecycle. This source is not a production PWA.
- Compromised origin JavaScript, browser extensions, shared device profiles, weak passphrases and offline access to an unlocked vault remain risks. GoreeShield, Wardveil and GoreeCloud Identity acceptance are distinct outstanding gates.
- Node acceptance checks static allowlisting and fail-closed behavior; a real Chromium test performs user opt-in, offline navigation, tokenless encrypted draft unlock, no API request and explicit removal. Normal Chromium/Firefox/WebKit and native-client acceptance tests remain independent.

No production server, personal task database, VPS workload or Vikunja record was changed by this app-shell feature.
