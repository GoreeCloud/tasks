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

test('owner-inspired list-first controls are real and use GC UI semantic roles', () => {
  const css = readFileSync(new URL('./list-first.css', import.meta.url), 'utf8');
  for (const id of ['sidebar-add-task','toolbar-add-task','mobile-add-task','mobile-search',
    'mobile-browse','mobile-browse-dialog','mobile-browse-close','mobile-project-select']) {
    assert.ok(ids.includes(id), 'Missing functional task navigation control '+id);
    assert.ok(app.includes("'"+id+"'"), 'Missing browser control wiring '+id);
  }
  assert.match(html,/aria-controls="task-form" aria-expanded="false"/);
  assert.match(css,/--task-hairline:\s*var\(--gc-v1-color-divider\)/);
  assert.match(css,/\.mobile-bottom-nav/);
  assert.match(css,/prefers-reduced-motion|forced-colors/);
  assert.doesNotMatch(css,/#5145d9|#e04b39/i,'Do not copy non-GC UI reference brand colors');
});
