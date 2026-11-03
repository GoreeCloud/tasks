import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY, deleteTask, editTask, hydrate, localDate, newTask, selectTasks, undoTaskDelete } from './model.mjs';
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
test('invalid calendar dates are rejected', () => { assert.throws(() => newTask('Bad date', null, '2026-02-30')); assert.throws(() => newTask('Bad date', null, '2026-13-01')); assert.equal(newTask('Leap day', null, '2028-02-29').due, '2028-02-29'); });
test('date is local not UTC', () => { assert.equal(localDate(new Date(2026, 9, 31, 23, 50)), '2026-10-31'); });

test('Unicode scalar validation and native priority types', () => {
  const bad = String.fromCharCode(0xD800);
  assert.throws(() => newTask('bad ' + bad));
  assert.throws(() => newTask(null));
  assert.throws(() => newTask('valid', null, '', true));
  assert.throws(() => newTask('valid', null, '', 'bogus'));
  assert.throws(() => newTask('valid', null, 0));
  assert.equal(newTask('Review 🚀', null, '', '2').priority, 2);
  assert.equal(newTask('Review 🚀').title, 'Review 🚀');
});

test('web edit changes all editable fields while preserving task identity and history', () => {
  const original = { ...newTask('Original task', '', '2026-11-03', 4),
    completed: true, completedAt: '2026-11-04T09:00:00Z' };
  const projects = [{ id: 'project-alpha', name: 'Roadmap' }];
  const edited = editTask(original, {
    title: '  Review launch  ', projectId: 'project-alpha',
    due: '2026-11-10', priority: '1'
  }, projects);
  assert.notStrictEqual(edited, original);
  assert.deepEqual(
    { id: edited.id, completed: edited.completed, createdAt: edited.createdAt,
      completedAt: edited.completedAt },
    { id: original.id, completed: original.completed, createdAt: original.createdAt,
      completedAt: original.completedAt }
  );
  assert.equal(edited.title, 'Review launch');
  assert.equal(edited.projectId, 'project-alpha');
  assert.equal(edited.due, '2026-11-10');
  assert.equal(edited.priority, 1);
  assert.equal(original.title, 'Original task');
  const inbox = editTask(edited, {
    title: 'Inbox', projectId: '', due: '', priority: 4
  }, projects);
  assert.equal(inbox.projectId, null);
  assert.equal(inbox.due, '');
});

test('web edit refuses invalid titles, dates, priorities and missing projects', () => {
  const original = newTask('Valid');
  const fields = { title: 'Updated', projectId: null, due: '', priority: 2 };
  const cases = [
    { title: ' ' }, { title: 'x'.repeat(241) },
    { title: 'bad ' + String.fromCharCode(0xD800) },
    { due: '2026-02-30' }, { due: '2026-11-31' },
    { priority: 0 }, { priority: true }, { priority: 'not-a-priority' },
    { projectId: 'missing-project' }, { projectId: 42 }
  ];
  for (const bad of cases) {
    assert.throws(() => editTask(original, { ...fields, ...bad }, []));
    assert.equal(original.title, 'Valid');
  }
  assert.throws(() => editTask(null, fields, []));
  assert.throws(() => editTask(original, fields, null));
  assert.equal(newTask('Inbox', '').projectId, null);
});

test('deletion undo restores full task identity, project and historical completion', () => {
  const project = { id: 'p1', name: 'Roadmap' };
  const completed = {
    ...newTask('Review 🚀', 'p1', '2026-11-10', 1),
    completed: true, completedAt: '2026-11-10T19:20:21.123Z'
  };
  const other = newTask('Keep me');
  const draft = { schema: 1, projects: [project], tasks: [completed, other] };
  const original = structuredClone(draft);
  const deleted = deleteTask(draft, completed.id);
  assert.deepEqual(deleted, completed);
  assert.deepEqual(draft.tasks, [other]);
  undoTaskDelete(draft, deleted);
  assert.deepEqual(draft.tasks, [other, completed]);
  assert.deepEqual(deleted, original.tasks[0]);
  assert.equal(draft.tasks[1].completedAt, '2026-11-10T19:20:21.123Z');
  // Changes to the reinserted task cannot corrupt the retained undo snapshot.
  draft.tasks[1].title = 'Changed afterward';
  assert.equal(deleted.title, 'Review 🚀');
});

test('undo rejects duplicate IDs, missing projects and invalid workspace state', () => {
  const task = newTask('Private task', 'p', '', 4);
  const draft = { schema: 1, projects: [{ id: 'p', name: 'Workspace' }], tasks: [task] };
  assert.throws(() => deleteTask(draft, 'missing'));
  assert.throws(() => undoTaskDelete(draft, task));
  const deleted = deleteTask(draft, task.id);
  draft.projects = [];
  assert.throws(() => undoTaskDelete(draft, deleted));
  assert.deepEqual(draft.tasks, []);
  draft.projects = [{ id: 'p', name: 'Workspace' }];
  undoTaskDelete(draft, deleted);
  assert.equal(draft.tasks.length, 1);
  assert.throws(() => undoTaskDelete(null, deleted));
  assert.throws(() => undoTaskDelete(draft, null));
});


test('tomorrow view respects calendar rollovers and excludes overdue or completed tasks', () => {
  const tasks = [
    {...newTask('Tonight', null, '2026-12-31'), id:'today'},
    {...newTask('Next year', null, '2027-01-01'), id:'tomorrow'},
    {...newTask('Later', null, '2027-01-02'), id:'later'},
    {...newTask('Done tomorrow', null, '2027-01-01'), id:'done', completed:true}
  ];
  assert.deepEqual(selectTasks(tasks, 'tomorrow', '2026-12-31').map(x => x.id), ['tomorrow']);
  const leap = {...newTask('Leap day', null, '2028-02-29'), id:'leap'};
  assert.deepEqual(selectTasks([leap], 'tomorrow', '2028-02-28').map(x => x.id), ['leap']);
  assert.deepEqual(selectTasks([leap], 'tomorrow', '2028-02-29'), []);
});
