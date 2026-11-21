import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarView } from "./CalendarView";

type Task = {
  id: string; title: string; description: string; project_id: string | null;
  due_date: string | null; priority: number; tags: string[]; recurrence: "none"|"daily"|"weekly"|"monthly";
  completed_at: string | null; version: number; created_at: string;
};
type Project = { id: string; name: string };
type Screen = "inbox"|"today"|"upcoming"|"calendar"|"completed"|"all"|"focus";
type TaskForm = { title: string; description: string; due_date: string; priority: number; recurrence: Task["recurrence"]; project_id: string; tags: string };
const emptyForm: TaskForm = { title: "", description: "", due_date: "", priority: 2, recurrence: "none", project_id: "", tags: "" };
const today = () => {
  const x = new Date();
  return [x.getFullYear(), String(x.getMonth()+1).padStart(2,"0"), String(x.getDate()).padStart(2,"0")].join("-");
};

function FocusTimer() {
  const [duration, setDuration] = useState(25);
  const [remaining, setRemaining] = useState(25 * 60);
  const [ends, setEnds] = useState<number | null>(null);
  useEffect(() => {
    if (ends === null) return;
    const tick = () => {
      const seconds = Math.max(0, Math.ceil((ends - Date.now()) / 1000));
      setRemaining(seconds);
      if (seconds === 0) setEnds(null);
    };
    tick();
    const timer = window.setInterval(tick, 350);
    return () => window.clearInterval(timer);
  }, [ends]);
  const pause = () => { if (ends !== null) {setRemaining(Math.max(0,Math.ceil((ends-Date.now())/1000)));setEnds(null);} };
  const reset = (minutes: number) => {setEnds(null);setDuration(minutes);setRemaining(minutes*60);};
  return <section className="focus-card gc-card" aria-label="Focus timer">
    <p className="eyebrow">FOCUS MODE</p>
    <h2>Make space for deep work.</h2>
    <div className="timer" role="timer" aria-label="Time remaining">{String(Math.floor(remaining/60)).padStart(2,"0")}:{String(remaining%60).padStart(2,"0")}</div>
    <p className="muted">A local foreground timer. No session tracking or background alerts.</p>
    <div className="button-row">
      <button className="primary-btn" onClick={() => ends===null ? setEnds(Date.now()+remaining*1000) : pause()}>{ends===null ? "Start focus" : "Pause"}</button>
      <button className="secondary-btn" onClick={() => reset(duration)}>Reset</button>
      <button className="secondary-btn" onClick={() => reset(duration===25?5:25)}>{duration===25?"Short break":"25-minute focus"}</button>
    </div>
  </section>;
}

