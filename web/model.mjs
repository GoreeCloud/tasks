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
export function newTask(title, projectId = null, due = '', priority = 4) {
  if (!validUnicodeText(title)) throw new Error('Task title must be valid Unicode text.');
  const name = title.trim();
  if (!name || name.length > 240) throw new Error('Task title must be 1–240 characters.');
  if (projectId !== null && typeof projectId !== 'string') throw new Error('Invalid project ID.');
  if (typeof due !== 'string') throw new Error('Due date must be text.');
  const p = typeof priority === 'string' && /^[1-4]$/.test(priority) ? Number(priority) : priority;
  if (typeof p !== 'number' || !Number.isInteger(p) || p < 1 || p > 4) throw new Error('Priority must be P1 through P4.');
  if (due && (!/^\d{4}-\d{2}-\d{2}$/.test(due) || Number.isNaN(Date.parse(due + 'T00:00:00Z')) || new Date(due + 'T00:00:00Z').toISOString().slice(0, 10) !== due)) throw new Error('Due date must be a valid YYYY-MM-DD date.');
  return { id: crypto.randomUUID(), title: name, projectId: projectId || null, due, priority: p, completed: false, createdAt: new Date().toISOString(), completedAt: null };
}
export function selectTasks(tasks, view, today, query = '') {
  const term = query.trim().toLocaleLowerCase();
  return tasks.filter(t => {
    if (term && !t.title.toLocaleLowerCase().includes(term)) return false;
    if (view === 'completed') return !!t.completed;
    if (t.completed) return false;
    if (view === 'inbox') return !t.projectId;
    if (view === 'today') return t.due === today || (!!t.due && t.due < today);
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
