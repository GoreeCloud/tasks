import test from 'node:test';
import assert from 'node:assert/strict';
import { batchEditTasks, duplicateTask, EMPTY, deleteTask, editTask, hydrate, localDate, newTask, selectTasks, undoTaskDelete } from './model.mjs';
import { exportBackup, validateBackupText } from './backup.mjs';
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

test('overdue and next-seven-day views respect local calendar boundaries and priority', () => {
  const sample = [
    { ...newTask('Overdue', '', '2026-10-31', 1), id:'overdue' },
    { ...newTask('Today', '', '2026-11-01', 2), id:'today' },
    { ...newTask('End of week', '', '2026-11-07', 4), id:'end' },
    { ...newTask('Beyond week', '', '2026-11-08', 3), id:'beyond' },
    { ...newTask('Later', '', '2026-11-09', 1), id:'later' },
    { ...newTask('Undated', '', '', 1), id:'none' },
    { ...newTask('Finished', '', '2026-11-01', 1), id:'done', completed: true, completedAt:'2026-11-01T18:00:00Z' }
  ];
  assert.deepEqual(selectTasks(sample,'overdue','2026-11-01').map(t=>t.id), ['overdue']);
  assert.deepEqual(selectTasks(sample,'soon','2026-11-01').map(t=>t.id), ['today','end']);
  assert.deepEqual(selectTasks(sample,'soon','2026-11-01','', {priority:'2'}).map(t=>t.id), ['today']);
  assert.deepEqual(selectTasks(sample,'upcoming','2026-11-01','', {sort:'due'}).map(t=>t.id), ['end','beyond','later']);
  assert.deepEqual(selectTasks(sample,'all','2026-11-01','', {sort:'title'}).map(t=>t.id),
    ['beyond','end','later','overdue','today','none']);
  assert.deepEqual(selectTasks(sample,'all','2026-11-01','today').map(t=>t.id), ['today']);
  assert.equal(sample[0].id, 'overdue'); // filters/sorts are nonmutating
});

test('bulk edits preserve task identity, history, and schema-one backup portability', () => {
  const project = {id:'roadmap',name:'Roadmap'};
  const before = newTask('First', null, '2026-11-01', 4);
  const second = newTask('Second', null, '', 3);
  const workspace = {schema:1,projects:[project],tasks:[before,second]};
  const timestamp = '2026-11-01T19:00:00.000Z';
  assert.equal(batchEditTasks(workspace,[before.id,second.id],{completed:true,priority:1,projectId:'roadmap'},timestamp),2);
  assert.ok(workspace.tasks.every(t=>t.completed && t.completedAt===timestamp && t.priority===1 && t.projectId==='roadmap'));
  assert.deepEqual(workspace.tasks.map(t=>t.id),[before.id,second.id]);
  assert.equal(workspace.tasks[0].createdAt,before.createdAt);
  assert.deepEqual(validateBackupText(exportBackup(workspace)),workspace);
  batchEditTasks(workspace,[before.id],{completed:true},'2026-11-02T00:00:00Z');
  assert.equal(workspace.tasks[0].completedAt,timestamp); // repeat complete does not reset history
  batchEditTasks(workspace,[before.id],{completed:false,projectId:null});
  assert.equal(workspace.tasks[0].completedAt,null);
  assert.equal(workspace.tasks[0].projectId,null);
  assert.equal(workspace.tasks[1].completedAt,timestamp);
});

test('bulk edits reject stale IDs and invalid patches without partial mutation', () => {
  const one = newTask('One');
  const two = newTask('Two');
  const workspace = {schema:1,projects:[{id:'p',name:'Project'}],tasks:[one,two]};
  const original = structuredClone(workspace);
  const bad = [
    [[one.id,'missing'],{completed:true}],
    [[one.id,one.id],{priority:1}],
    [[one.id,two.id],{priority:0}],
    [[one.id,two.id],{projectId:'missing'}],
    [[one.id,two.id],{completed:'yes'}],
    [[one.id],{title:'unsupported'}],
    [[],{completed:true}],
    [[one.id],{}]
  ];
  for (const [ids,patch] of bad) {
    assert.throws(()=>batchEditTasks(workspace,ids,patch));
    assert.deepEqual(workspace,original);
  }
  assert.throws(()=>batchEditTasks(workspace,[one.id],{completed:true},'not-a-time'));
  assert.deepEqual(workspace,original);
});

test('task descriptions preserve Unicode and editing history', () => {
  const task = newTask('Plan',null,'',2,'Notes 🚀\nMore details');
  assert.equal(task.description,'Notes 🚀\nMore details');
  const edited = editTask(task,{title:'Updated',projectId:null,due:'',priority:1},[]);
  assert.equal(edited.description,task.description);
  assert.equal(editTask(edited,{title:'Updated',projectId:null,due:'',priority:1,description:''},[]).description,'');
  assert.throws(()=>newTask('Bad',null,'',4,'x'.repeat(2001)));
  assert.throws(()=>newTask('Bad',null,'',4,String.fromCharCode(0xD800)));
});

test('search matches plain-text notes in active, completed, and project views without losing view boundaries', () => {
  const notes = {...newTask('Public title', 'project-a', '2026-11-03', 2, 'Release audit 🧭\nLine two'), id:'n'};
  const completed = {...newTask('Closed ticket', null, '', 4, 'Release audit 🧭'), id:'c', completed:true, completedAt:'2026-11-01T16:00:00Z'};
  const unrelated = {...newTask('Other',null,'',4,'Different notes'),id:'u'};
  const list = [notes, completed, unrelated];
  const find=(view,query)=>selectTasks(list,view,'2026-11-01',query).map(t=>t.id);
  assert.deepEqual(find('all','  AUDIT  '),['n']);
  assert.deepEqual(find('all','🧭'),['n']);
  assert.deepEqual(find('completed','audit'),['c']);
  assert.deepEqual(find('inbox','audit'),[]);
  assert.deepEqual(find('project:project-a','audit'),['n']);
  assert.deepEqual(find('upcoming','audit'),['n']);
  assert.deepEqual(find('all','Public title'),['n']);
  assert.deepEqual(find('all','cannot-match'),[]);
});

test('duplicate completed schema-2 task creates a distinct open copy without historical timestamps', () => {
  const completed = {
    ...newTask('Ship 🚀', 'team', '2026-11-19', 2, 'Release checklist\n🧭'),
    id: 'original', completed: true, createdAt: '2026-10-20T10:20:30.123456Z',
    completedAt: '2026-11-01T15:44:20.56789Z'
  };
  const project = [{id:'team',name:'Team'}];
  const duplicated = duplicateTask(completed, project);
  assert.notEqual(duplicated.id, completed.id);
  assert.deepEqual(
    [duplicated.title,duplicated.projectId,duplicated.due,duplicated.priority,duplicated.description],
    [completed.title,completed.projectId,completed.due,completed.priority,completed.description]
  );
  assert.equal(duplicated.completed,false);
  assert.equal(duplicated.completedAt,null);
  assert.notEqual(duplicated.createdAt,completed.createdAt);
  assert.equal(exportBackup({schema:2,projects:project,tasks:[completed,duplicated]}).includes('Release checklist'),true);
  assert.throws(()=>duplicateTask(completed,[]),/project/);
  assert.throws(()=>duplicateTask(null,project),/Task/);
});
