import { isoTimestamp } from './backup.mjs';

// Preview-only integrity reference: never invoked by live Tasks.
// Hash serialized local task payloads; this detects corruption, not tampering
// by an adversary able to rewrite both the records and manifest.
async function payloadDigest(task) {
  const bytes = new TextEncoder().encode(JSON.stringify(task));
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2,'0')).join('');
}
function validateShape(m) {
  if (!m || typeof m !== 'object' || Array.isArray(m) ||
      !/^[A-Za-z0-9-]{1,128}$/.test(m.groupId ?? '') ||
      typeof m.groupRootId !== 'string' || !m.groupRootId ||
      !isoTimestamp(m.deletedAt) || !Array.isArray(m.memberIds) ||
      m.memberIds.length < 1 || m.memberIds.length > 1000 ||
      m.memberIds.some(id => typeof id !== 'string' || !id || id.length > 128) ||
      m.memberIds.some((id, i) => i > 0 && id <= m.memberIds[i-1]) ||
      !m.memberIds.includes(m.groupRootId) ||
      !Array.isArray(m.memberDigests) || m.memberDigests.length !== m.memberIds.length ||
      m.memberDigests.some(digest => typeof digest !== 'string' || !/^[a-f0-9]{64}$/.test(digest))) {
    throw new Error('Invalid group manifest.');
  }
  return m;
}

export async function verifySubtreeManifest(manifest, trash) {
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
  const lookup = new Map(group.map(entry => [entry.task.id, entry.task]));
  const actual = await Promise.all(m.memberIds.map(id => payloadDigest(lookup.get(id))));
  if (!actual.every((digest,i) => digest === m.memberDigests[i])) {
    throw new Error('Group manifest payload digest mismatch.');
  }
  return true;
}

export async function createSubtreeManifest(trash, groupId) {
  if (!Array.isArray(trash)) throw new Error('Invalid Trash.');
  const rows = trash.filter(entry => entry?.groupId === groupId);
  if (!rows.length) throw new Error('Recovery group not found.');
  const first = rows[0];
  const manifest = { groupId, groupRootId: first.groupRootId,
    deletedAt: first.deletedAt,
    memberIds: rows.map(entry => entry?.task?.id).sort() };
  const lookup = new Map(rows.map(entry => [entry.task.id,entry.task]));
  manifest.memberDigests = await Promise.all(manifest.memberIds.map(id => payloadDigest(lookup.get(id))));
  await verifySubtreeManifest(manifest, trash);
  return structuredClone(manifest);
}
