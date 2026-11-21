import { useRef, useState } from "react";

type Project = {id:string;name:string};
type CsvFormat = "generic"|"todoist";
type CsvRow = {title:string;description:string;due_date:string|null;priority:number;tags:string[];
               recurrence:string;parent_index:number|null};
type Preview = {format:CsvFormat;count:number;tasks:CsvRow[];warnings:string[];checksum:string};
type ImportResponse = {count:number;ids:string[];warnings:string[];checksum:string};
type Request = <T,>(path:string,init?:RequestInit)=>Promise<T>;

export function CsvImportView({request,projects,onImported}:{
  request:Request;projects:Project[];onImported:()=>Promise<void>
}) {
  const fileSelection=useRef(0);
  const [format,setFormat]=useState<CsvFormat>("generic");
  const [projectId,setProjectId]=useState("");
  const [flatten,setFlatten]=useState(false);
  const [fileName,setFileName]=useState("");
  const [csvText,setCsvText]=useState("");
  const [preview,setPreview]=useState<Preview|null>(null);
  const [key,setKey]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [success,setSuccess]=useState("");
  const source=()=>({format,csv_text:csvText,project_id:projectId||null,flatten_hierarchy:flatten});
  const resetPreview=()=>{setPreview(null);setKey("");setSuccess("");setError("");};
  const selectFile=async (file?:File)=>{
    const selection=++fileSelection.current;
    resetPreview();setCsvText("");setFileName("");
    if(!file)return;
    if(file.size>500000){setError("CSV files must not exceed 500,000 bytes");return;}
    try {
      const text=await file.text();
      if(selection!==fileSelection.current)return;
      if(new TextEncoder().encode(text).length>500000){
        setError("CSV exceeds the 500,000-byte limit");return;
      }
      setCsvText(text);setFileName(file.name);
    } catch {if(selection===fileSelection.current)setError("Unable to read this local CSV file");}
  };
  const makePreview=async()=>{
    setBusy(true);setError("");setSuccess("");
    try {
      const result=await request<Preview>("/import/csv/preview",{
        method:"POST",body:JSON.stringify(source())
      });
      setPreview(result);setKey(crypto.randomUUID());
    } catch(e) {
      setPreview(null);setKey("");
      setError(e instanceof Error?e.message:"CSV preview failed");
    } finally {setBusy(false);}
  };
  const commit=async()=>{
    if(!preview||!key)return;
    setBusy(true);setError("");
    try {
      const result=await request<ImportResponse>("/import/csv",{
        method:"POST",headers:{"Idempotency-Key":key},
        body:JSON.stringify({...source(),checksum:preview.checksum})
      });
      await onImported();
      setSuccess(result.count+" tasks imported to the selected workspace project.");
      setPreview(null);setKey("");setCsvText("");setFileName("");
    } catch(e) {
      // Preserve exact content, preview and idempotency key when the network
      // outcome is uncertain, preventing duplicate creation on explicit retry.
      setError(e instanceof Error?e.message:"Import did not complete");
    } finally {setBusy(false);}
  };
  return <section className="csv-import-panel gc-card" aria-label="CSV task migration">
    <p className="eyebrow">PORTABLE TASK DATA</p>
    <h2>Import with a preview.</h2>
    <p className="muted">Your CSV stays in this browser tab until you request a preview. Nothing is written to the server until you explicitly confirm. Importing here does not read or modify your Todoist or Vikunja account.</p>
    {error&&<div className="alert" role="alert">{error}<button type="button"
      aria-label="Dismiss import error" onClick={()=>setError("")}>×</button></div>}
    {success&&<p className="csv-success" role="status">{success}</p>}
    <div className="csv-form">
      <label>CSV format
        <select aria-label="CSV format" disabled={busy} value={format} onChange={event=>{
          resetPreview();setFormat(event.target.value as CsvFormat);
        }}>
          <option value="generic">GoreeCloud / generic CSV</option>
          <option value="todoist">Todoist project CSV (date-only subset)</option>
        </select>
      </label>
      <label>Destination project
        <select aria-label="Import destination project" disabled={busy} value={projectId} onChange={event=>{
          resetPreview();setProjectId(event.target.value);
        }}>
          <option value="">Inbox</option>
          {projects.map(project=><option key={project.id} value={project.id}>{project.name}</option>)}
        </select>
      </label>
      <label>CSV file
        <input type="file" disabled={busy} accept=".csv,text/csv" aria-label="Choose CSV file" onChange={event=>
          void selectFile(event.target.files?.[0])
        }/>
      </label>
      {fileName&&<p className="muted">Selected: {fileName}</p>}
      {format==="todoist"&&<label className="csv-checkbox">
        <input type="checkbox" disabled={busy} checked={flatten} onChange={event=>{
          resetPreview();setFlatten(event.target.checked);
        }}/> Flatten orphaned indentation instead of rejecting it
      </label>}
      <p className="muted csv-note">
        {format==="generic"?
          "Required column: title. Optional: description, due_date (YYYY-MM-DD), priority (1–4), tags (separate with |), recurrence and parent_row.":
          "Todoist: TYPE, CONTENT, PRIORITY and INDENT are supported. Dates must be YYYY-MM-DD; natural-language recurrence, timezones, sections and notes are not converted automatically."}
      </p>
      <button type="button" className="primary-btn" onClick={()=>void makePreview()}
        disabled={busy||!csvText.trim()}>Preview import</button>
    </div>
    {preview&&<div className="csv-preview">
      <h3>Ready to import {preview.count} tasks</h3>
      {preview.warnings.length>0&&<section className="csv-warnings" aria-label="Import limitations">
        <h4>Review unsupported data before importing</h4>
        <ul>{preview.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul>
      </section>}
      <ol>{preview.tasks.slice(0,10).map((task,index)=><li key={index}>
        <strong>{task.title}</strong>
        <span className="muted">P{task.priority}{task.due_date?" · "+task.due_date:""}
          {task.parent_index!==null?" · Subtask":""}</span>
      </li>)}</ol>
      {preview.count>10&&<p className="muted">...and {preview.count-10} more tasks.</p>}
      <p className="muted">The selected destination is {projects.find(p=>p.id===projectId)?.name||"Inbox"}. You can cancel without writing anything.</p>
      <div className="csv-actions">
        <button type="button" className="primary-btn" disabled={busy} onClick={()=>void commit()}>
          Confirm import {preview.count} tasks
        </button>
        <button type="button" className="secondary-btn" onClick={resetPreview} disabled={busy}>Cancel preview</button>
      </div>
    </div>}
  </section>;
}
