import { EMPTY } from './model.mjs';
import {
  exportBackup, isoTimestamp, validateBackup, validateBackupText
} from './backup.mjs';

/*
 * The browser's private, device-local storage envelope is NOT a portable
 * schema-1 backup. Keep every active and deleted row in one localStorage key
 * so a successful setItem cannot commit just half of a delete/restore.
 *
 * Upgrades are lazy: the first successful edit replaces an old schema-1
 * snapshot with this envelope. Read/validation errors never rewrite a key.
 */
export const LOCAL_FORMAT = 'goreecloud.tasks.local.v2';
export const MAX_TRASH_RECORDS = 1000;
export const MAX_LOCAL_BYTES = 3 * 1024 * 1024;

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function checkedTrash(workspace, trash) {
  if (!Array.isArray(trash) || trash.length > MAX_TRASH_RECORDS) {
    throw new Error('Local Trash is invalid or full; no data was saved.');
  }
  const active = new Set(workspace.tasks.map(task => task.id));
  const seen = new Set();
  return trash.map(entry => {
    if (!isObject(entry) || !isObject(entry.task) ||
        !isoTimestamp(entry.deletedAt)) {
      throw new Error('Local Trash contains invalid recovery metadata.');
    }
    const task = entry.task;
    if (typeof task.id !== 'string' || seen.has(task.id) || active.has(task.id)) {
      throw new Error('Local Trash contains duplicate or active task IDs.');
    }
    seen.add(task.id);
    // Deleted tasks can retain a project ID after a backup import replaces
    // the active project list. Validate every task field without silently
    // reassigning such historical references to Inbox.
    const projects = workspace.projects.slice();
    if (task.projectId !== null && typeof task.projectId === 'string' &&
        !projects.some(project => project.id === task.projectId)) {
      projects.push({ id: task.projectId, name: 'Archived project' });
    }
    const version = task.description !== undefined && task.description !== '' ? 2 : 1;
    const validated = validateBackup({
      schema: version, projects, tasks: [{ ...task, ...(version === 2 ? {description: task.description} : {}) }]
    }).tasks[0];
    return { task: validated, deletedAt: entry.deletedAt };
  });
}

export function readLocalSnapshot(raw) {
  if (raw === null) return { workspace: EMPTY(), trash: [] };
  if (typeof raw !== 'string' ||
      new TextEncoder().encode(raw).length > MAX_LOCAL_BYTES) {
    throw new Error('Local workspace exceeds the 3 MiB storage limit.');
  }
  let stored;
  try { stored = JSON.parse(raw); }
  catch { throw new Error('Local workspace is not valid JSON.'); }
  // Legacy storage was exactly a portable schema-1 backup.
  if (!isObject(stored) || stored.format !== LOCAL_FORMAT) {
    return { workspace: validateBackupText(raw), trash: [] };
  }
  const workspace = validateBackup(stored.workspace);
  // This is not an export; keep a separate check of current workspace size.
  exportBackup(workspace);
  return { workspace, trash: checkedTrash(workspace, stored.trash) };
}

export function serializeLocalSnapshot(workspace, trash) {
  const version = workspace.schema === 2 || workspace.tasks.some(t => t.description !== undefined && t.description !== '') ? 2 : 1;
  const current = validateBackup({ ...workspace, schema: version, tasks: workspace.tasks.map(t =>
    version === 2 ? { ...t, description: t.description ?? '' } : t) });
  // Guarantee that active data remains exportable on its own.
  exportBackup(current);
  const checked = checkedTrash(current, trash);
  const raw = JSON.stringify({ format: LOCAL_FORMAT, workspace: current, trash: checked });
  if (new TextEncoder().encode(raw).length > MAX_LOCAL_BYTES) {
    throw new Error('Browser workspace including Trash exceeds 3 MiB; no data was saved.');
  }
  return raw;
}

export function moveToTrash(workspace, trash, deleteTask, id, deletedAt) {
  if (!isoTimestamp(deletedAt)) throw new Error('Invalid deletion time.');
  if (trash.length >= MAX_TRASH_RECORDS) {
    throw new Error('Local Trash is full. Restore tasks before deleting more.');
  }
  const task = deleteTask(workspace, id);
  trash.push({ task, deletedAt });
  return task;
}

export function restoreFromTrash(workspace, trash, undoTaskDelete, id) {
  const index = trash.findIndex(entry => entry.task.id === id);
  if (index < 0) throw new Error('Task is no longer in Trash.');
  const entry = trash[index];
  undoTaskDelete(workspace, entry.task);
  trash.splice(index, 1);
  return entry.task;
}
