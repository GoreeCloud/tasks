import { useMemo } from "react";

export type BoardTask = {
  id: string; title: string; description: string; due_date: string | null;
  priority: number; tags: string[]; parent_id: string | null;
};

const levels = [
  {priority:1, label:"P1 · Urgent", subtitle:"Highest priority"},
  {priority:2, label:"P2 · High", subtitle:"Next to tackle"},
  {priority:3, label:"P3 · Medium", subtitle:"Work in progress"},
  {priority:4, label:"P4 · Low", subtitle:"Whenever it fits"}
];

export function PriorityBoard({tasks, onOpen, onMove, busy}:{
  tasks: BoardTask[];
  onOpen:(id:string)=>void;
  onMove:(id:string,currentPriority:number,priority:number)=>void;
  busy:boolean;
}) {
  const groups = useMemo(() => levels.map(level => ({
    ...level,
    items: tasks.filter(task=>task.priority===level.priority)
  })),[tasks]);
  return <section className="board-panel" aria-label="Priority task board">
    <p className="muted board-help">Organize by priority. Use Move up or Move down to change a task's priority without dragging.</p>
    <div className="board-grid">
      {groups.map(group=><section key={group.priority} className="board-lane" aria-label={group.label}>
        <header className="board-heading">
          <div><h3>{group.label}</h3><p>{group.subtitle}</p></div>
          <span className="count">{group.items.length}</span>
        </header>
        <div className="board-cards">
          {group.items.map(task=><article key={task.id} className="board-card gc-card">
            <button type="button" className="board-card-title" onClick={()=>onOpen(task.id)}
              aria-label={"Edit " + task.title}>{task.title}</button>
            <p className="muted">{task.parent_id?"↳ Subtask · ":""}{task.due_date||"No due date"}</p>
            {task.tags.length>0&&<p className="board-tags">{task.tags.map(tag=>"#"+tag).join(" · ")}</p>}
            <div className="board-move">
              <button type="button" className="secondary-btn" disabled={busy||group.priority===1}
                aria-label={"Move "+task.title+" to P"+(group.priority-1)}
                onClick={()=>onMove(task.id,group.priority,group.priority-1)}>Move up</button>
              <button type="button" className="secondary-btn" disabled={busy||group.priority===4}
                aria-label={"Move "+task.title+" to P"+(group.priority+1)}
                onClick={()=>onMove(task.id,group.priority,group.priority+1)}>Move down</button>
            </div>
          </article>)}
          {group.items.length===0&&<p className="muted board-empty">No tasks</p>}
        </div>
      </section>)}
    </div>
  </section>;
}
