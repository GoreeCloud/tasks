export const STORAGE_KEY = 'goreecloud.tasks.local.v1';
export const EMPTY = () => ({ schema: 1, projects: [], tasks: [] });
export function hydrate(raw) {
  try {
    const data = JSON.parse(raw);
    if (!data || data.schema !== 1 || !Array.isArray(data.projects) || !Array.isArray(data.tasks)) return EMPTY();
    return { schema: 1, projects: data.projects.filter(p => p && typeof p.id === 'string' && typeof p.name === 'string'), tasks: data.tasks.filter(t => t && typeof t.id === 'string' && typeof t.title === 'string') };
  } catch { return EMPTY(); }
}
export function validUnicodeText(value) {
  if (typeof value !== 'string') return false;
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (code >= 0xD800 && code <= 0xDBFF) {
      const trailing = value.charCodeAt(++i);
      if (!(trailing >= 0xDC00 && trailing <= 0xDFFF)) return false;
    } else if (code >= 0xDC00 && code <= 0xDFFF) return false;
  }
  return true;
}
/** Validate the same editable fields for new tasks and updates. */
function validatedTaskFields(title, projectId, due, priority) {
  if (!validUnicodeText(title)) throw new Error('Task title must be valid Unicode text.');
  const name = title.trim();
  if (!name || name.length > 240) throw new Error('Task title must be 1–240 characters.');
  if (projectId !== null && typeof projectId !== 'string') throw new Error('Invalid project ID.');
  if (typeof due !== 'string') throw new Error('Due date must be text.');
  const p = typeof priority === 'string' && /^[1-4]$/.test(priority) ? Number(priority) : priority;
  if (typeof p !== 'number' || !Number.isInteger(p) || p < 1 || p > 4) throw new Error('Priority must be P1 through P4.');
  if (due && (!/^\d{4}-\d{2}-\d{2}$/.test(due) || Number.isNaN(Date.parse(due + 'T00:00:00Z')) || new Date(due + 'T00:00:00Z').toISOString().slice(0, 10) !== due)) throw new Error('Due date must be a valid YYYY-MM-DD date.');
  return { title: name, projectId: projectId || null, due, priority: p };
}
export function newTask(title, projectId = null, due = '', priority = 4) {
  const fields = validatedTaskFields(title, projectId, due, priority);
  return { id: crypto.randomUUID(), ...fields, completed: false, createdAt: new Date().toISOString(), completedAt: null };
}
/** Return a new task without changing identity, creation or completion history. */
export function editTask(task, { title, projectId, due, priority }, projects) {
  if (!task || typeof task !== 'object' || Array.isArray(task)) throw new Error('Task no longer exists.');
  const fields = validatedTaskFields(title, projectId, due, priority);
  if (!Array.isArray(projects) ||
      (fields.projectId !== null && !projects.some(project => project.id === fields.projectId))) {
    throw new Error('The chosen project no longer exists.');
  }
  return { ...task, ...fields };
}
/** Remove exactly one task from a draft; caller persists it only after validation. */
export function deleteTask(draft, id) {
  if (!draft || !Array.isArray(draft.tasks)) throw new Error('Invalid task workspace.');
  const index = draft.tasks.findIndex(task => task.id === id);
  if (index < 0) throw new Error('Task no longer exists.');
  return draft.tasks.splice(index, 1)[0];
}
/** Reinsert an in-session deleted task without fabricating completion history. */
export function undoTaskDelete(draft, task) {
  if (!draft || !Array.isArray(draft.tasks) || !Array.isArray(draft.projects) ||
      !task || typeof task.id !== 'string') throw new Error('Invalid undo state.');
  if (draft.tasks.some(entry => entry.id === task.id)) throw new Error('Task already exists.');
  if (task.projectId !== null &&
      !draft.projects.some(project => project.id === task.projectId)) {
    throw new Error('The original project no longer exists.');
  }
  // The enclosing exportBackup() also validates the complete portable schema.
  draft.tasks.push(structuredClone(task));
}
export function selectTasks(tasks, view, today, query = '') {
  const term = query.trim().toLocaleLowerCase();
  // Calendar-day arithmetic is performed on YYYY-MM-DD strings, not on local
  // 24-hour durations that can skip or repeat a daylight-saving hour.
  const tomorrow = new Date(today + 'T00:00:00Z');
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  const tomorrowKey = tomorrow.toISOString().slice(0, 10);
  return tasks.filter(t => {
    if (term && !t.title.toLocaleLowerCase().includes(term)) return false;
    if (view === 'completed') return !!t.completed;
    if (t.completed) return false;
    if (view === 'inbox') return !t.projectId;
    if (view === 'today') return t.due === today || (!!t.due && t.due < today);
    if (view === 'tomorrow') return t.due === tomorrowKey;
    if (view === 'upcoming') return !!t.due && t.due > today;
    if (view === 'priority') return t.priority <= 2;
    if (view.startsWith('project:')) return t.projectId === view.slice(8);
    return true;
  }).sort((a, b) => a.priority - b.priority || (a.due || '9999').localeCompare(b.due || '9999') || b.createdAt.localeCompare(a.createdAt));
}
export function localDate(now = new Date()) {
  const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
  return y+'-'+m+'-'+d;
}
