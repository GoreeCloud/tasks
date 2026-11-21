/** Opt-in static-only shell. No API response, token or task data in CacheStorage. */
const SCRIPT="/offline-sw.js";
const PREFIX="goreecloud-tasks-public-shell-";
function supported() {
  if(!globalThis.isSecureContext||!("serviceWorker" in navigator)||!("caches" in globalThis))
    throw new Error("Offline app shell requires HTTPS or localhost with Service Worker support");
}
export async function hasOfflineShell():Promise<boolean> {
  if(!("serviceWorker" in navigator))return false;
  const reg=await navigator.serviceWorker.getRegistration("/");
  return !!reg?.active&&new URL(reg.active.scriptURL).pathname===SCRIPT;
}
export async function enableOfflineShell():Promise<void> {
  supported();
  const registration=await navigator.serviceWorker.register(SCRIPT,{scope:"/"});
  await navigator.serviceWorker.ready;
  if(!registration.active||new URL(registration.active.scriptURL).pathname!==SCRIPT)
    throw new Error("Unable to activate the public offline shell");
}
export async function removeOfflineShell():Promise<void> {
  supported();
  const reg=await navigator.serviceWorker.getRegistration("/");
  if(reg&&[reg.active,reg.waiting,reg.installing].some(w=>w&&new URL(w.scriptURL).pathname===SCRIPT))
    await reg.unregister();
  for(const name of await caches.keys())
    if(name.startsWith(PREFIX))await caches.delete(name);
}
