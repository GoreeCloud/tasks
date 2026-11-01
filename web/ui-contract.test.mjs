import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const app = readFileSync(new URL('./app.mjs', import.meta.url), 'utf8');
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);

test('browser app references only unique, existing static control IDs', () => {
  assert.equal(new Set(ids).size, ids.length, 'Duplicate HTML element IDs');
  const referenced = new Set([...app.matchAll(/\$\('([a-z][a-z0-9-]*)'\)/g)].map(match => match[1]));
  for (const id of referenced) assert.ok(ids.includes(id), 'Missing static control: ' + id);
});

test('bulk actions, filter labels and keyboard skip-link are declared', () => {
  for (const id of ['select-visible', 'bulk-toolbar', 'bulk-complete', 'bulk-reopen',
    'bulk-priority', 'bulk-project', 'bulk-trash', 'bulk-clear', 'filter-priority',
    'sort-tasks', 'stat-rate']) assert.ok(ids.includes(id), 'Missing ' + id);
  assert.match(html, /href="#main-content">Skip to tasks<\/a>/);
  assert.match(html, /aria-label="Bulk task actions"/);
  assert.match(html, /data-view="soon"/);
  assert.match(html, /data-view="overdue"/);
  assert.match(html, /aria-live="polite"/);
});
