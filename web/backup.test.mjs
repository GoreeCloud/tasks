import assert from 'node:assert/strict';
import test from 'node:test';
import { exportBackup, validateBackup, validateBackupText, validDate } from './backup.mjs';

const valid = () => ({ schema: 1, projects: [{ id: 'p', name: ' Home ' }], tasks: [
  { id: 't', title: ' Task ', projectId: 'p', priority: 1, due: '2028-02-29',
    completed: false, createdAt: '2026-10-31T21:00:00Z', completedAt: null }
] });

test('strict lossless backup roundtrip except whitespace trimming', () => {
  const snapshot = validateBackupText(exportBackup(valid()));
  assert.equal(snapshot.projects[0].name, 'Home');
  assert.equal(snapshot.tasks[0].title, 'Task');
  assert.equal(snapshot.tasks[0].due, '2028-02-29');
});
test('rejects malformed, wrong-version, and excessive JSON', () => {
  assert.throws(() => validateBackupText('not json'));
  assert.throws(() => validateBackupText(' '.repeat(2 * 1024 * 1024 + 1)));
  assert.throws(() => validateBackup({ ...valid(), schema: 2 }));
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
