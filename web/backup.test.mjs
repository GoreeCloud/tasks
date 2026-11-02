import assert from 'node:assert/strict';
import test from 'node:test';
import { exportBackup, isoTimestamp, validateBackup, validateBackupText, validDate } from './backup.mjs';
import { readFileSync } from 'node:fs';
import { editTask, newTask } from './model.mjs';

const valid = () => ({ schema: 1, projects: [{ id: 'p', name: ' Home ' }], tasks: [
  { id: 't', title: ' Task ', projectId: 'p', priority: 1, due: '2028-02-29',
    completed: false, createdAt: '2026-10-31T21:00:00Z', completedAt: null }
] });

test('strict timestamp contract rejects normalized or nonportable times', () => {
  const matrix = JSON.parse(readFileSync(new URL('../fixtures/portable/timestamp-contract.json', import.meta.url), 'utf8'));
  for (const timestamp of matrix.valid) {
    assert.equal(isoTimestamp(timestamp), true, 'Expected accepted: ' + timestamp);
    const snapshot = valid();
    snapshot.tasks[0].createdAt = timestamp;
    assert.equal(validateBackup(snapshot).tasks[0].createdAt, timestamp);
  }
  for (const timestamp of matrix.invalid) {
    assert.equal(isoTimestamp(timestamp), false, 'Unexpected acceptance: ' + timestamp);
    const snapshot = valid();
    snapshot.tasks[0].createdAt = timestamp;
    assert.throws(() => validateBackup(snapshot), 'Invalid backup timestamp: ' + timestamp);
  }
});

test('shared schema-1 synthetic fixture round-trips with full field precision', () => {
  const raw = readFileSync(new URL('../fixtures/portable/schema1-synthetic.json', import.meta.url), 'utf8');
  const original = JSON.parse(raw);
  const accepted = validateBackupText(raw);
  assert.equal(accepted.projects.length, 2);
  assert.equal(accepted.tasks.length, 3);
  assert.deepEqual(accepted, original);
  assert.deepEqual(validateBackupText(exportBackup(accepted)), original);
  assert.equal(accepted.tasks[0].completedAt, '2026-11-01T01:23:45.654321Z');
  assert.equal(accepted.tasks[0].createdAt, '2026-10-31T20:15:42.123456-05:00');
  for (const invalid of [
    { ...original, projects: [] },
    { ...original, tasks: [{ ...original.tasks[0], completedAt: null }] },
    { ...original, tasks: [{ ...original.tasks[0], priority: true }] },
    { ...original, tasks: [{ ...original.tasks[0], due: '2026-02-30' }] }
  ]) assert.throws(() => validateBackup(invalid));
});

test('edited task retains completion metadata through portable backup roundtrip', () => {
  const task = {
    ...newTask('Original', null, '2026-11-03', 4),
    completed: true, completedAt: '2026-11-04T09:10:11.123Z'
  };
  const projects = [{ id: 'p', name: 'Delivery' }];
  const edited = editTask(task, {
    title: 'Shipped', projectId: 'p', due: '2026-11-20', priority: '1'
  }, projects);
  const restored = validateBackupText(exportBackup({ schema: 1, projects, tasks: [edited] }));
  assert.deepEqual(restored.tasks[0], edited);
  assert.equal(restored.tasks[0].completedAt, task.completedAt);
  assert.equal(restored.tasks[0].createdAt, task.createdAt);
});

