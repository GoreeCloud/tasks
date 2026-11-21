/** GoreeCloud Tasks browser offline vault v1.
 *
 * Opt-in, passphrase-unlocked AES-256-GCM for task snapshots and queued writes.
 * No authentication token, password, derived key or plaintext task is persisted.
 * This is not multiuser authorization or a native encrypted sync engine.
 */
export type CachedTask = {
  id: string; title: string; description: string; project_id: string|null;
  parent_id: string|null; due_date: string|null; priority: number; tags: string[];
  recurrence: "none"|"daily"|"weekly"|"monthly"; completed_at: string|null;
  version: number; created_at: string;
};
export type CachedProject = {id:string;name:string};
export type QueueItem = {
  id: string; kind: "create"|"edit"; task_id: string|null;
  expected_version: number|null; payload: Record<string,unknown>;
  created_at: string; status: "pending"|"conflict";
};
export type VaultPayload = {
  format:"goreecloud-tasks-offline-data-1"; saved_at:string;
  cursor:number; tasks:CachedTask[]; projects:CachedProject[]; queue:QueueItem[];
};
type VaultEnvelope = {format:"goreecloud-tasks-offline-aesgcm-1"; salt:string; nonce:string; data:string; revision?:number};
const DB_NAME="goreecloud-tasks-offline-v1";
const STORE="secrets";
const ITEM="vault";
const MAX_BYTES=5_000_000;
const enc=new TextEncoder();
const dec=new TextDecoder("utf-8",{fatal:true});
// Legacy records used the origin-only AAD; newly written records also
// authenticate their CAS revision to prevent unauthenticated version rollback.
const aadForRevision=(revision:number)=>enc.encode(
  "goreecloud-tasks-offline-v1|"+location.origin+(revision===0?"":"|rev="+revision)
);

function base64(bytes:Uint8Array):string {
  let text="";
  for(let n=0;n<bytes.length;n+=8192)
    text+=String.fromCharCode(...bytes.subarray(n,n+8192));
  return btoa(text);
}
function unbase64(encoded:string):Uint8Array<ArrayBuffer> {
  const chars=atob(encoded),bytes=new Uint8Array(chars.length);
  for(let i=0;i<chars.length;i++)bytes[i]=chars.charCodeAt(i);
  return bytes;
}
function randomBytes(count:number) {
  const bytes=new Uint8Array(count);
  crypto.getRandomValues(bytes);
  return bytes;
}
function checkBrowser() {
  if(!globalThis.isSecureContext || !crypto?.subtle || !indexedDB)
    throw new Error("Encrypted offline storage requires HTTPS or localhost and IndexedDB");
}
async function db():Promise<IDBDatabase> {
  checkBrowser();
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open(DB_NAME,1);
    request.onupgradeneeded=()=>{
      if(!request.result.objectStoreNames.contains(STORE))
        request.result.createObjectStore(STORE);
    };
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(new Error("Unable to open secure offline storage"));
    request.onblocked=()=>reject(new Error("Close other Tasks tabs and retry"));
  });
}
async function readRaw():Promise<VaultEnvelope|null> {
  const database=await db();
  try {
    return await new Promise((resolve,reject)=>{
      const tx=database.transaction(STORE,"readonly");
      const req=tx.objectStore(STORE).get(ITEM);
      req.onsuccess=()=>resolve(req.result??null);
      req.onerror=()=>reject(new Error("Unable to read offline storage"));
    });
  }finally{database.close();}
}
/** Atomic optimistic compare-and-swap inside one IndexedDB transaction.
 * Prevents stale tabs from overwriting or recreating other tabs' draft queues.
 * The encryption salt also acts as the per-vault instance identity, so a
 * deleted-and-recreated vault cannot be modified by an unlocked old tab.
 */
