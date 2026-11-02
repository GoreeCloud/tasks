import { isoTimestamp } from './backup.mjs';
import { validateProposedGraph } from './subtask-graph.mjs';
import { MAX_LOCAL_BYTES, MAX_TRASH_RECORDS } from './local-store.mjs';

function validatePlanSize(workspace, trash) {
  if (trash.length > MAX_TRASH_RECORDS ||
      new TextEncoder().encode(JSON.stringify({workspace,trash})).length > MAX_LOCAL_BYTES) {
    throw new Error('Proposed local Trash capacity exceeded; no changes applied.');
  }
}

function checkedGroupId(id) {
  if (typeof id !== 'string' || !/^[a-zA-Z0-9-]{1,128}$/.test(id)) {
    throw new Error('Invalid recovery group ID.');
  }
}

/** PREVIEW ONLY. Returns a new plan; no changes to a persisted workspace. */
export function planSubtreeTrash(workspace, trash, rootId, deletedAt, groupId) {
  validateProposedGraph(workspace);
  checkedGroupId(groupId);
  if (!isoTimestamp(deletedAt)) throw new Error('Invalid deletion timestamp.');
  if (!Array.isArray(trash) || trash.some(entry => entry.groupId === groupId)) {
    throw new Error('Recovery group already exists or Trash is invalid.');
  }
  const byId = new Map(workspace.tasks.map(task => [task.id,task]));
  if (!byId.has(rootId)) throw new Error('Root task no longer exists.');
  const children = new Map();
  for (const task of workspace.tasks) {
    if (task.parentId !== null) {
      if (!children.has(task.parentId)) children.set(task.parentId, []);
      children.get(task.parentId).push(task.id);
    }
  }
  const ids = new Set(), pending = [rootId];
  while (pending.length) {
    const id = pending.pop();
    ids.add(id);
    pending.push(...(children.get(id) || []));
  }
  if (trash.some(entry => ids.has(entry?.task?.id))) {
    throw new Error('A task ID conflicts with recoverable Trash.');
  }
  const groupSize = ids.size;
  const transferred = workspace.tasks.filter(task => ids.has(task.id));
  const nextWorkspace = {...workspace, tasks: workspace.tasks.filter(task => !ids.has(task.id))};
  const nextTrash = [...trash, ...transferred.map(task => ({
    task: structuredClone(task), deletedAt, groupId, groupRootId: rootId, groupSize
  }))];
  validateProposedGraph(nextWorkspace);
  validatePlanSize(nextWorkspace, nextTrash);
  return {workspace: nextWorkspace, trash: nextTrash, affectedIds: [...ids]};
}

/** Restores a full deletion group only when its parents and IDs are valid. */
export function planSubtreeRestore(workspace, trash, groupId) {
  validateProposedGraph(workspace);
  checkedGroupId(groupId);
  if (!Array.isArray(trash)) throw new Error('Trash is invalid.');
  const group = trash.filter(entry => entry.groupId === groupId);
  if (!group.length) throw new Error('Recovery group not found.');
  const [first] = group;
  if (!Number.isInteger(first.groupSize) || first.groupSize < 1 ||
      group.length !== first.groupSize || group.length > MAX_TRASH_RECORDS ||
      group.some(entry => entry.groupSize !== first.groupSize ||
        entry.groupRootId !== first.groupRootId ||
        !isoTimestamp(entry.deletedAt) || !entry.task ||
        !Object.hasOwn(entry.task,'parentId'))) {
    throw new Error('Incomplete or invalid recovery group.');
  }
  const ids = new Set(group.map(entry => entry.task.id));
  if (ids.size !== group.length || !ids.has(first.groupRootId)) {
    throw new Error('Recovery group has duplicate or missing roots.');
  }
  const active = new Set(workspace.tasks.map(task => task.id));
  if (group.some(entry => active.has(entry.task.id)) ||
      trash.some(entry => entry.groupId !== groupId && ids.has(entry?.task?.id))) {
    throw new Error('Recovery ID collision.');
  }
  const restored = group.map(entry => structuredClone(entry.task));
  const nextWorkspace = {...workspace, tasks: [...workspace.tasks, ...restored]};
  validateProposedGraph(nextWorkspace); // validates parent chains and projects together
  const nextTrash = trash.filter(entry => entry.groupId !== groupId);
  validatePlanSize(nextWorkspace, nextTrash);
  return {workspace: nextWorkspace, trash: nextTrash, restoredIds: [...ids]};
}
