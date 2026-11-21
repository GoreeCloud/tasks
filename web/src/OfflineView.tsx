import { useCallback, useEffect, useRef, useState } from "react";
import {
  type CachedProject,type CachedTask,type QueueItem,type VaultSession,
  applyChangePage,type ChangePage,createVault,emptyPayload,eraseVault,hasVault,saveVault,unlockVault
} from "./offlineVault";

type Request = <T,>(path:string,init?:RequestInit)=>Promise<T>;
type Bootstrap = {format:string;cursor:number;tasks:CachedTask[];projects:CachedProject[]};

export function OfflineView({request,onSynced}:{
  request:Request;onSynced:()=>Promise<void>
}) {
  const session=useRef<VaultSession|null>(null);
  const [exists,setExists]=useState(false);
  const [locked,setLocked]=useState(true);
  const [passphrase,setPassphrase]=useState("");
  const [verify,setVerify]=useState("");
  const [tasks,setTasks]=useState<CachedTask[]>([]);
  const [projects,setProjects]=useState<CachedProject[]>([]);
  const [pending,setPending]=useState<QueueItem[]>([]);
  const [draft,setDraft]=useState("");
  const [priority,setPriority]=useState(2);
  const [dueDate,setDueDate]=useState("");
  const [projectId,setProjectId]=useState("");
  const [editing,setEditing]=useState<string|null>(null);
  const [editedTitle,setEditedTitle]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const load=useCallback((vault:VaultSession)=>{
    session.current=vault;
    setTasks(vault.payload.tasks);
    setProjects(vault.payload.projects);
    setPending(vault.payload.queue);
    setLocked(false);
  },[]);
  useEffect(()=>{
    let current=true;
    void hasVault().then(value=>{if(current)setExists(value);})
      .catch(()=>{if(current)setError("Encrypted browser storage is unavailable");});
    return ()=>{current=false;session.current=null;};
  },[]);
  const lock=()=>{
    session.current=null;setTasks([]);setProjects([]);setPending([]);setLocked(true);
    setDraft("");setDueDate("");setEditing(null);setPassphrase("");setVerify("");
    setMessage("");setError("");
  };
  async function mutate(work:()=>Promise<void>) {
    setBusy(true);setError("");setMessage("");
    try {await work();}
    catch(err){setError(err instanceof Error?err.message:"Offline action failed");}
    finally{setBusy(false);}
  }
  async function store(queue:QueueItem[],nextTasks?:CachedTask[],nextProjects?:CachedProject[],cursor?:number) {
    const current=session.current;
    if(!current)throw new Error("Unlock your encrypted vault first");
    const payload={...current.payload,saved_at:new Date().toISOString(),
      queue,tasks:nextTasks??current.payload.tasks,
      projects:nextProjects??current.payload.projects,
      cursor:cursor??current.payload.cursor};
    const updated=await saveVault(current,payload);
    load(updated);
  }
  async function setup() {
    if(passphrase!==verify)throw new Error("Passphrase confirmation does not match");
    const snapshot=await request<Bootstrap>("/sync/bootstrap");
    if(snapshot.format!=="goreecloud-tasks-sync-1"||
       !Array.isArray(snapshot.tasks)||!Array.isArray(snapshot.projects))
      throw new Error("Server synchronization format is unsupported");
    const created=await createVault(passphrase,emptyPayload(snapshot.tasks,snapshot.projects,snapshot.cursor));
    load(created);setExists(true);setPassphrase("");setVerify("");
    setMessage("Encrypted offline vault enabled. You can now draft tasks without a network connection.");
  }
  async function open() {
    const unlocked=await unlockVault(passphrase);
    load(unlocked);setPassphrase("");setMessage("Offline vault unlocked for this browser tab.");
  }
  async function queueCreate() {
    if(!draft.trim()||draft.trim().length>240)throw new Error("Task title must contain 1–240 characters");
    if(pending.length>=200)throw new Error("Offline queue limit reached");
    if(projectId&&!projects.some(project=>project.id===projectId))
      throw new Error("Select a project in this encrypted snapshot");
    const op:QueueItem={id:crypto.randomUUID(),kind:"create",task_id:null,expected_version:null,
      payload:{title:draft.trim(),priority,project_id:projectId||null,
        due_date:dueDate||null,description:"",tags:[],recurrence:"none",parent_id:null},
      created_at:new Date().toISOString(),status:"pending"};
    await store([...pending,op]);setDraft("");setDueDate("");setPriority(2);
    setMessage("Task draft saved in your encrypted offline queue; not yet on the server.");
  }
  async function queueEdit(task:CachedTask) {
    if(!editedTitle.trim()||editedTitle.length>240)
      throw new Error("Task title must contain 1–240 characters");
    if(pending.some(item=>item.task_id===task.id))
      throw new Error("This task already has a pending edit. Sync or discard it first.");
    const op:QueueItem={
      id:crypto.randomUUID(),kind:"edit",task_id:task.id,expected_version:task.version,
      payload:{title:editedTitle.trim()},created_at:new Date().toISOString(),status:"pending"
    };
    await store([...pending,op]);setEditing(null);setEditedTitle("");
    setMessage("Title change saved offline with the original server revision; not yet applied.");
  }
  async function discard(op:QueueItem) {
    await store(pending.filter(item=>item.id!==op.id));
    setMessage("Discarded the selected offline draft; no server data was changed.");
  }
  async function syncNow() {
    const current=session.current;
    if(!current)throw new Error("Unlock first");
    if(pending.some(item=>item.status==="conflict"))
      throw new Error("Resolve or discard conflicting drafts before syncing");
    let queue=current.payload.queue;
    for(const op of queue){
      try {
        if(op.kind==="create") {
          await request("/tasks",{
            method:"POST",headers:{"Idempotency-Key":op.id},
            body:JSON.stringify(op.payload)
          });
        } else if(op.kind==="edit"&&op.task_id&&op.expected_version){
          await request("/tasks/"+encodeURIComponent(op.task_id),{
            method:"PATCH",headers:{"Idempotency-Key":op.id},
            body:JSON.stringify({...op.payload,expected_version:op.expected_version})
          });
        } else throw new Error("Unsupported offline operation");
      }catch(err) {
        const description=err instanceof Error?err.message:"Unable to contact the server";
        if(/\(409\)|\(404\)|\(410\)/.test(description)) {
          queue=queue.map(item=>item.id===op.id?{...item,status:"conflict" as const}:item);
          await store(queue);
          throw new Error("Sync stopped at a conflict. Review the server task and discard the pending edit if needed. "+description);
        }
        throw new Error("Sync paused; the encrypted queue was preserved. "+description);
      }
      // Commit queue acknowledgement immediately after each successful HTTP response.
      // A lost create response safely retries with the SAME idempotency key.
      queue=queue.filter(item=>item.id!==op.id);
      await store(queue);
    }
    const snapshot=await request<Bootstrap>("/sync/bootstrap");
    if(snapshot.format!=="goreecloud-tasks-sync-1")
      throw new Error("Unsupported server synchronization format");
    await store([],snapshot.tasks,snapshot.projects,snapshot.cursor);
    await onSynced();
    setMessage("Server sync completed. Your encrypted local snapshot is current.");
  }
  async function pullChanges() {
    const current=session.current;
    if(!current)throw new Error("Unlock your encrypted vault first");
    if(pending.length)throw new Error("Sync or discard pending drafts before pulling changes");
    // Apply a bounded sequence in RAM and save one encrypted result only when
    // the entire page chain has been validated. This avoids partial cache writes.
    let candidate=current.payload;
    for(let pageIndex=0;pageIndex<10;pageIndex++) {
      const page=await request<ChangePage>(
        "/sync/changes?after="+encodeURIComponent(String(candidate.cursor))+"&limit=200"
      );
      candidate=applyChangePage(candidate,page);
      if(!page.has_more) {
        await store([],candidate.tasks,candidate.projects,candidate.cursor);
        setMessage("Encrypted offline snapshot updated from the server change feed.");
        return;
      }
    }
    throw new Error("Too many change pages. Use full snapshot refresh instead.");
  }
  async function refreshSnapshot() {
    if(pending.length)throw new Error("Sync or discard pending drafts before refreshing");
    const snapshot=await request<Bootstrap>("/sync/bootstrap");
    if(snapshot.format!=="goreecloud-tasks-sync-1")throw new Error("Unsupported server version");
    await store([],snapshot.tasks,snapshot.projects,snapshot.cursor);
    setMessage("Encrypted snapshot updated from the server.");
  }
  async function forget() {
    if(!window.confirm("Permanently erase this browser's encrypted Tasks offline vault and ALL unsynced drafts?"))
      return;
    await eraseVault();lock();setExists(false);
    setMessage("Local encrypted vault erased. Server tasks were not changed.");
  }
  return <section className="offline-panel gc-card" aria-label="Encrypted offline workspace">
    <p className="eyebrow">OPTIONAL · ENCRYPTED LOCAL STORAGE</p>
    <h2>Offline workspace</h2>
    <p className="muted">Protect task snapshots and drafts with a passphrase you choose. The server token and vault passphrase are never saved. Sync is manual: conflicts are never overwritten automatically.</p>
    {error&&<p className="alert" role="alert">{error}</p>}
    {message&&<p className="offline-message" role="status">{message}</p>}
    {locked?<form className="offline-unlock" onSubmit={e=>{e.preventDefault();void mutate(exists?open:setup);}}>
      <h3>{exists?"Unlock encrypted vault":"Enable encrypted offline vault"}</h3>
      <label>Vault passphrase (12+ characters)
        <input aria-label="Offline vault passphrase" required minLength={12} maxLength={512}
          autoComplete="off" type="password" value={passphrase}
          onChange={e=>setPassphrase(e.target.value)}/>
      </label>
      {!exists&&<label>Confirm passphrase
        <input aria-label="Confirm offline passphrase" required minLength={12} maxLength={512}
          autoComplete="off" type="password" value={verify}
          onChange={e=>setVerify(e.target.value)}/>
      </label>}
      <button type="submit" className="primary-btn" disabled={busy||passphrase.length<12}>
        {exists?"Unlock vault":"Enable vault from server"}
      </button>
      {!exists&&<p className="muted">Initial setup requires a successful server connection. A lost passphrase cannot be recovered. No background sync is enabled.</p>}
      {exists&&<button type="button" className="danger-btn" disabled={busy}
        onClick={()=>void mutate(forget)}>Erase local vault...</button>}
    </form>:<>
      <div className="offline-status">
        <span>Encrypted vault unlocked · {tasks.length} cached tasks · {pending.length} queued drafts</span>
        <div className="offline-actions">
          <button type="button" className="secondary-btn" disabled={busy} onClick={()=>void mutate(pullChanges)}>Pull server changes</button>
          <button type="button" className="secondary-btn" disabled={busy} onClick={()=>void mutate(refreshSnapshot)}>Full snapshot refresh</button>
          <button type="button" className="secondary-btn" disabled={busy} onClick={()=>void mutate(syncNow)}>Sync now</button>
          <button type="button" className="secondary-btn" disabled={busy} onClick={lock}>Lock</button>
        </div>
      </div>
      <form className="offline-composer" onSubmit={e=>{e.preventDefault();void mutate(queueCreate);}}>
        <h3>Draft a standalone task</h3>
        <label>Title<input aria-label="Offline task title" required maxLength={240} value={draft}
          onChange={e=>setDraft(e.target.value)} placeholder="Plan the next step"/></label>
        <div className="offline-fields">
          <label>Due<input type="date" aria-label="Offline task due date" value={dueDate}
            onChange={e=>setDueDate(e.target.value)}/></label>
          <label>Priority<select aria-label="Offline task priority" value={priority}
            onChange={e=>setPriority(Number(e.target.value))}>{[1,2,3,4].map(n=>
              <option key={n} value={n}>P{n}</option>)}</select></label>
          <label>Project<select aria-label="Offline task project" value={projectId}
            onChange={e=>setProjectId(e.target.value)}><option value="">Inbox</option>
            {projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        </div>
        <button type="submit" className="primary-btn" disabled={busy||!draft.trim()}>
          Save encrypted draft</button>
      </form>
      {pending.length>0&&<section className="offline-queue" aria-label="Pending offline drafts">
        <h3>Pending changes — review before sending</h3>
        <ul>{pending.map(item=><li key={item.id}>
          <span><strong>{item.kind==="create"?"Create task":"Edit title"}</strong> · {String(item.payload.title||"Task")}
            {item.status==="conflict"?" · CONFLICT":""}</span>
          <button type="button" className="secondary-btn" disabled={busy}
            onClick={()=>void mutate(()=>discard(item))}>Discard draft</button>
        </li>)}</ul>
      </section>}
      <section className="offline-tasks" aria-label="Cached task titles">
        <h3>Cached tasks (last saved snapshot)</h3>
        <p className="muted">Offline edits are limited to the title of an existing task or drafting new standalone tasks. After a server conflict, review the current task in the online workspace before discarding the local edit.</p>
        <ul>{tasks.slice(0,250).map(task=><li key={task.id}>
          <div><strong>{task.title}</strong>
            <span className="muted">P{task.priority} · Revision {task.version}{task.completed_at?" · Completed":""}</span>
          </div>
          {editing===task.id?<form onSubmit={e=>{e.preventDefault();void mutate(()=>queueEdit(task));}}>
            <input aria-label="Edit offline title" required maxLength={240} value={editedTitle}
              onChange={e=>setEditedTitle(e.target.value)}/>
            <button type="submit" disabled={busy}>Queue edit</button>
            <button type="button" onClick={()=>setEditing(null)}>Cancel</button>
          </form>:<button type="button" className="secondary-btn" disabled={busy||
            pending.some(op=>op.task_id===task.id)} onClick={()=>{
              setEditing(task.id);setEditedTitle(task.title);
            }}>Edit offline title</button>}
        </li>)}</ul>
        {tasks.length>250&&<p className="muted">Showing 250 cached task titles. Search and full cached editing are not yet supported.</p>}
      </section>
      <button type="button" className="danger-btn" disabled={busy}
        onClick={()=>void mutate(forget)}>Erase offline vault and unsynced drafts...</button>
    </>}
  </section>;
}
