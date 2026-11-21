import { useCallback, useEffect, useState } from "react";

type Habit = {
  id: string; name: string; description: string; version: number;
  checked_in_today: boolean; current_streak: number; total_checkins: number; as_of: string;
};

export type HabitsRequest = <T,>(path: string, init?: RequestInit) => Promise<T>;

function localDate() {
  const day = new Date();
  return [day.getFullYear(),String(day.getMonth()+1).padStart(2,"0"),
          String(day.getDate()).padStart(2,"0")].join("-");
}

export function HabitsView({request}:{request:HabitsRequest}) {
  const [habits,setHabits] = useState<Habit[]>([]);
  const [newName,setNewName] = useState("");
  const [newDescription,setNewDescription] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [editing,setEditing] = useState<string|null>(null);
  const [editName,setEditName] = useState("");
  const [editNotes,setEditNotes] = useState("");

  const refresh=useCallback(async()=>{
    const loaded=await request<Habit[]>("/habits?as_of="+localDate());
    setHabits(loaded);
  },[request]);

  useEffect(()=>{
    let active=true;
    void request<Habit[]>("/habits?as_of="+localDate())
      .then(items=>{if(active)setHabits(items);})
      .catch(err=>{if(active)setError(err instanceof Error?err.message:"Unable to load habits");});
    return ()=>{active=false;};
  },[request]);

  async function mutate(operation:()=>Promise<unknown>) {
    setBusy(true);setError("");
    try {await operation();await refresh();}
    catch(err) {setError(err instanceof Error?err.message:"Habit request failed");}
    finally {setBusy(false);}
  }

  return <section className="habit-panel" aria-label="Daily habit tracker">
    <p className="muted habit-notice">Simple daily habits. Check-ins are saved to your self-hosted server, not to browser storage. Automatic reminders and offline habit sync are not available yet.</p>
    {error && <div className="alert" role="alert">{error}
      <button type="button" onClick={()=>setError("")} aria-label="Dismiss habit error">×</button>
    </div>}
    <form className="gc-card habit-composer" onSubmit={event=>{
      event.preventDefault();if(!newName.trim())return;
      void mutate(async()=>{
        await request("/habits",{method:"POST",body:JSON.stringify({name:newName,description:newDescription})});
        setNewName("");setNewDescription("");
      });
    }}>
      <h2>Build a small routine</h2>
      <label>Habit name<input required maxLength={120} value={newName}
        onChange={event=>setNewName(event.target.value)} placeholder="e.g. Read 15 minutes"/></label>
      <label>Notes (optional)<textarea value={newDescription} maxLength={16000}
        onChange={event=>setNewDescription(event.target.value)} rows={2}/></label>
      <button className="primary-btn" type="submit" disabled={busy||!newName.trim()}>+ Create habit</button>
    </form>
    <div className="section-header"><h2>Daily check-ins <span className="count">{habits.length}</span></h2>
      <button type="button" className="secondary-btn" disabled={busy} onClick={()=>void mutate(async()=>{})}>Refresh</button>
    </div>
    <div className="habit-list">
      {habits.map(habit=><article className="gc-card habit-item" key={habit.id}>
        <div className="habit-main">
          <button className={habit.checked_in_today?"habit-check checked":"habit-check"}
            type="button" disabled={busy}
            aria-label={(habit.checked_in_today?"Undo today's check-in for ":"Check in today for ")+habit.name}
            aria-pressed={habit.checked_in_today}
            onClick={()=>void mutate(async()=>{
              const day=localDate();
              if(habit.checked_in_today)await request("/habits/"+encodeURIComponent(habit.id)+
                "/checkins/"+day+"?expected_version="+habit.version,{method:"DELETE"});
              else await request("/habits/"+encodeURIComponent(habit.id)+"/checkins",{
                method:"POST",body:JSON.stringify({day,expected_version:habit.version})
              });
            })}>{habit.checked_in_today?"✓":"○"}</button>
          <div className="habit-description">
            <strong>{habit.name}</strong>
            {habit.description&&<p>{habit.description}</p>}
            <span>{habit.current_streak} day streak · {habit.total_checkins} total check-ins</span>
          </div>
          <span className="habit-day-label">{habit.checked_in_today?"Done today":"Not yet today"}</span>
        </div>
        {editing===habit.id ? <form className="habit-edit" onSubmit={event=>{
          event.preventDefault(); if(!editName.trim())return;
          void mutate(async()=>{
            await request("/habits/"+encodeURIComponent(habit.id),{
              method:"PATCH",body:JSON.stringify({expected_version:habit.version,name:editName,description:editNotes})
            });setEditing(null);
          });
        }}>
          <label>Edit name<input required maxLength={120} value={editName}
            onChange={event=>setEditName(event.target.value)}/></label>
          <label>Edit notes<textarea rows={2} maxLength={16000} value={editNotes}
            onChange={event=>setEditNotes(event.target.value)}/></label>
          <div className="habit-actions"><button className="primary-btn" disabled={busy} type="submit">Save habit</button>
            <button className="secondary-btn" type="button" onClick={()=>setEditing(null)}>Cancel</button></div>
        </form> :
        <div className="habit-actions"><button type="button" className="secondary-btn" onClick={()=>{
          setEditing(habit.id);setEditName(habit.name);setEditNotes(habit.description);
        }}>Edit habit</button>
        <button type="button" className="danger-btn" disabled={busy} onClick={()=>{
          if(window.confirm("Permanently delete this habit and all its check-in history?"))void mutate(async()=>{
            await request("/habits/"+encodeURIComponent(habit.id)+"?expected_version="+habit.version,{method:"DELETE"});
          });
        }}>Delete habit</button></div>}
      </article>)}
      {!habits.length&&<p className="muted habit-empty">No habits yet. Create one to start tracking daily progress.</p>}
    </div>
  </section>;
}
