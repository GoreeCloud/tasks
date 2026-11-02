import { MAX_BACKUP_BYTES, validateBackup } from './backup.mjs';

/** PREVIEW ONLY: validates proposed v4 relationships without enabling imports. */
export function validateProposedGraph(snapshot) {
  if (!snapshot || snapshot.schema !== 4 || !Array.isArray(snapshot.tasks)) {
    throw new Error('Expected proposed schema 4.');
  }
  // Run the existing mature task/description/label/timestamp validator first.
  // Never permit the proposed schema through the production importer.
  const legacy = validateBackup({
    ...snapshot,
    schema: 3,
    tasks: snapshot.tasks.map(task => {
      if (!task || typeof task !== 'object' || Array.isArray(task) ||
          !Object.hasOwn(task, 'parentId')) throw new Error('Missing parentId.');
      const { parentId, ...rest } = task;
      if (parentId !== null &&
          (typeof parentId !== 'string' || parentId.length < 1 ||
           parentId.length > 128 || /[\u0000-\u001f\u007f]/u.test(parentId))) {
        throw new Error('Invalid parentId.');
      }
      return rest;
    })
  });
  const indexed = new Map(snapshot.tasks.map(task => [task.id, task]));
  const depths = new Map();
  const counts = new Map();
  for (const task of snapshot.tasks) {
    const key = task.projectId ?? null;
    const count = (counts.get(key) ?? 0) + 1;
    if (count > 300) throw new Error('Project exceeds 300 active tasks including subtasks.');
    counts.set(key, count);
    const chain = new Set();
    let id = task.id, depth = 0;
    while (id !== null) {
      if (chain.has(id)) throw new Error('Subtask parent cycle.');
      chain.add(id);
      depth += 1;
      if (depth > 3) throw new Error('Subtask nesting exceeds three levels.');
      const parent = indexed.get(id);
      if (!parent) throw new Error('Missing parent task.');
      if (parent.projectId !== task.projectId) throw new Error('Cross-project subtask relationship.');
      id = parent.parentId;
    }
    depths.set(task.id, depth);
  }
  return {
    schema: 4, projects: legacy.projects,
    tasks: legacy.tasks.map(task => ({
      ...task, parentId: indexed.get(task.id).parentId
    })),
    depths
  };
}

export function parseProposedGraphText(raw) {
  if (typeof raw !== 'string' ||
      new TextEncoder().encode(raw).length > MAX_BACKUP_BYTES) {
    throw new Error('Proposed backup is too large.');
  }
  let data;
  try { data = JSON.parse(raw); }
  catch { throw new Error('Invalid JSON.'); }
  return validateProposedGraph(data);
}
