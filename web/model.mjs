export const STORAGE_KEY = 'goreecloud.tasks.local.v1';
export const EMPTY = () => ({ schema: 1, projects: [], tasks: [] });
export function checkedDescription(value) {
  if (typeof value !== 'string' || !validUnicodeText(value) || value.length > 2000)
    throw new Error('Description must be valid Unicode text, at most 2000 characters.');
  return value;
}
export function checkedLabels(labels) {
  if (!Array.isArray(labels) || labels.length > 8) throw new Error('Up to 8 labels per task.');
  const seen = new Set();
  return labels.map(label => {
    if (typeof label !== 'string' || !validUnicodeText(label) ||
        !label.trim() || label.trim().length > 32 || label !== label.trim() ||
        /[,\u0000-\u001f\u007f]/u.test(label) || seen.has(label)) {
      throw new Error('Labels must be unique 1–32 character plain text without commas or controls.');
    }
    seen.add(label);
    return label;
  });
}
export function parseLabelInput(raw) {
  if (typeof raw !== 'string') throw new Error('Invalid labels.');
  return checkedLabels(raw.trim() ? raw.split(',').map(label => label.trim()) : []);
}
export function hydrate(raw) {
  try {
    const data = JSON.parse(raw);
    if (!data || ![1, 2, 3].includes(data.schema) || !Array.isArray(data.projects) || !Array.isArray(data.tasks)) return EMPTY();
    return { schema: data.schema, projects: data.projects.filter(p => p && typeof p.id === 'string' && typeof p.name === 'string'), tasks: data.tasks.filter(t => t && typeof t.id === 'string' && typeof t.title === 'string') };
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
export function newTask(title, projectId = null, due = '', priority = 4, description = '', labels = []) {
  const fields = validatedTaskFields(title, projectId, due, priority);
  const result = { id: crypto.randomUUID(), ...fields, completed: false, createdAt: new Date().toISOString(), completedAt: null };
  if (description !== '') result.description = checkedDescription(description);
  const normalized = checkedLabels(labels);
  if (normalized.length) result.labels = normalized;
  return result;
}
/** Return a new task without changing identity, creation or completion history. */
export function editTask(task, { title, projectId, due, priority, description, labels }, projects) {
  if (!task || typeof task !== 'object' || Array.isArray(task)) throw new Error('Task no longer exists.');
  const fields = validatedTaskFields(title, projectId, due, priority);
  if (!Array.isArray(projects) ||
      (fields.projectId !== null && !projects.some(project => project.id === fields.projectId))) {
    throw new Error('The chosen project no longer exists.');
  }
  const edited = { ...task, ...fields };
  if (description !== undefined) {
    const notes = checkedDescription(description);
    if (notes !== '' || Object.hasOwn(task, 'description')) edited.description = notes;
  }
  if (labels !== undefined) {
    const normalized = checkedLabels(labels);
    if (normalized.length || Object.hasOwn(task, 'labels')) edited.labels = normalized;
  }
  return edited;
}
/** Create a fresh open task without importing the source's identity or completion history. */
export function duplicateTask(task, projects) {
  if (!task || !Array.isArray(projects)) throw new Error('Task no longer exists.');
  if (task.projectId != null && !projects.some(project => project.id === task.projectId))
    throw new Error('The original project no longer exists.');
  return newTask(task.title, task.projectId, task.due, task.priority, task.description ?? '', task.labels ?? []);
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
/** Filter and sort without modifying stored task order or task records. */
export function selectTasks(tasks, view, today, query = '', options = {}) {
  const term = query.trim().toLocaleLowerCase();
  const priority = options.priority || 'all';
  const label = options.label || '';
  if (label && (!validUnicodeText(label) || label.length > 32)) throw new Error('Invalid label filter.');
  const sort = options.sort || 'smart';
  // Calendar arithmetic in UTC avoids shortening the range on DST changes.
  const end = new Date(today + 'T12:00:00Z');
  // Seven calendar dates including today (today through day six).
  end.setUTCDate(end.getUTCDate() + 6);
  const nextSevenDays = end.toISOString().slice(0, 10);
  const filtered = tasks.filter(t => {
    if (term && !t.title.toLocaleLowerCase().includes(term) &&
        !(t.description || '').toLocaleLowerCase().includes(term)) return false;
    if (priority !== 'all' && t.priority !== Number(priority)) return false;
    if (label && !(t.labels || []).includes(label)) return false;
    if (view === 'completed') return !!t.completed;
    if (t.completed) return false;
    if (view === 'inbox') return !t.projectId;
    if (view === 'today') return !!t.due && t.due <= today;
    if (view === 'overdue') return !!t.due && t.due < today;
    if (view === 'soon') return !!t.due && t.due >= today && t.due <= nextSevenDays;
    if (view === 'upcoming') return !!t.due && t.due > today;
    if (view === 'priority') return t.priority <= 2;
    if (view.startsWith('project:')) return t.projectId === view.slice(8);
    return true;
  });
  const byDue = (a, b) => (a.due || '9999-12-31').localeCompare(b.due || '9999-12-31');
  const byRecent = (a, b) => b.createdAt.localeCompare(a.createdAt);
  return filtered.sort((a, b) => {
    if (sort === 'due') return byDue(a, b) || a.priority - b.priority || byRecent(a, b);
    if (sort === 'newest') return byRecent(a, b);
    if (sort === 'title') return a.title.localeCompare(b.title) || byRecent(a, b);
    return a.priority - b.priority || byDue(a, b) || byRecent(a, b);
  });
}

/** All-or-nothing edits: validate every selected ID and field before writing. */
export function batchEditTasks(workspace, ids, changes, now = new Date().toISOString()) {
  if (!workspace || !Array.isArray(workspace.tasks) || !Array.isArray(workspace.projects) ||
      !Array.isArray(ids) || !ids.length || !changes || typeof changes !== 'object' ||
      Array.isArray(changes)) throw new Error('Invalid bulk edit.');
  const keys = Object.keys(changes);
  if (!keys.length || keys.some(key => !['completed', 'priority', 'projectId'].includes(key))) {
    throw new Error('Unsupported bulk edit.');
  }
  if ('completed' in changes && typeof changes.completed !== 'boolean') throw new Error('Invalid completion state.');
  if ('priority' in changes && (!Number.isInteger(changes.priority) || changes.priority < 1 || changes.priority > 4)) {
    throw new Error('Priority must be P1 through P4.');
  }
  if ('projectId' in changes &&
      (changes.projectId !== null && !workspace.projects.some(project => project.id === changes.projectId))) {
    throw new Error('The chosen project no longer exists.');
  }
  if ('completed' in changes && changes.completed && (!Number.isFinite(Date.parse(now)) || !now.endsWith('Z'))) {
    throw new Error('Invalid completion timestamp.');
  }
  const unique = new Set(ids);
  if (unique.size !== ids.length || ids.some(id => typeof id !== 'string')) throw new Error('Duplicate or invalid task selection.');
  const existing = new Map(workspace.tasks.map(task => [task.id, task]));
  for (const id of ids) if (!existing.has(id)) throw new Error('A selected task no longer exists.');
  const replacements = new Map();
  for (const id of ids) {
    const task = existing.get(id);
    let updated = { ...task };
    if ('priority' in changes || 'projectId' in changes) {
      updated = editTask(task, {
        title: task.title, due: task.due,
        priority: changes.priority ?? task.priority,
        projectId: 'projectId' in changes ? changes.projectId : task.projectId
      }, workspace.projects);
    }
    if ('completed' in changes && task.completed !== changes.completed) {
      updated.completed = changes.completed;
      updated.completedAt = changes.completed ? now : null;
    }
    replacements.set(id, updated);
  }
  workspace.tasks = workspace.tasks.map(task => replacements.get(task.id) || task);
  return replacements.size;
}
export function localDate(now = new Date()) {
  const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
  return y+'-'+m+'-'+d;
}
