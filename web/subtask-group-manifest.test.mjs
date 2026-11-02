import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { planSubtreeTrash } from './subtask-trash-preview.mjs';
import { createSubtreeManifest, verifySubtreeManifest } from './subtask-group-manifest.mjs';
const fixture=()=>JSON.parse(readFileSync(new URL('../fixtures/portable/schema4-proposed-synthetic.json',import.meta.url),'utf8'));
const plan=()=>planSubtreeTrash(fixture(),[],'task-notes','2026-11-02T14:00:00Z','g-1');
test('manifest includes full three-level deleted subtree without modifying its records',async()=>{
 const p=plan(),before=JSON.stringify(p.trash),m=await createSubtreeManifest(p.trash,'g-1');
 assert.deepEqual(m.memberIds,['task-empty-notes','task-grandchild','task-notes']);
 assert.equal(await verifySubtreeManifest(m,p.trash),true);
 assert.equal(JSON.stringify(p.trash),before);
});
test('forged surviving group sizes cannot hide a missing grandchild',async()=>{
 const p=plan(),m=await createSubtreeManifest(p.trash,'g-1');
 const incomplete=structuredClone(p.trash).filter(e=>e.task.id!=='task-grandchild');
 for(const e of incomplete)e.groupSize=2;
 await assert.rejects(verifySubtreeManifest(m,incomplete),/mismatch/);
 assert.equal(await verifySubtreeManifest(m,p.trash),true);
});
test('rejects shuffled, duplicate, substituted and conflicting group manifests',async()=>{
 const p=plan(),m=await createSubtreeManifest(p.trash,'g-1');
 for(const bad of [
  {...m,memberIds:[...m.memberIds].reverse()},
  {...m,memberIds:['task-empty-notes','task-empty-notes','task-notes']},
  {...m,memberIds:m.memberIds.slice(1)},
  {...m,groupRootId:'unrelated'},
  {...m,deletedAt:'not-a-date'}
 ]) await assert.rejects(verifySubtreeManifest(bad,p.trash));
 const changed=structuredClone(p.trash);changed[0].task.id='unrelated';
 await assert.rejects(verifySubtreeManifest(m,changed),/mismatch/);
});

test('manifests detect altered notes with unchanged IDs and group metadata',async()=>{
 const p=plan(),m=await createSubtreeManifest(p.trash,'g-1');
 const changed=structuredClone(p.trash);
 changed[0].task.description='Altered recovery content';
 await assert.rejects(verifySubtreeManifest(m,changed),/digest mismatch/);
 assert.equal(await verifySubtreeManifest(m,p.trash),true);
});
