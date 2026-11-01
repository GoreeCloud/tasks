import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { deleteTask, EMPTY, newTask, undoTaskDelete } from './model.mjs';
import { exportBackup } from './backup.mjs';
import {
  LOCAL_FORMAT, MAX_TRASH_RECORDS, moveToTrash, readLocalSnapshot,
  restoreFromTrash, serializeLocalSnapshot
} from './local-store.mjs';

const fixture = () => JSON.parse(readFileSync(
  new URL('../fixtures/portable/schema1-synthetic.json', import.meta.url), 'utf8'
));

test('legacy schema-1 browser storage remains readable without overwriting it', () => {
  const old = exportBackup(fixture());
  const loaded = readLocalSnapshot(old);
  assert.deepEqual(loaded.workspace, fixture());
  assert.deepEqual(loaded.trash, []);
  const migrated = serializeLocalSnapshot(loaded.workspace, loaded.trash);
  assert.equal(JSON.parse(migrated).format, LOCAL_FORMAT);
  assert.deepEqual(readLocalSnapshot(migrated), loaded);
  assert.deepEqual(readLocalSnapshot(null), { workspace: EMPTY(), trash: [] });
});

test('single persisted snapshot retains deleted rows and exact timestamps after restart', () => {
  const workspace = fixture();
  const original = structuredClone(workspace.tasks[0]);
  const trash = [];
  const deleted = moveToTrash(
    workspace, trash, deleteTask, original.id, '2026-11-01T15:00:00Z'
  );
  assert.deepEqual(deleted, original);
  assert.equal(workspace.tasks.length, 2);
  const persisted = serializeLocalSnapshot(workspace, trash);
  const stored = JSON.parse(persisted);
  assert.equal(stored.format, LOCAL_FORMAT);
  assert.equal(stored.workspace.tasks.length, 2);
  assert.equal(stored.trash.length, 1);
  const reopened = readLocalSnapshot(persisted);
  assert.deepEqual(reopened.trash[0].task, original);
  assert.equal(reopened.trash[0].task.completedAt, '2026-11-01T01:23:45.654321Z');
  assert.deepEqual(
    JSON.parse(exportBackup(reopened.workspace)).tasks.map(t => t.id),
    ['task-pending', 'task-inbox']
  );
  const restored = restoreFromTrash(
    reopened.workspace, reopened.trash, undoTaskDelete, original.id
  );
  assert.deepEqual(restored, original);
  assert.deepEqual(reopened.trash, []);
  assert.deepEqual(reopened.workspace.tasks.at(-1), original);
  const afterReload = readLocalSnapshot(
    serializeLocalSnapshot(reopened.workspace, reopened.trash)
  );
  assert.deepEqual(afterReload.workspace.tasks.at(-1), original);
});

test('orphaned project links stay intact and recovery fails closed', () => {
  const source = fixture();
  const trash = [];
  moveToTrash(source, trash, deleteTask, 'task-completed', '2026-11-01T15:00:00Z');
  const replacement = { schema: 1, projects: [], tasks: [] };
  const restoredLocal = readLocalSnapshot(serializeLocalSnapshot(replacement, trash));
  assert.equal(restoredLocal.trash[0].task.projectId, 'project-alpha');
  assert.throws(() => restoreFromTrash(
    restoredLocal.workspace, restoredLocal.trash, undoTaskDelete, 'task-completed'
  ), /original project no longer exists/i);
  assert.equal(restoredLocal.trash.length, 1);
  assert.equal(restoredLocal.workspace.tasks.length, 0);
  restoredLocal.workspace.projects.push({ id: 'project-alpha', name: 'Roadmap' });
  restoreFromTrash(restoredLocal.workspace, restoredLocal.trash, undoTaskDelete, 'task-completed');
  assert.equal(restoredLocal.workspace.tasks[0].projectId, 'project-alpha');
});

test('conflicting active IDs abort import rather than discard recoverable history', () => {
  const workspace = fixture();
  const trash = [];
  moveToTrash(workspace, trash, deleteTask, 'task-inbox', '2026-11-01T15:00:00Z');
  const collide = fixture();
  assert.throws(() => serializeLocalSnapshot(collide, trash), /duplicate or active task IDs/);
  assert.equal(trash.length, 1);
  assert.equal(workspace.tasks.length, 2);
});