test('strict lossless backup roundtrip except whitespace trimming', () => {
  const snapshot = validateBackupText(exportBackup(valid()));
  assert.equal(snapshot.projects[0].name, 'Home');
  assert.equal(snapshot.tasks[0].title, 'Task');
  assert.equal(snapshot.tasks[0].due, '2028-02-29');
});
test('rejects malformed, wrong-version, and excessive JSON', () => {
  assert.throws(() => validateBackupText('not json'));
  assert.throws(() => validateBackupText(' '.repeat(2 * 1024 * 1024 + 1)));
  assert.throws(() => validateBackup({ ...valid(), schema: 4 }));
  assert.throws(() => validateBackup({ ...valid(), projects: [] }));
});
test('rejects invalid due dates, reference collisions and unknown projects', () => {
  assert.equal(validDate('2026-02-30'), false);
  assert.equal(validDate('2028-02-29'), true);
  const input = valid();
  input.tasks[0].due = '2026-02-30';
  assert.throws(() => validateBackup(input));
  input.tasks[0].due = '';
  input.tasks.push({ ...input.tasks[0] });
  assert.throws(() => validateBackup(input));
  input.tasks.pop();
  input.tasks[0].projectId = 'missing';
  assert.throws(() => validateBackup(input));
});
test('rejects malformed completion, titles and dates without discarding entries', () => {
  const input = valid();
  input.tasks[0].completed = true;
  assert.throws(() => validateBackup(input));
  input.tasks[0].completedAt = '2026-10-31T21:04:00Z';
  assert.equal(validateBackup(input).tasks[0].completed, true);
  input.tasks[0].title = ' ';
  assert.throws(() => validateBackup(input));
});
test('ignores unknown properties on validated records', () => {
  const input = valid();
  input.tasks[0].secret = 'not-exported';
  input.projects[0].extra = '<script>';
  const safe = validateBackup(input);
  assert.equal(safe.tasks[0].secret, undefined);
  assert.equal(safe.projects[0].extra, undefined);
});

test('preserves emoji but refuses unpaired Unicode in backups', () => {
  const input = valid();
  input.tasks[0].title = 'Plan 🚀';
  input.projects[0].name = 'Projects 🎯';
  assert.equal(validateBackup(input).tasks[0].title, 'Plan 🚀');
  const invalid = String.fromCharCode(0xD800);
  input.tasks[0].title = 'bad ' + invalid;
  assert.throws(() => validateBackup(input));
  input.tasks[0].title = 'valid';
  input.projects[0].name = 'bad ' + invalid;
  assert.throws(() => validateBackup(input));
});

test('schema-2 descriptions round-trip, and schema-1 cannot silently discard notes', () => {
  const task = newTask('Review',null,'',2,'Nested line\nPrivacy note 📋');
  const snapshot = {schema:1,projects:[],tasks:[task]};
  assert.throws(()=>validateBackup(snapshot),/schema 2/);
  const encoded = JSON.parse(exportBackup(snapshot));
  assert.equal(encoded.schema,2);
  assert.equal(encoded.tasks[0].description,task.description);
  assert.equal(validateBackupText(JSON.stringify(encoded)).tasks[0].description,task.description);
  assert.throws(()=>validateBackup({...encoded,tasks:[{...task,description:23}]}));
  assert.throws(()=>validateBackup({...encoded,tasks:[{...task,description:'x'.repeat(2001)}]}));
  assert.equal(JSON.parse(exportBackup({schema:1,projects:[],tasks:[newTask('Old')]})).schema,1);
});

test('shared schema-2 synthetic fixture round-trips with multiline Unicode descriptions', () => {
  const fixture = JSON.parse(readFileSync(new URL('../fixtures/portable/schema2-synthetic.json',import.meta.url),'utf8'));
  assert.deepEqual(validateBackupText(exportBackup(fixture)),fixture);
  assert.equal(fixture.tasks[0].description,'Check accessibility 🧭\nFollow up on copy edits.');
  assert.throws(()=>validateBackup({...fixture,tasks:[{...fixture.tasks[0],description:'🧭'.repeat(1001)}]}));
});

test('shared schema3 labels round-trip and reject legacy silent downgrade',()=>{
  const fixture=JSON.parse(readFileSync(new URL('../fixtures/portable/schema3-synthetic.json',import.meta.url),'utf8'));
  assert.deepEqual(validateBackupText(exportBackup(fixture)),fixture);
  assert.throws(()=>validateBackup({...fixture,schema:2}),/schema 3/);
  const corrupt={...fixture,tasks:[{...fixture.tasks[0],labels:['Work','Work']},fixture.tasks[1]]};
  assert.throws(()=>validateBackup(corrupt),/unique/);
  const tooMany={...fixture,tasks:[{...fixture.tasks[0],labels:Array(9).fill('X')},fixture.tasks[1]]};
  assert.throws(()=>validateBackup(tooMany),/8 labels/);
});

test('unsupported proposed schema-4 hierarchy is rejected rather than losing parent links',()=>{
 const data=readFileSync(new URL('../fixtures/portable/schema4-proposed-synthetic.json',import.meta.url),'utf8');
 assert.throws(()=>validateBackupText(data),/Unsupported/);
});
