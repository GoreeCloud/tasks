import { MAX_BACKUP_BYTES, validateBackup } from './backup.mjs';
import { validateProposedGraph } from './subtask-graph.mjs';

/** Read-only proposed v4 root conversion. Never used by live import/storage. */
export function previewLegacyAsRoots(source) {
  // Normalize with the current strict reader, not with a hand-rolled parser.
  const legacy = validateBackup(source);
  const candidate = {
    schema: 4,
    projects: legacy.projects,
    tasks: legacy.tasks.map(task => ({
      ...task,
      ...(legacy.schema < 2 ? { description: '' } : {}),
      ...(legacy.schema < 3 ? { labels: [] } : {}),
      parentId: null
    }))
  };
  if (new TextEncoder().encode(JSON.stringify(candidate)).length > MAX_BACKUP_BYTES) {
    throw new Error('Projected schema-4 backup exceeds the size limit.');
  }
  const validated = validateProposedGraph(candidate);
  return {schema: 4, projects: validated.projects, tasks: validated.tasks};
}
