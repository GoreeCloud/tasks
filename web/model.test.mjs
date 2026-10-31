import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY, hydrate, localDate, newTask, selectTasks } from './model.mjs';
test('bad persistence recovers safely', () => { assert.deepEqual(hydrate('{'), EMPTY()); assert.deepEqual(hydrate('{"schema":2}'), EMPTY()); });
test('title and priority validation', () => { assert.throws(() => newTask('  ')); assert.throws(() => newTask('ok', null, '', 0)); assert.equal(newTask('  Plan  ').title, 'Plan'); });
test('inbox, project, today, completed and priority filtering', () => {
  const a={...newTask('Inbox'), id:'a', due:'2026-10-31', priority:1};
  const b={...newTask('Project', 'p'), id:'b', due:'2026-11-02', priority:4};
  const c={...newTask('Done'), id:'c', completed:true};
  assert.deepEqual(selectTasks([a,b,c],'inbox','2026-10-31').map(x=>x.id),['a']);
  assert.deepEqual(selectTasks([a,b,c],'today','2026-10-31').map(x=>x.id),['a']);
  assert.deepEqual(selectTasks([a,b,c],'upcoming','2026-10-31').map(x=>x.id),['b']);
  assert.deepEqual(selectTasks([a,b,c],'project:p','2026-10-31').map(x=>x.id),['b']);
  assert.deepEqual(selectTasks([a,b,c],'completed','2026-10-31').map(x=>x.id),['c']);
  assert.deepEqual(selectTasks([a,b,c],'priority','2026-10-31').map(x=>x.id),['a']);
});
test('date is local not UTC', () => { assert.equal(localDate(new Date(2026, 9, 31, 23, 50)), '2026-10-31'); });
