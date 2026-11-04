import { validUnicodeText, checkedDescription, checkedLabels } from './model.mjs';
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
  return validUnicodeText(value) && value.length > 0 && value.length <= MAX_ID_LENGTH && !/[\u0000-\u001f\u007f]/.test(value);
}
// Parse only the ISO-8601 subset Android OffsetDateTime accepts; Date.parse
// otherwise normalizes impossible days and the 24:00 hour instead of failing.
export function isoTimestamp(value) {
  if (typeof value !== 'string' || value.length > 40) return false;
  const parts = /^(\d{4}-\d{2}-\d{2})T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)(?:\.(\d{1,9}))?(Z|([+-])(\d{2}):([0-5]\d))$/.exec(value);
  if (!parts || !validDate(parts[1])) return false;
  if (parts[7]) {
    const hours = Number(parts[8]);
    const minutes = Number(parts[9]);
    if (hours > 18 || (hours === 18 && minutes !== 0)) return false;
  }
  // Android's portable format requires a positive, representable epoch ms.
  const millis = Date.parse(value);
  return Number.isFinite(millis) && millis > 0;
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
  if (!isObject(value) || ![1, 2, 3].includes(value.schema) || !Array.isArray(value.projects) || !Array.isArray(value.tasks)) {
    throw new Error('Unsupported or incomplete GoreeCloud Tasks backup schema.');
  }
  if (value.tasks.length > MAX_RECORDS || value.projects.length > MAX_RECORDS) {
    throw new Error('Backup exceeds the record limit.');
  }
  const projectIds = new Set();
  const projects = value.projects.map(project => {
    if (!isObject(project) || !validId(project.id) || !validUnicodeText(project.name) ||
        project.name.trim().length < 1 || project.name.trim().length > 100 || projectIds.has(project.id)) {
      throw new Error('Backup contains an invalid or duplicate project.');
    }
    projectIds.add(project.id);
    return { id: project.id, name: project.name.trim() };
  });
  const taskIds = new Set();
  const tasks = value.tasks.map(task => {
    if (!isObject(task) || !validId(task.id) || taskIds.has(task.id) ||
        !validUnicodeText(task.title) || task.title.trim().length < 1 || task.title.trim().length > 240 ||
        !Number.isInteger(task.priority) || task.priority < 1 || task.priority > 4 ||
        typeof task.completed !== 'boolean' || !validDate(task.due) ||
        (task.projectId !== null && (!validId(task.projectId) || !projectIds.has(task.projectId))) ||
        !isoTimestamp(task.createdAt) ||
        (task.completedAt !== null && !isoTimestamp(task.completedAt)) ||
        (task.completed !== (task.completedAt !== null))) {
      throw new Error('Backup contains an invalid, duplicate or unlinked task.');
    }
    // Schema 1 has no description field: reject nonempty notes instead of losing them.
    if (value.schema === 1 && Object.hasOwn(task, 'description'))
      throw new Error('Descriptions require schema 2; export must not drop notes.');
    if (value.schema < 3 && Object.hasOwn(task, 'labels'))
      throw new Error('Labels require schema 3; export must not drop labels.');
    const description = value.schema >= 2 ? checkedDescription(task.description) : undefined;
    const labels = value.schema === 3 ? checkedLabels(task.labels) : undefined;
    taskIds.add(task.id);
    return {
      ...(value.schema >= 2 ? { description } : {}),
      ...(value.schema === 3 ? { labels } : {}),
      id: task.id, title: task.title.trim(), projectId: task.projectId,
      due: task.due, priority: task.priority, completed: task.completed,
      createdAt: task.createdAt, completedAt: task.completedAt
    };
  });
  return { schema: value.schema, projects, tasks };
}
export function exportBackup(state) {
  if (!isObject(state) || ![1, 2, 3].includes(state.schema) || !Array.isArray(state.tasks)) {
    throw new Error('Unsupported or incomplete GoreeCloud Tasks backup schema.');
  }
  // Editing can leave empty optional fields on legacy in-memory task records.
  // Validate those fields first, then include them only in a schema that owns
  // them. Never discard nonempty notes or labels or silently downgrade schema 4.
  const inspected = state.tasks.map(task => {
    if (!isObject(task)) throw new Error('Backup contains an invalid task.');
    const description = Object.hasOwn(task, 'description') ? checkedDescription(task.description) : '';
    const labels = Object.hasOwn(task, 'labels') ? checkedLabels(task.labels) : [];
    return { task, description, labels };
  });
  const version = state.schema === 3 || inspected.some(row => row.labels.length) ? 3 :
    state.schema === 2 || inspected.some(row => row.description !== '') ? 2 : 1;
  const compatible = { ...state, schema: version, tasks: inspected.map(({ task, description, labels }) => {
    const { description: _originalDescription, labels: _originalLabels, ...base } = task;
    return {
      ...base,
      ...(version >= 2 ? { description } : {}),
      ...(version === 3 ? { labels } : {})
    };
  }) };
  const json = JSON.stringify(validateBackup(compatible), null, 2);
  if (new TextEncoder().encode(json).length > MAX_BACKUP_BYTES) {
    throw new Error('Workspace exceeds the 2 MiB JSON export limit.');
  }
  return json;
}
