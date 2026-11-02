import { isoTimestamp } from './backup.mjs';

// Preview-only integrity reference: never invoked by live Tasks.
function validateShape(m) {
  if (!m || typeof m !== 'object' || Array.isArray(m) ||
      !/^[A-Za-z0-9-]{1,128}$/.test(m.groupId ?? '') ||
      typeof m.groupRootId !== 'string' || !m.groupRootId ||
      !isoTimestamp(m.deletedAt) || !Array.isArray(m.memberIds) ||
      m.memberIds.length < 1 || m.memberIds.length > 1000 ||
      m.memberIds.some(id => typeof id !== 'string' || !id || id.length > 128) ||
      m.memberIds.some((id, i) => i > 0 && id <= m.memberIds[i-1]) ||
      !m.memberIds.includes(m.groupRootId)) {
    throw new Error('Invalid group manifest.');
  }
  return m;
}

export function verifySubtreeManifest(manifest, trash) {
  const m = validateShape(manifest);
  if (!Array.isArray(trash)) throw new Error('Invalid recoverable Trash.');
  const group = trash.filter(entry => entry?.groupId === m.groupId);
  if (group.length !== m.memberIds.length) throw new Error('Group manifest count mismatch.');
  const ids = group.map(entry => entry?.task?.id).sort();
  if (!ids.every((id, index) => id === m.memberIds[index])) {
    throw new Error('Group manifest membership mismatch.');
  }
  if (group.some(entry => entry.groupRootId !== m.groupRootId ||
      entry.deletedAt !== m.deletedAt || entry.groupSize !== m.memberIds.length)) {
    throw new Error('Group manifest metadata mismatch.');
  }
  return true;
}

export function createSubtreeManifest(trash, groupId) {
  if (!Array.isArray(trash)) throw new Error('Invalid Trash.');
  const rows = trash.filter(entry => entry?.groupId === groupId);
  if (!rows.length) throw new Error('Recovery group not found.');
  const first = rows[0];
  const manifest = { groupId, groupRootId: first.groupRootId,
    deletedAt: first.deletedAt,
    memberIds: rows.map(entry => entry?.task?.id).sort() };
  verifySubtreeManifest(manifest, trash);
  return structuredClone(manifest);
}
