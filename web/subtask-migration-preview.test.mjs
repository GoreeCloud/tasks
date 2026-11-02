import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateBackup} from './backup.mjs';
import {validateProposedGraph} from './subtask-graph.mjs';
import {previewLegacyAsRoots} from './subtask-migration-preview.mjs';
const fixture=(name)=>JSON.parse(readFileSync(new URL('../fixtures/portable/'+name,import.meta.url),'utf8'));

test('schema 1/2/3 preserve all metadata as detached v4 roots in preview only',()=>{
  for(const name of ['schema1-synthetic.json','schema2-synthetic.json','schema3-synthetic.json']){
    const source=fixture(name),before=JSON.stringify(source);
    const normalized=validateBackup(source),projected=previewLegacyAsRoots(source);
    assert.equal(JSON.stringify(source),before);
    assert.equal(projected.schema,4);
    assert.deepEqual(projected.projects,normalized.projects);
    assert.equal(projected.tasks.length,normalized.tasks.length);
    assert.ok(projected.tasks.every(t=>t.parentId===null && Array.isArray(t.labels) && typeof t.description==='string'));
    for(let i=0;i<normalized.tasks.length;i++){
      const {parentId,description,labels,...task}=projected.tasks[i];
      const {description:oldDescription,labels:oldLabels,...old}=normalized.tasks[i];
      assert.deepEqual(task,old);
      assert.equal(description,oldDescription??'');
      assert.deepEqual(labels,oldLabels??[]);
    }
    assert.ok([...validateProposedGraph(projected).depths.values()].every(n=>n===1));
  }
});

test('legacy preview never flattens existing v4 or silently violates project limits',()=>{
  assert.throws(()=>previewLegacyAsRoots(fixture('schema4-proposed-synthetic.json')),/Unsupported/);
  const legacy=fixture('schema3-synthetic.json');
  legacy.tasks=Array.from({length:301},(_,i)=>({...legacy.tasks[0],id:'item-'+i}));
  assert.throws(()=>previewLegacyAsRoots(legacy),/300/);
});
