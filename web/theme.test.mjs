import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { createHash } from 'node:crypto';

const script = readFileSync(new URL('./theme-bootstrap.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const styles = readFileSync(new URL('./theme-overrides.css', import.meta.url), 'utf8');
const snapshot = readFileSync(new URL('./gc-app-semantic.css', import.meta.url));

function boot(values = {}, fail = false) {
  const saved = new Map(Object.entries(values));
  const root = { dataset: {}, style: {} };
  const store = {
    getItem(key) { if (fail) throw new Error('Storage disabled'); return saved.get(key) ?? null; },
    setItem(key, value) { if (fail) throw new Error('Storage disabled'); saved.set(key, value); }
  };
  const window = { get localStorage() { if (fail) throw new Error('Storage disabled'); return store; } };
  runInNewContext(script, { document: { documentElement: root }, window });
  return { root, saved, controller: window.GoreeTasksTheme };
}
test('fresh profile starts light with neutral accent regardless of OS preference', () => {
  const { root } = boot();
  assert.deepEqual(root.dataset, { theme: 'light', mode: 'light', gcAccent: 'neutral' });
  assert.equal(root.style.colorScheme, 'light');
});
test('existing saved dark choice survives migration and neutral remains opt-in-free', () => {
  const { root } = boot({ 'goreecloud.tasks.theme': 'dark' });
  assert.equal(root.dataset.mode, 'dark');
  assert.equal(root.dataset.gcAccent, 'neutral');
});
test('explicit saved settings take precedence over legacy and survive reload', () => {
  const old = { 'goreecloud.tasks.theme': 'dark' };
  const session = boot(old);
  assert.equal(session.controller.save('light', 'lagoon'), true);
  assert.equal(session.root.dataset.mode, 'light');
  assert.equal(session.root.dataset.gcAccent, 'lagoon');
  assert.equal(session.saved.get('goreecloud.tasks.ui.v1'), JSON.stringify({mode: 'light', accent: 'lagoon'}));
  const next = boot(Object.fromEntries(session.saved));
  assert.equal(next.root.dataset.gcAccent, 'lagoon');
  assert.equal(next.root.dataset.mode, 'light');
  assert.equal(next.saved.get('goreecloud.tasks.theme'), 'dark');
});
test('invalid and unavailable preferences safely default without changing task storage', () => {
  const invalid = boot({ 'goreecloud.tasks.appearance': 'auto', 'goreecloud.tasks.accent': 'script',
    'goreecloud.tasks.local.v1': 'preserve exactly' });
  assert.equal(invalid.root.dataset.mode, 'light');
  assert.equal(invalid.root.dataset.gcAccent, 'neutral');
  assert.equal(invalid.controller.save('untrusted', 'untrusted'), true);
  assert.equal(invalid.root.dataset.mode, 'light');
  assert.equal(invalid.root.dataset.gcAccent, 'neutral');
  assert.equal(invalid.saved.get('goreecloud.tasks.local.v1'), 'preserve exactly');
  const blocked = boot({}, true);
  assert.equal(blocked.root.dataset.mode, 'light');
  assert.equal(blocked.controller.save('dark', 'moss'), false);
  assert.equal(blocked.root.dataset.mode, 'dark');
});
test('GC UI snapshot is pinned, early-loading, and semantic role mapped', () => {
  assert.equal(createHash('sha256').update(snapshot).digest('hex'),
    'e3885c2df30fa02ad98c915d8be44d27f0d45387d4c44742a41b30dfa237cede');
  assert.ok(html.indexOf('theme-bootstrap.js') < html.indexOf('gc-app-semantic.css'));
  assert.ok(html.indexOf('gc-app-semantic.css') < html.indexOf('style.css'));
  for (const id of ['appearance-dialog', 'appearance-mode', 'appearance-accent',
    'appearance-form', 'appearance-cancel']) assert.match(html, new RegExp('id="' + id + '"'));
  assert.match(styles, /--gc-brand:var\(--gc-v1-color-primary\)/);
  assert.doesNotMatch(styles, /#5145d9/i);
});
