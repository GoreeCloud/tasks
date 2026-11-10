import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateBackup } from './backup.mjs';
import { parseProposedGraphText, validateProposedGraph } from './subtask-graph.mjs';

const raw = readFileSync(new URL('../fixtures/portable/schema4-proposed-synthetic.json', import.meta.url), 'utf8');
const base = () => JSON.parse(raw);
const mutate = fn => { const data = base(); fn(data); return data; };

test('proposed hierarchy validates offline and production importer still rejects schema 4', () => {
  const graph = parseProposedGraphText(raw);
  assert.equal(graph.tasks.length, 3);
  assert.equal(graph.depths.get('task-notes'), 1);
  assert.equal(graph.depths.get('task-empty-notes'), 2);
  assert.equal(graph.depths.get('task-grandchild'), 3);
  assert.equal(graph.tasks[0].createdAt, base().tasks[0].createdAt);
  assert.equal(graph.tasks[0].completedAt, base().tasks[0].completedAt);
  assert.deepEqual(graph.tasks[0].labels, ['Work', 'Design 🧭']);
  assert.throws(() => validateBackup(base()), /Unsupported/);
});
test('v4 graph rejects orphans, cycles, self-parenting and project mismatches', () => {
  const bad = [
    d => { d.tasks[1].parentId = 'orphan'; },
    d => { d.tasks[0].parentId = 'task-grandchild'; },
    d => { d.tasks[1].parentId = d.tasks[1].id; },
    d => { d.tasks[1].projectId = null; },
    d => { delete d.tasks[1].parentId; },
    d => { d.tasks[1].parentId = 11; },
    d => { d.tasks[1].parentId = '\uD800'; },
    d => { d.tasks.push({...d.tasks[1]}); },
    d => { d.tasks[0].labels = ['Work', 'Work']; },
  ];
  for (const change of bad) assert.throws(() => validateProposedGraph(mutate(change)));
});
test('v4 graph rejects >3 levels and more than 300 tasks in one project', () => {
  assert.throws(() => validateProposedGraph(mutate(d => {
    d.tasks.push({...d.tasks[2], id:'task-fourth',parentId:'task-grandchild'});
  })), /three levels/);
  assert.throws(() => validateProposedGraph(mutate(d => {
    for (let i = 0; i < 299; ++i) d.tasks.push({
      ...d.tasks[1], id:'extra-' + i, parentId:'task-notes'
    });
  })), /300/);
});
test('v4 preview is bounded and does not mutate caller input', () => {
  const data=base(), before=JSON.stringify(data);
  validateProposedGraph(data);
  assert.equal(JSON.stringify(data),before);
  assert.throws(()=>parseProposedGraphText(' '.repeat(2*1024*1024+1)),/too large/);
  assert.throws(()=>parseProposedGraphText('{'),/Invalid JSON/);
  assert.throws(()=>validateProposedGraph({...data,schema:3}),/schema 4/);
});