test('trash capacity never silently purges deleted records', () => {
  const workspace = fixture();
  const trash = Array.from({ length: MAX_TRASH_RECORDS }, (_, i) => ({
    task: {
      id: 'deleted-' + i, title: 'Saved ' + i, projectId: null,
      due: '', priority: 4, completed: false,
      createdAt: '2026-11-01T01:00:00Z', completedAt: null
    }, deletedAt: '2026-11-01T15:00:00Z'
  }));
  assert.throws(() => moveToTrash(
    workspace, trash, deleteTask, 'task-inbox', '2026-11-01T15:00:00Z'
  ), /Trash is full/);
  assert.equal(workspace.tasks.length, 3);
  assert.equal(trash.length, MAX_TRASH_RECORDS);
  assert.equal(readLocalSnapshot(serializeLocalSnapshot(workspace, trash)).trash.length, MAX_TRASH_RECORDS);
  assert.throws(() => serializeLocalSnapshot(workspace, [...trash, trash[0]]), /full/);
});

test('malformed local snapshots fail closed rather than return an empty workspace', () => {
  const workspace = fixture();
  const trash = [];
  moveToTrash(workspace, trash, deleteTask, 'task-completed', '2026-11-01T15:00:00Z');
  const stored = JSON.parse(serializeLocalSnapshot(workspace, trash));
  const corrupt = [
    '{', JSON.stringify({ format: LOCAL_FORMAT, workspace, trash: null }),
    JSON.stringify({ ...stored, trash: [stored.trash[0], stored.trash[0]] }),
    JSON.stringify({ ...stored, trash: [{ ...stored.trash[0], deletedAt: '2026-02-30T12:00:00Z' }] }),
    JSON.stringify({ ...stored, trash: [{ ...stored.trash[0], task: { ...stored.trash[0].task, priority: true } }] }),
    JSON.stringify({ ...stored, workspace: { ...stored.workspace, tasks: [{ ...stored.trash[0].task }] } }),
    JSON.stringify({ ...stored, workspace: { schema: 4, projects: [], tasks: [] } }),
    JSON.stringify({ ...stored, trash: [{ ...stored.trash[0], task: { ...stored.trash[0].task, completedAt: null } }] })
  ];
  for (const raw of corrupt) assert.throws(() => readLocalSnapshot(raw));
  const validated = readLocalSnapshot(JSON.stringify(stored));
  assert.equal(validated.trash[0].task.id, 'task-completed');
});

test('deletion or restore failure is reversible with the same local draft', () => {
  const workspace = fixture();
  const trash = [];
  assert.throws(() => moveToTrash(
    workspace, trash, deleteTask, 'does-not-exist', '2026-11-01T15:00:00Z'
  ));
  assert.equal(workspace.tasks.length, 3);
  assert.deepEqual(trash, []);
  assert.throws(() => restoreFromTrash(workspace, trash, undoTaskDelete, 'task-inbox'));
  assert.equal(workspace.tasks.length, 3);
});

test('schema-2 notes survive local Trash and restart', () => {
  const workspace = {schema:1,projects:[],tasks:[newTask('Memo',null,'',1,'Keep secret in local Trash')]};
  const local = serializeLocalSnapshot(workspace,[]);
  const parsed = readLocalSnapshot(local);
  assert.equal(parsed.workspace.schema,2);
  const trash=[];
  const original=parsed.workspace.tasks[0];
  moveToTrash(parsed.workspace,trash,deleteTask,original.id,'2026-11-01T15:00:00Z');
  const read=readLocalSnapshot(serializeLocalSnapshot(parsed.workspace,trash));
  assert.equal(read.trash[0].task.description,original.description);
  restoreFromTrash(read.workspace,read.trash,undoTaskDelete,original.id);
  assert.equal(read.workspace.tasks[0].description,original.description);
});

test('schema3 label arrays survive local Trash and restoration',()=>{
 const task=newTask('Tagged',null,'',2,'Notes',['Work','Design 🧭']);
 const workspace={schema:3,projects:[],tasks:[task]};
 const trash=[];
 moveToTrash(workspace,trash,deleteTask,task.id,'2026-11-01T15:00:00Z');
 const disk=readLocalSnapshot(serializeLocalSnapshot(workspace,trash));
 assert.deepEqual(disk.trash[0].task.labels,['Work','Design 🧭']);
 restoreFromTrash(disk.workspace,disk.trash,undoTaskDelete,task.id);
 assert.deepEqual(disk.workspace.tasks[0].labels,['Work','Design 🧭']);
 assert.equal(JSON.parse(exportBackup(disk.workspace)).schema,3);
});
