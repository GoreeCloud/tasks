/**
 * Browser-local GoreeCloud Tasks backup contract. Pure functions for testability.
 * Deliberately preserves only documented fields; no HTML, keys or credentials.
 */
export const MAX_BACKUP_BYTES = 2 * 1024 * 1024;
export const MAX_RECORDS = 10_000;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_ID_LENGTH = 128;

export function validDate(value) {
  if (value === '') return true;
  if (typeof value !== 'string' || !ISO_DATE.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function validId(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= MAX_ID_LENGTH && !/[\u0000-\u001f\u007f]/.test(value);
}
function isoTimestamp(value) {
  return typeof value === 'string' && value.length <= 40 && !Number.isNaN(Date.parse(value)) && /^\d{4}-\d\d-\d\dT/.test(value);
}
export function validateBackupText(raw) {
  if (typeof raw !== 'string' || new TextEncoder().encode(raw).length > MAX_BACKUP_BYTES) {
    throw new Error('Backup is too large or unreadable (2 MiB maximum).');
  }
  let value;
  try { value = JSON.parse(raw); } catch { throw new Error('Not a valid JSON backup.'); }
  return validateBackup(value);
}
export function validateBackup(value) {
  if (!isObject(value) || value.schema !== 1 || !Array.isArray(value.projects) || !Array.isArray(value.tasks)) {
    throw new Error('Unsupported or incomplete GoreeCloud Tasks backup schema.');
  }
  if (value.tasks.length > MAX_RECORDS || value.projects.length > MAX_RECORDS) {
    throw new Error('Backup exceeds the record limit.');
  }
  const projectIds = new Set();
  const projects = value.projects.map(project => {
    if (!isObject(project) || !validId(project.id) || typeof project.name !== 'string' ||
        project.name.trim().length < 1 || project.name.trim().length > 100 || projectIds.has(project.id)) {
      throw new Error('Backup contains an invalid or duplicate project.');
    }
    projectIds.add(project.id);
    return { id: project.id, name: project.name.trim() };
  });
  const taskIds = new Set();
  const tasks = value.tasks.map(task => {
    if (!isObject(task) || !validId(task.id) || taskIds.has(task.id) ||
        typeof task.title !== 'string' || task.title.trim().length < 1 || task.title.trim().length > 240 ||
        !Number.isInteger(task.priority) || task.priority < 1 || task.priority > 4 ||
        typeof task.completed !== 'boolean' || !validDate(task.due) ||
        (task.projectId !== null && (!validId(task.projectId) || !projectIds.has(task.projectId))) ||
        !isoTimestamp(task.createdAt) ||
        (task.completedAt !== null && !isoTimestamp(task.completedAt)) ||
        (task.completed !== (task.completedAt !== null))) {
      throw new Error('Backup contains an invalid, duplicate or unlinked task.');
    }
    taskIds.add(task.id);
    return {
      id: task.id, title: task.title.trim(), projectId: task.projectId,
      due: task.due, priority: task.priority, completed: task.completed,
      createdAt: task.createdAt, completedAt: task.completedAt
    };
  });
  return { schema: 1, projects, tasks };
}
export function exportBackup(state) {
  const json = JSON.stringify(validateBackup(state), null, 2);
  if (new TextEncoder().encode(json).length > MAX_BACKUP_BYTES) {
    throw new Error('Workspace exceeds the 2 MiB JSON export limit.');
  }
  return json;
}