export function App() {
  const [token, setToken] = useState("");
  const [entry, setEntry] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [view, setView] = useState<Screen>("inbox");
  const [projectFilter, setProjectFilter] = useState<string|null>(null);
  const [query, setQuery] = useState("");
  const [form, setForm] = useState<TaskForm>(emptyForm);
  const [editor, setEditor] = useState<string|null>(null);
  const [newProject, setNewProject] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const request = useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const res = await fetch("/api/v1" + path, {
      ...init, headers: { "Authorization": "Bearer " + token, "Content-Type": "application/json", ...init.headers }
    });
    if (!res.ok) {
      const content = await res.json().catch(() => null);
      const detail = typeof content?.detail === "string" ? content.detail : "Request failed";
      throw new Error(detail + " (" + res.status + ")");
    }
    return res.status === 204 ? undefined as T : res.json() as Promise<T>;
  }, [token]);

  const refresh = useCallback(async () => {
    const [allTasks, allProjects] = await Promise.all([
      request<Task[]>("/tasks?status=all"), request<Project[]>("/projects")
    ]);
    setTasks(allTasks);
    setProjects(allProjects);
  }, [request]);

  useEffect(() => {
    if (!token) return;
    void refresh().catch(e => setError(String(e.message)));
  }, [token, refresh]);

  async function execute(work: () => Promise<unknown>) {
    setBusy(true);setError("");
    try {await work();await refresh();}
    catch(e) {setError(e instanceof Error ? e.message : "Unexpected error");}
    finally {setBusy(false);}
  }
  const visible = useMemo(() => tasks.filter(task => {
    if (query && ![task.title,task.description,task.tags.join(" ")].join(" ").toLowerCase().includes(query.toLowerCase())) return false;
    if (projectFilter !== null && task.project_id !== projectFilter) return false;
    if (view === "completed") return !!task.completed_at;
    if (task.completed_at) return view === "all";
    if (view === "today") return !!task.due_date && task.due_date <= today();
    if (view === "upcoming") return !!task.due_date && task.due_date > today();
    return true;
  }), [tasks, view, projectFilter, query]);
  const selected = tasks.find(x => x.id === editor);
  const count = tasks.filter(x=>!x.completed_at).length;
  const navigate = (page: Screen, project: string|null = null) => {setView(page);setProjectFilter(project);setEditor(null);};
  const updateForm = (part: Partial<TaskForm>) => setForm(prev => ({...prev,...part}));
  const labels = { inbox:"My tasks", today:"Today", upcoming:"Upcoming", completed:"Completed", all:"All tasks", calendar:"Calendar", focus:"Focus" };
  const counts = {today:tasks.filter(t=>!t.completed_at&&!!t.due_date&&t.due_date<=today()).length,upcoming:tasks.filter(t=>!t.completed_at&&!!t.due_date&&t.due_date>today()).length};

  if (!token) return <main className="gc-app sign-in">
    <section className="gc-card auth-card">
      <span className="brand-mark" aria-hidden="true">◈</span><p className="eyebrow">GOREECLOUD · PRIVATE WORKSPACE</p>
      <h1>Where your plans come together.</h1>
      <p className="muted">Connect to your self-hosted GoreeCloud Tasks server. The API token stays in this browser tab's memory and is never stored by this app.</p>
      <form onSubmit={e=>{e.preventDefault();setToken(entry.trim());setEntry("");}}>
        <label htmlFor="api-token">Server API token</label>
        <input id="api-token" autoComplete="off" type="password" required minLength={32} value={entry} onChange={e=>setEntry(e.target.value)} placeholder="Enter your API token" />
        <button className="primary-btn full-width" type="submit">Open workspace</button>
      </form><small>Development preview · Use HTTPS outside localhost</small>
    </section>
  </main>;

  return <div className="gc-app workspace">
    <aside className="sidebar" aria-label="Workspace navigation">
      <div className="logo"><span className="brand-mark" aria-hidden="true">◈</span><div><strong>GoreeCloud</strong><small>TASKS</small></div></div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Views">
        {(["inbox","today","upcoming","calendar","completed","all","focus"] as Screen[]).map((screen,i)=>
          <button key={screen} className={"nav-item "+(view===screen&&projectFilter===null?"active":"")} onClick={()=>navigate(screen)} aria-current={view===screen&&projectFilter===null?"page":undefined}>
            <span aria-hidden="true">{["☷","◷","▦","▣","✓","≡","◎"][i]}</span>{labels[screen]}
            {screen==="today"&&counts.today>0&&<b>{counts.today}</b>}
          </button>)}
      </nav>
      <div className="sidebar-label project-label">PROJECTS</div>
      <nav aria-label="Projects">
        {projects.map(p=><button key={p.id} className={"nav-item "+(projectFilter===p.id?"active":"")} onClick={()=>navigate("inbox",p.id)}>
          <span className="project-dot" aria-hidden="true"></span>{p.name}</button>)}
      </nav>
      <form className="new-project" onSubmit={e=>{e.preventDefault();if(newProject.trim())void execute(async()=>{await request("/projects",{method:"POST",body:JSON.stringify({name:newProject})});setNewProject("");});}}>
        <label className="sr-only" htmlFor="project-name">New project name</label>
        <input id="project-name" maxLength={120} value={newProject} onChange={e=>setNewProject(e.target.value)} placeholder="+ New project" />
      </form>
      <div className="sidebar-bottom"><span className="status-dot"></span>Local-first architecture
        <button onClick={()=>{setToken("");setTasks([]);setProjects([]);setEntry("");}}>Disconnect</button>
      </div>
    </aside>
    <main className="main-content">
      <header className="topbar"><span>{today()}</span><div className="topbar-end">
        <span className="subtle">Self-hosted workspace</span>
        <button className="secondary-btn" disabled={busy} onClick={()=>void execute(async()=>{const data=await request<unknown>("/export");const file=new Blob([JSON.stringify(data,null,2)],{type:"application/json"});const url=URL.createObjectURL(file);const a=document.createElement("a");a.href=url;a.download="goreecloud-tasks-export.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);})}>Export JSON</button>
        <button className="secondary-btn" disabled={busy} onClick={()=>void execute(async()=>{
          const result=await fetch("/api/v1/export.ics",{headers:{"Authorization":"Bearer "+token}});
          if(!result.ok)throw new Error("Calendar export unavailable ("+result.status+")");
          const file=await result.blob();
          const url=URL.createObjectURL(file);
          const anchor=document.createElement("a");
          anchor.href=url;anchor.download="goreecloud-tasks.ics";anchor.click();
          setTimeout(()=>URL.revokeObjectURL(url),1000);
        })}>Export calendar</button>
      </div></header>
      <div className="content-grid">
        <section className="primary-column">
          <div className="page-heading"><p className="eyebrow">YOUR DAY, YOUR PACE</p><h1>{projectFilter?projects.find(p=>p.id===projectFilter)?.name||"Project":labels[view]}</h1><p className="muted">{count} active tasks across your workspace. A little progress counts.</p></div>
          {error && <div className="alert" role="alert">{error}<button onClick={()=>setError("")} aria-label="Dismiss error">×</button></div>}
          {view === "focus" ? <FocusTimer/> : <>
            <form className="task-composer gc-card" onSubmit={e=>{e.preventDefault();if(!form.title.trim())return;void execute(async()=>{
              await request("/tasks",{method:"POST",body:JSON.stringify({title:form.title,description:form.description,priority:form.priority,due_date:form.due_date||null,recurrence:form.recurrence,project_id:form.project_id||projectFilter||null,tags:form.tags.split(",").map(x=>x.trim()).filter(Boolean)})});setForm(emptyForm);
            });}}>
              <label className="sr-only" htmlFor="task-title">Task title</label>
              <input id="task-title" maxLength={240} required placeholder="What needs to get done?" value={form.title} onChange={e=>updateForm({title:e.target.value})}/>
              <div className="composer-details">
                <label>Due <input aria-label="Due date" type="date" value={form.due_date} onChange={e=>updateForm({due_date:e.target.value})}/></label>
                <label>Priority <select aria-label="Priority" value={form.priority} onChange={e=>updateForm({priority:Number(e.target.value)})}><option value={1}>P1</option><option value={2}>P2</option><option value={3}>P3</option><option value={4}>P4</option></select></label>
                <label>Repeat <select aria-label="Repeat" value={form.recurrence} onChange={e=>updateForm({recurrence:e.target.value as Task["recurrence"]})}><option value="none">Never</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label>
                <label>Project <select aria-label="Task project" value={form.project_id || projectFilter || ""} onChange={e=>updateForm({project_id:e.target.value})}><option value="">Inbox</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
                <label>Labels <input aria-label="Task labels" value={form.tags} onChange={e=>updateForm({tags:e.target.value})} placeholder="tag1, tag2" maxLength={480}/></label>
                <button className="primary-btn" type="submit" disabled={busy}>+ Add task</button>
              </div>
            </form>
            <div className="section-header"><h2>{view==="calendar"?"Monthly plan":view==="today"?"Scheduled for today":view==="upcoming"?"On the horizon":"Tasks"} <span className="count">{visible.length}</span></h2>
              <label className="sr-only" htmlFor="search-task">Search tasks</label><input id="search-task" type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search tasks" /></div>
            {view==="calendar" ? <CalendarView tasks={visible} onOpen={setEditor}/> : <div className="task-list">
              {visible.map(task=><article className={"task-row "+(task.completed_at?"is-complete":"")} key={task.id}>
                <button className="complete-button" disabled={busy} aria-label={(task.completed_at?"Reopen ":"Complete ")+task.title} title={task.completed_at?"Reopen":"Complete"} onClick={()=>void execute(async()=>{
                  await request("/tasks/"+encodeURIComponent(task.id)+"/"+(task.completed_at?"reopen":"complete"),{method:"POST",body:JSON.stringify({expected_version:task.version})});
                })}>{task.completed_at?"✓":""}</button>
                <button className="task-description" onClick={()=>setEditor(task.id)}>
                  <strong>{task.title}</strong><span>{task.due_date||"No due date"}{task.recurrence!=="none"?" · ↻ "+task.recurrence:""}{task.tags.length?" · #"+task.tags.join(" #"):""}</span>
                </button>
                <span className={"priority p"+task.priority}>P{task.priority}</span>
              </article>)}
              {!visible.length&&<div className="empty-state"><span aria-hidden="true">✧</span><h3>Space to breathe.</h3><p>No tasks in this view. Add one above or choose another list.</p></div>}
            </div>}
          </>}
        </section>
        <aside className="right-rail" aria-label="Task details and overview">
          {selected ? <TaskDetails key={selected.id} task={selected} projects={projects} disabled={busy} onClose={()=>setEditor(null)} onSave={data=>void execute(async()=>{await request("/tasks/"+selected.id,{method:"PATCH",body:JSON.stringify({expected_version:selected.version,...data})});setEditor(null);})} onDelete={()=>{if(window.confirm("Permanently delete this task?"))void execute(async()=>{await request("/tasks/"+selected.id+"?expected_version="+selected.version,{method:"DELETE"});setEditor(null);});}}/> :
          <><section className="gc-card overview"><p className="eyebrow">AT A GLANCE</p><h2>Keep the momentum.</h2><div className="stat-number">{count}</div><p className="muted">tasks on your plate</p><div className="stat-grid"><div><strong>{counts.today}</strong><span>Due now</span></div><div><strong>{counts.upcoming}</strong><span>Upcoming</span></div></div></section>
          <section className="tip-card"><span aria-hidden="true">✦</span><h3>One thing at a time.</h3><p>Choose your next meaningful step. Consistency builds clarity.</p><button onClick={()=>navigate("focus")}>Enter focus mode →</button></section></>}
        </aside>
      </div>
    </main>
  </div>;
}

function TaskDetails({task,projects,disabled,onSave,onDelete,onClose}:{
  task:Task;projects:Project[];disabled:boolean;onSave:(value:Omit<Partial<TaskForm>,"tags"|"due_date"|"project_id">&{tags:string[];due_date:string|null;project_id:string|null})=>void;onDelete:()=>void;onClose:()=>void
}) {
  const [data,setData]=useState<TaskForm>({title:task.title,description:task.description,due_date:task.due_date||"",priority:task.priority,project_id:task.project_id||"",recurrence:task.recurrence,tags:task.tags.join(", ")});
  return <section className="gc-card details">
    <div className="detail-header"><h2>Task details</h2><button className="secondary-btn" aria-label="Close task details" onClick={onClose}>×</button></div>
    <form onSubmit={e=>{e.preventDefault();onSave({...data,due_date:data.due_date||null,project_id:data.project_id||null,tags:data.tags.split(",").map(x=>x.trim()).filter(Boolean)});}}>
      <label>Title<input required maxLength={240} value={data.title} onChange={e=>setData({...data,title:e.target.value})}/></label>
      <label>Notes<textarea maxLength={16000} rows={5} value={data.description} onChange={e=>setData({...data,description:e.target.value})}/></label>
      <label>Project<select value={data.project_id} onChange={e=>setData({...data,project_id:e.target.value})}><option value="">Inbox</option>{projects.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label>
      <label>Due<input type="date" value={data.due_date} onChange={e=>setData({...data,due_date:e.target.value})}/></label>
      <label>Priority<select value={data.priority} onChange={e=>setData({...data,priority:Number(e.target.value)})}>{[1,2,3,4].map(n=><option value={n} key={n}>P{n}</option>)}</select></label>
      <label>Repeat<select value={data.recurrence} onChange={e=>setData({...data,recurrence:e.target.value as Task["recurrence"]})}>{["none","daily","weekly","monthly"].map(r=><option key={r} value={r}>{r}</option>)}</select></label>
      <label>Tags (comma-separated)<input value={data.tags} onChange={e=>setData({...data,tags:e.target.value})}/></label>
      <button className="primary-btn full-width" type="submit" disabled={disabled}>Save changes</button>
      <button className="danger-btn" type="button" disabled={disabled} onClick={onDelete}>Delete task</button>
    </form>
  </section>;
}
