import { EMPTY, localDate, newTask, selectTasks, STORAGE_KEY } from './model.mjs';
import { exportBackup, MAX_BACKUP_BYTES, validateBackupText } from './backup.mjs';

const $ = id => document.getElementById(id);
let state = EMPTY();
let lastSavedRaw = null;
let writeLocked = false;
let unreadableStore = false;
let view = 'inbox';
let search = '';
const views = {
  inbox: ['Inbox', 'A calm place to capture what matters and make progress.'],
  today: ['Today', 'Make room for your most important next steps.'],
  upcoming: ['Upcoming', 'See what is coming, one day at a time.'],
  priority: ['Priority', 'Keep high-impact work in sight.'],
  all: ['All tasks', 'Everything on your plate, in one thoughtful view.'],
  completed: ['Completed', 'A record of the progress you have made.']
};
function report(message) { $('status').textContent = message; }
function locked(message) {
  writeLocked = true;
  report(message);
  ['task-form', 'project-form'].forEach(id => {
    $(id).querySelectorAll('input, select, button').forEach(control => { control.disabled = true; });
  });
  $('new-project').disabled = true;
  $('mobile-new-project').disabled = true;
}
try {
  lastSavedRaw = localStorage.getItem(STORAGE_KEY);
  if (lastSavedRaw !== null) state = validateBackupText(lastSavedRaw);
} catch {
  unreadableStore = true;
  locked('Stored task data is unreadable. Editing and exporting are disabled to prevent a misleading empty backup; restore a valid backup to recover.');
}
function mutate(change) {
  if (writeLocked) return false;
  try {
    // Non-atomic stale-tab check: safe against ordinary sequential edits,
    // but concurrent tabs still require future transactional IndexedDB storage.
    if (localStorage.getItem(STORAGE_KEY) !== lastSavedRaw) {
      locked('Tasks changed in another tab. Reload before editing to avoid overwriting newer data.');
      return false;
    }
    const draft = structuredClone(state);
    change(draft);
    const raw = exportBackup(draft);
    localStorage.setItem(STORAGE_KEY, raw);
    lastSavedRaw = raw;
    state = draft;
    report('');
    return true;
  } catch (error) {
    report(error instanceof Error ? 'Save failed: ' + error.message : 'Could not save the task.');
    return false;
  }
}
function el(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = content;
  return element;
}
function makeButton(label, className, click) {
  const button = el('button', className, label);
  button.type = 'button';
  button.disabled = writeLocked;
  button.addEventListener('click', click);
  return button;
}
function render() {
  const today = localDate();
  const filtered = selectTasks(state.tasks, view, today, search);
  const meta = views[view] || (view.startsWith('project:') ?
    [state.projects.find(project => project.id === view.slice(8))?.name || 'Project', 'Your project tasks, all in one place.'] : views.inbox);
  $('page-title').textContent = meta[0];
  $('crumb').textContent = meta[0];
  $('page-description').textContent = meta[1];
  $('stat-open').textContent = String(state.tasks.filter(task => !task.completed).length);
  $('stat-today').textContent = String(state.tasks.filter(task => !task.completed && task.due && task.due <= today).length);
  $('stat-done').textContent = String(state.tasks.filter(task => task.completed).length);
  $('inbox-count').textContent = String(state.tasks.filter(task => !task.completed && !task.projectId).length);
  $('result-count').textContent = '(' + filtered.length + ')';
  document.querySelectorAll('[data-view]').forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('selected', active);
    if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  const projectNav = $('project-nav');
  projectNav.replaceChildren();
  const mobileProjects = $('mobile-project-select');
  mobileProjects.replaceChildren(new Option('Projects', ''));
  const projectSelect = $('task-project');
  const previousSelection = projectSelect.value;
  projectSelect.replaceChildren(new Option('Inbox', ''));
  for (const project of state.projects) {
    const nav = makeButton('◈  ' + project.name, 'nav-item project-nav', () => {
      view = 'project:' + project.id;
      render();
    });
    nav.disabled = false;
    nav.dataset.view = 'project:' + project.id;
    if (view === nav.dataset.view) nav.classList.add('selected');
    projectNav.append(nav);
    projectSelect.add(new Option(project.name, project.id));
    mobileProjects.add(new Option(project.name, project.id));
  }
  mobileProjects.value = view.startsWith('project:') ? view.slice(8) : '';
  projectSelect.value = view.startsWith('project:') ? view.slice(8) : previousSelection;
  const list = $('task-list');
  list.replaceChildren();
  $('empty').hidden = filtered.length !== 0;
  filtered.forEach(task => {
    const item = el('li', 'task-row' + (task.completed ? ' is-completed' : ''));
    const checkbox = el('input', 'task-checkbox');
    checkbox.type = 'checkbox';
    checkbox.checked = task.completed;
    checkbox.disabled = writeLocked;
    checkbox.setAttribute('aria-label', (task.completed ? 'Reopen ' : 'Complete ') + task.title);
    checkbox.addEventListener('change', () => {
      mutate(draft => {
        const current = draft.tasks.find(entry => entry.id === task.id);
        current.completed = checkbox.checked;
        current.completedAt = checkbox.checked ? new Date().toISOString() : null;
      });
      render();
    });
    const body = el('div', 'task-body');
    body.append(el('strong', 'task-name', task.title));
    const details = el('div', 'task-details');
    details.append(el('span', 'priority priority-' + task.priority, 'P' + task.priority));
    if (task.due) details.append(el('span', task.due < today && !task.completed ? 'due overdue' : 'due', task.due));
    const project = state.projects.find(entry => entry.id === task.projectId);
    if (project) details.append(el('span', 'project-pill', project.name));
    body.append(details);
    const edit = makeButton('Edit', 'row-button', () => {
      const changed = prompt('Edit task title', task.title);
      if (changed === null) return;
      const title = changed.trim();
      if (!title || title.length > 240) { report('Task title must be 1–240 characters.'); return; }
      mutate(draft => { draft.tasks.find(entry => entry.id === task.id).title = title; });
      render();
    });
    const remove = makeButton('Delete', 'row-button danger', () => {
      if (!confirm('Delete this task permanently? Export a backup first if needed.')) return;
      mutate(draft => { draft.tasks = draft.tasks.filter(entry => entry.id !== task.id); });
      render();
    });
    item.append(checkbox, body, edit, remove);
    list.append(item);
  });
}
$('task-form').addEventListener('submit', event => {
  event.preventDefault();
  try {
    const task = newTask($('task-title').value, $('task-project').value, $('task-date').value, $('task-priority').value);
    if (mutate(draft => { draft.tasks.push(task); })) {
      $('task-form').reset();
      $('task-title').focus();
    }
    render();
  } catch (error) { report(error.message); }
});
document.querySelectorAll('#primary-nav [data-view]').forEach(button => button.addEventListener('click', () => {
  view = button.dataset.view;
  render();
}));
$('search').addEventListener('input', event => { search = event.target.value; render(); });
const dialog = $('project-dialog');
$('new-project').addEventListener('click', () => dialog.showModal());
$('project-cancel').addEventListener('click', () => dialog.close());
$('mobile-new-project').addEventListener('click', () => $('new-project').click());
$('mobile-project-select').addEventListener('change', event => {
  if (event.target.value) { view = 'project:' + event.target.value; render(); }
});
$('project-form').addEventListener('submit', event => {
  event.preventDefault();
  const name = $('project-title').value.trim();
  if (!name || name.length > 100) { report('Project name must be 1–100 characters.'); return; }
  const project = { id: crypto.randomUUID(), name };
  if (mutate(draft => { draft.projects.push(project); })) {
    view = 'project:' + project.id;
    dialog.close();
    $('project-form').reset();
  }
  render();
});
$('theme-toggle').addEventListener('click', () => {
  const root = document.documentElement;
  const next = root.dataset.mode === 'dark' ? 'light' : 'dark';
  root.dataset.mode = next;
  try { localStorage.setItem('goreecloud.tasks.theme', next); }
  catch { report('Theme preference could not be saved.'); }
});
try {
  const saved = localStorage.getItem('goreecloud.tasks.theme');
  if (saved === 'light' || saved === 'dark') document.documentElement.dataset.mode = saved;
} catch { /* theme remains available for this session */ }
$('export-data').addEventListener('click', () => {
  if (unreadableStore) { report('Cannot export unreadable task data. Restore a valid backup first.'); return; }
  try {
    const data = exportBackup(state);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = el('a');
    link.href = url;
    link.download = 'goreecloud-tasks-' + localDate() + '.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    report('Backup exported. Verify the downloaded file before relying on it.');
  } catch (error) { report('Export failed: ' + error.message); }
});
$('import-data').addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;
  if (file.size > MAX_BACKUP_BYTES) { report('Backup exceeds the 2 MiB limit.'); return; }
  let candidate;
  try { candidate = validateBackupText(await file.text()); }
  catch (error) { report('Import rejected: ' + error.message); return; }
  const summary = candidate.tasks.length + ' task(s), ' + candidate.projects.length + ' project(s).';
  if (!confirm('Replace ALL browser-local GoreeCloud Tasks data with this backup (' + summary + ')? Export your current data first.')) return;
  try {
    if (localStorage.getItem(STORAGE_KEY) !== lastSavedRaw) {
      locked('Tasks changed while importing. Reload before restoring.');
      return;
    }
    const raw = exportBackup(candidate);
    localStorage.setItem(STORAGE_KEY, raw);
    lastSavedRaw = raw;
    state = candidate;
    writeLocked = false;
    unreadableStore = false;
    ['task-form', 'project-form'].forEach(id => $(id).querySelectorAll('input, select, button').forEach(control => { control.disabled = false; }));
    $('new-project').disabled = false;
    $('mobile-new-project').disabled = false;
    view = 'inbox';
    search = '';
    $('search').value = '';
    report('Backup restored locally (' + summary + '). Please verify your tasks.');
    render();
  } catch { report('Could not restore: browser storage is unavailable. Existing data was not changed.'); }
});
$('mobile-export').addEventListener('click', () => $('export-data').click());
$('mobile-import').addEventListener('click', () => $('import-data').click());
$('mobile-theme').addEventListener('click', () => $('theme-toggle').click());
window.addEventListener('storage', event => {
  if (event.key === STORAGE_KEY && event.newValue !== lastSavedRaw) {
    locked('This workspace changed in another tab. Reload before editing to avoid lost updates.');
    render();
  }
});
render();
