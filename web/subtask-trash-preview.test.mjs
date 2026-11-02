import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateProposedGraph } from './subtask-graph.mjs';
import { planSubtreeTrash, planSubtreeRestore } from './subtask-trash-preview.mjs';

const fixture = () => JSON.parse(readFileSync(
  new URL('../fixtures/portable/schema4-proposed-synthetic.json',import.meta.url),'utf8'
));
const date = '2026-11-02T14:00:00Z';

test('isolated proposal deletes and restores a complete subtree with exact metadata',()=>{
  const original=fixture(), before=JSON.stringify(original);
  const trashPlan=planSubtreeTrash(original,[],'task-notes',date,'group-1');
  assert.equal(JSON.stringify(original),before);
  assert.equal(trashPlan.workspace.tasks.length,0);
  assert.deepEqual(trashPlan.affectedIds.sort(),original.tasks.map(t=>t.id).sort());
  assert.ok(trashPlan.trash.every(entry=>entry.groupSize===3 &&
    entry.deletedAt===date && entry.groupRootId==='task-notes'));
  const restored=planSubtreeRestore(trashPlan.workspace,trashPlan.trash,'group-1');
  assert.deepEqual(restored.workspace,original);
  assert.deepEqual(restored.trash,[]);
  assert.deepEqual(validateProposedGraph(restored.workspace).depths.get('task-grandchild'),3);
  assert.equal(restored.workspace.tasks[0].completedAt, original.tasks[0].completedAt);
});

test('isolated proposal deletes only child descendants and can recover beside parent',()=>{
  const original=fixture();
  const plan=planSubtreeTrash(original,[],'task-empty-notes',date,'child-1');
  assert.deepEqual(plan.workspace.tasks.map(t=>t.id),['task-notes']);
  assert.equal(plan.trash.length,2);
  const restored=planSubtreeRestore(plan.workspace,plan.trash,'child-1');
  assert.deepEqual(new Set(restored.workspace.tasks.map(t=>t.id)),
    new Set(original.tasks.map(t=>t.id)));
});

test('restoring incomplete group, missing parent, cross-project parent or ID collision fails without mutation',()=>{
  const original=fixture();
  const moved=planSubtreeTrash(original,[],'task-empty-notes',date,'child-1');
  const fail=(workspace,trash)=> {
    const before=JSON.stringify({workspace,trash});
    assert.throws(()=>planSubtreeRestore(workspace,trash,'child-1'));
    assert.equal(JSON.stringify({workspace,trash}),before);
  };
  fail(moved.workspace,moved.trash.slice(0,1));
  fail({...moved.workspace,tasks:[]},moved.trash); // original parent missing
  const collision={...moved.workspace,tasks:[...moved.workspace.tasks,
    {...original.tasks[1],id:'task-grandchild',parentId:'task-notes'}]};
  fail(collision,moved.trash);
  const wrongProject=moved.trash.map(entry=>({
    ...entry,task:{...entry.task,projectId:null}
  }));
  fail(moved.workspace,wrongProject);
  const duplicated=[...moved.trash, {...moved.trash[0],groupId:'unrelated'}];
  fail(moved.workspace,duplicated);
});

test('invalid or reused group IDs, capacity, tampered graph and stale IDs abort deletion',()=>{
  const original=fixture(), before=JSON.stringify(original);
  const fail=(w,t,r,when,g)=>assert.throws(()=>planSubtreeTrash(w,t,r,when,g));
  fail(original,[],'unknown',date,'new');
  fail(original,[],'task-notes',date,'');
  fail(original,[],'task-notes','invalid','new');
  fail(original,[{groupId:'new'}],'task-notes',date,'new');
  fail(original,[{task:{id:'task-grandchild'}}],'task-notes',date,'new');
  fail(original,Array.from({length:1000},(_,i)=>({groupId:'old-'+i})),
    'task-notes',date,'new');
  assert.equal(JSON.stringify(original),before);
});