async function compareAndSwapRaw(
  value:VaultEnvelope|null,expectedRevision:number|null,expectedSalt:string|null
):Promise<void> {
  const database=await db();
  try{
    await new Promise<void>((resolve,reject)=>{
      const tx=database.transaction(STORE,"readwrite");
      const store=tx.objectStore(STORE);
      let conflict=false;
      tx.oncomplete=()=>resolve();
      tx.onabort=()=>reject(new Error(conflict
        ?"Offline vault changed in another tab; lock and unlock to reload without overwriting"
        :"Encrypted offline storage write aborted"));
      const read=store.get(ITEM);
      read.onsuccess=()=>{
        const current=read.result as VaultEnvelope|undefined;
        const revision=current?.revision===undefined?0:current.revision;
        if((expectedRevision===null && current!==undefined)||
           (expectedRevision!==null && (!current||
             current.format!=="goreecloud-tasks-offline-aesgcm-1"||
             !Number.isSafeInteger(revision)||revision<0||
             revision!==expectedRevision||current.salt!==expectedSalt))) {
          conflict=true;tx.abort();return;
        }
        if(value)store.put(value,ITEM);
        else store.delete(ITEM);
      };
    });
  }finally{database.close();}
}
async function derive(passphrase:string,salt:Uint8Array):Promise<CryptoKey> {
  const root=await crypto.subtle.importKey("raw",enc.encode(passphrase),"PBKDF2",false,["deriveKey"]);
  return crypto.subtle.deriveKey(
    {name:"PBKDF2",salt:new Uint8Array(salt),iterations:310000,hash:"SHA-256"},
    root,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]
  );
}
function validate(data:unknown):asserts data is VaultPayload {
  const p=data as VaultPayload;
  if(!p||p.format!=="goreecloud-tasks-offline-data-1"||
     !Array.isArray(p.tasks)||p.tasks.length>5000||
     !Array.isArray(p.projects)||p.projects.length>5000||
     !Array.isArray(p.queue)||p.queue.length>200||
     !Number.isSafeInteger(p.cursor)||p.cursor<0)
    throw new Error("The encrypted vault contains an unsupported data format");
  if(p.queue.some(q=>!q||!["create","edit"].includes(q.kind)||
    !["pending","conflict"].includes(q.status)||typeof q.id!=="string"))
    throw new Error("The offline queue contains unsupported operations");
}
async function persist(
  key:CryptoKey,salt:Uint8Array,payload:VaultPayload,expectedRevision:number|null
):Promise<number> {
  validate(payload);
  const clear=enc.encode(JSON.stringify(payload));
  if(clear.byteLength>MAX_BYTES)
    throw new Error("Offline vault is full; reconcile or export data before adding more");
  const revision=(expectedRevision??0)+1;
  if(!Number.isSafeInteger(revision))throw new Error("Offline vault revision exhausted");
  const nonce=randomBytes(12);
  const cipher=await crypto.subtle.encrypt(
    {name:"AES-GCM",iv:nonce,additionalData:aadForRevision(revision)},key,clear
  );
  const saltText=base64(salt);
  await compareAndSwapRaw({format:"goreecloud-tasks-offline-aesgcm-1",
    revision,salt:saltText,nonce:base64(nonce),data:base64(new Uint8Array(cipher))},
    expectedRevision,expectedRevision===null?null:saltText);
  return revision;
}
export type VaultSession = {
  key:CryptoKey;salt:Uint8Array;payload:VaultPayload;revision:number;
};
export function emptyPayload(tasks:CachedTask[],projects:CachedProject[],cursor:number):VaultPayload {
  return {format:"goreecloud-tasks-offline-data-1",saved_at:new Date().toISOString(),
    tasks,projects,cursor,queue:[]};
}
export async function hasVault(){return !!(await readRaw());}
export async function createVault(passphrase:string,payload:VaultPayload):Promise<VaultSession> {
  if(passphrase.length<12||passphrase.length>512)
    throw new Error("Choose a passphrase of at least 12 characters");
  const salt=randomBytes(16);
  const key=await derive(passphrase,salt);
  // Existence check and initial record creation are one exclusive write.
  const revision=await persist(key,salt,payload,null);
  return {key,salt,payload,revision};
}
export async function unlockVault(passphrase:string):Promise<VaultSession> {
  const raw=await readRaw();
  if(!raw||raw.format!=="goreecloud-tasks-offline-aesgcm-1")
    throw new Error("No compatible offline vault exists in this browser");
  try {
    const salt=unbase64(raw.salt),nonce=unbase64(raw.nonce);
    const revision=raw.revision??0; // Existing pre-CAS vaults migrate on first save.
    if(salt.length!==16||nonce.length!==12||
       !Number.isSafeInteger(revision)||revision<0||
       (raw.revision!==undefined&&revision<1))throw new Error("Invalid vault");
    const key=await derive(passphrase,salt);
    const clear=await crypto.subtle.decrypt(
      {name:"AES-GCM",iv:nonce,additionalData:aadForRevision(revision)},
      key,unbase64(raw.data)
    );
    const payload:unknown=JSON.parse(dec.decode(clear));
    validate(payload);
    return {key,salt,payload,revision};
  }catch{
    throw new Error("Incorrect passphrase or damaged encrypted offline vault");
  }
}
export async function saveVault(session:VaultSession,payload:VaultPayload):Promise<VaultSession> {
  // Do not edit session until the authenticated encrypted write completes.
  const revision=await persist(session.key,session.salt,payload,session.revision);
  return {...session,payload,revision};
}
/** Erasure must not silently destroy a newer tab's queue or resurrect a vault. */
export async function eraseVault(expectedRevision?:number,expectedSalt?:Uint8Array) {
  const raw=expectedRevision===undefined?await readRaw():null;
  if(expectedRevision===undefined&&!raw)return;
  const revision=expectedRevision??(raw!.revision??0);
  const salt=expectedSalt?base64(expectedSalt):raw?.salt;
  if(!salt)throw new Error("Offline vault identity is unavailable");
  await compareAndSwapRaw(null,revision,salt);
}


