import { useMemo, useState } from "react";

export type CalendarTask = {
  id: string;
  title: string;
  due_date: string | null;
  priority: number;
  completed_at: string | null;
};

const dayKey = (date: Date) =>
  [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"),
   String(date.getDate()).padStart(2, "0")].join("-");

function moveMonth(date: Date, months: number) {
  return new Date(date.getFullYear(), date.getMonth() + months, 1);
}

const dateLabel = (key: string) => new Date(key + "T12:00:00").toLocaleDateString(
  undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" }
);

/** Month grid uses local calendar dates, never UTC date-string parsing. */
export function CalendarView({ tasks, onOpen }: {
  tasks: CalendarTask[]; onOpen: (taskId: string) => void;
}) {
  const [month, setMonth] = useState(() => {
    const current = new Date();
    return new Date(current.getFullYear(), current.getMonth(), 1);
  });
  const [selected, setSelected] = useState(() => dayKey(new Date()));
  const entries = useMemo(() => {
    const dates = new Map<string, CalendarTask[]>();
    for (const task of tasks) {
      if (!task.due_date || task.completed_at) continue;
      const current = dates.get(task.due_date) || [];
      current.push(task);
      dates.set(task.due_date, current);
    }
    for (const group of dates.values()) group.sort((a, b) => a.priority - b.priority || a.title.localeCompare(b.title));
    return dates;
  }, [tasks]);
  const grid = useMemo(() => Array.from({ length: 42 }, (_, index) => {
    const date = new Date(month.getFullYear(), month.getMonth(), index + 1 - month.getDay());
    return { key: dayKey(date), inMonth: date.getMonth() === month.getMonth(), number: date.getDate() };
  }), [month]);
  const daily = entries.get(selected) || [];
  const monthTitle = month.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  return <section className="calendar-panel gc-card" aria-label="Task calendar">
    <header className="calendar-heading">
      <div>
        <p className="eyebrow">PLANNING</p>
        <h3>{monthTitle}</h3>
      </div>
      <div className="calendar-actions">
        <button className="secondary-btn" type="button" onClick={() => setMonth(moveMonth(month,-1))}
          aria-label="Previous month">‹</button>
        <button className="secondary-btn" type="button" onClick={() => {
          const current = new Date(); setMonth(new Date(current.getFullYear(),current.getMonth(),1));setSelected(dayKey(current));
        }}>Today</button>
        <button className="secondary-btn" type="button" onClick={() => setMonth(moveMonth(month,1))}
          aria-label="Next month">›</button>
      </div>
    </header>
    <div className="calendar-grid" role="group" aria-label={monthTitle + " days"}>
      {["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(day =>
        <span className="calendar-weekday" key={day}>{day}</span>
      )}
      {grid.map(day => {
        const dayTasks = entries.get(day.key) || [];
        return <div key={day.key} className={"calendar-cell"+(day.inMonth?"":" calendar-other")+(selected===day.key?" calendar-selected":"")}>
          <button className="calendar-date" type="button" onClick={() => setSelected(day.key)}
            aria-label={"Show tasks for " + dateLabel(day.key) + ": " + dayTasks.length}
            aria-pressed={selected===day.key}>
            <time dateTime={day.key}>{day.number}</time>
            {dayTasks.length > 0 && <span className="calendar-day-count">{dayTasks.length}</span>}
          </button>
          <div className="calendar-events">
            {dayTasks.slice(0,2).map(task => <button type="button" key={task.id}
              onClick={() => {setSelected(day.key);onOpen(task.id);}}
              title={task.title} className={"calendar-event priority-"+task.priority}>{task.title}</button>)}
            {dayTasks.length > 2 && <span className="calendar-more">+{dayTasks.length - 2} more</span>}
          </div>
        </div>;
      })}
    </div>
    <div className="calendar-agenda">
      <h4>{dateLabel(selected)} <span className="count">{daily.length}</span></h4>
      {daily.length===0 ? <p className="muted">Nothing scheduled for this day.</p> :
        <div className="calendar-agenda-list">{daily.map(task => <button key={task.id}
          type="button" onClick={() => onOpen(task.id)} className="calendar-agenda-task">
          <span>{task.title}</span><span className={"priority p"+task.priority}>P{task.priority}</span>
        </button>)}</div>}
    </div>
  </section>;
}