/** Monotonic, bounded change-feed application. No writes until caller persists
 * an authenticated encrypted snapshot. Reject malformed/out-of-order pages.
 */
export type ChangeEvent = {
  cursor:number;entity:"task"|"project";entity_id:string;
  operation:"upsert"|"delete";payload:CachedTask|CachedProject|null;
  created_at:string;
};
export type ChangePage = {
  format:"goreecloud-tasks-sync-1";after:number;next_cursor:number;
  has_more:boolean;changes:ChangeEvent[];
};
export function applyChangePage(snapshot:VaultPayload,page:ChangePage):VaultPayload {
  if(page?.format!=="goreecloud-tasks-sync-1"||page.after!==snapshot.cursor||
     !Number.isSafeInteger(page.next_cursor)||page.next_cursor<page.after||
     typeof page.has_more!=="boolean"||!Array.isArray(page.changes)||page.changes.length>200)
    throw new Error("Invalid server change-feed format; use a full bootstrap");
  const tasks=new Map(snapshot.tasks.map(item=>[item.id,item]));
  const projects=new Map(snapshot.projects.map(item=>[item.id,item]));
  let last=page.after;
  for(const event of page.changes) {
    if(!Number.isSafeInteger(event.cursor)||event.cursor<=last||
       !["task","project"].includes(event.entity)||
       !["upsert","delete"].includes(event.operation)||
       typeof event.entity_id!=="string"||!event.entity_id)
      throw new Error("Out-of-order or invalid sync event; refresh full snapshot");
    last=event.cursor;
    const entityMap=event.entity==="task"?tasks:projects;
    if(event.operation==="delete") {
      entityMap.delete(event.entity_id);
    } else {
      const payload=event.payload;
      if(!payload||payload.id!==event.entity_id||
         (event.entity==="task"&&typeof (payload as CachedTask).version!=="number")||
         (event.entity==="project"&&typeof (payload as CachedProject).name!=="string"))
        throw new Error("Invalid sync event payload; refresh full snapshot");
      if(event.entity==="task")tasks.set(event.entity_id,payload as CachedTask);
      else projects.set(event.entity_id,payload as CachedProject);
    }
  }
  if(last!==page.next_cursor||page.has_more&&page.changes.length===0)
    throw new Error("Change-feed cursor discontinuity; refresh full snapshot");
  if(tasks.size>5000||projects.size>5000)
    throw new Error("Encrypted cache record limit exceeded; use full bootstrap");
  return {...snapshot,saved_at:new Date().toISOString(),
    tasks:[...tasks.values()],projects:[...projects.values()],cursor:page.next_cursor};
}
