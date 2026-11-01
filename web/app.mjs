import { EMPTY, deleteTask, editTask, localDate, newTask, selectTasks, STORAGE_KEY, undoTaskDelete } from './model.mjs';
import { exportBackup, MAX_BACKUP_BYTES, validateBackupText } from './backup.mjs';
import { moveToTrash, readLocalSnapshot, restoreFromTrash, serializeLocalSnapshot } from './local-store.mjs';

const $ = id => document.getElementById(id);
let state = EMPTY();
let lastSavedRaw = null;
let writeLocked = false;
let unreadableStore = false;
let view = 'inbox';
let search = '';
// Recoverable Trash is stored with active tasks in the same local snapshot.
const deletedTasks = [];
function showUndo() {
  const button = $('undo-task-delete');
  button.hidden = view === 'trash' || writeLocked || deletedTasks.length === 0;
  button.disabled = writeLocked || deletedTasks.length === 0;
}
const views = {
  inbox: ['Inbox', 'A calm place to capture what matters and make progress.'],
  today: ['Today', 'Make room for your most important next steps.'],
  upcoming: ['Upcoming', 'See what is coming, one day at a time.'],
  priority: ['Priority', 'Keep high-impact work in sight.'],
  all: ['All tasks', 'Everything on your plate, in one thoughtful view.'],
  completed: ['Completed', 'A record of the progress you have made.'],
  trash: ['Trash', 'Restore deleted tasks locally. Trash is not included in JSON exports.']
};
function report(message) { $('status').textContent = message; }
function locked(message) {
  writeLocked = true;
  report(message);
  ['task-form', 'project-form', 'edit-task-form'].forEach(id => {
    $(id).querySelectorAll('input, select, button[type="submit"]').forEach(control => { control.disabled = true; });
  });
  $('new-project').disabled = true;
  $('mobile-new-project').disabled = true;
  showUndo();
}
try {
  lastSavedRaw = localStorage.getItem(STORAGE_KEY);
  const loaded = readLocalSnapshot(lastSavedRaw);
  state = loaded.workspace;
  deletedTasks.push(...loaded.trash);
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
    const trashDraft = structuredClone(deletedTasks);
    change(draft, trashDraft);
    const raw = serializeLocalSnapshot(draft, trashDraft);
    localStorage.setItem(STORAGE_KEY, raw);
    lastSavedRaw = raw;
    state = draft;
    deletedTasks.splice(0, deletedTasks.length, ...trashDraft);
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
const taskEditor = $('edit-task-dialog');
let editingTaskId = null;
function openTaskEditor(task) {
  if (writeLocked) return;
  editingTaskId = task.id;
  $('edit-task-title').value = task.title;
  $('edit-task-priority').value = String(task.priority);
  $('edit-task-date').value = task.due || '';
  const projectSelect = $('edit-task-project');
  projectSelect.replaceChildren(new Option('Inbox', ''));
  for (const project of state.projects) projectSelect.add(new Option(project.name, project.id));
  projectSelect.value = task.projectId || '';
  $('edit-task-error').textContent = '';
  taskEditor.showModal();
  $('edit-task-title').focus();
}
function render() {
  const today = localDate();
  const filtered = view === 'trash'
    ? deletedTasks.filter(entry => !search.trim() || entry.task.title.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
    : selectTasks(state.tasks, view, today, search);
  const meta = views[view] || (view.startsWith('project:') ?
    [state.projects.find(project => project.id === view.slice(8))?.name || 'Project', 'Your project tasks, all in one place.'] : views.inbox);
  $('page-title').textContent = meta[0];
  $('crumb').textContent = meta[0];
  $('page-description').textContent = meta[1];
  $('tasks-heading').firstChild.textContent = view === 'trash' ? 'Deleted tasks ' : 'Your tasks ';
  $('task-form').hidden = view === 'trash';
  $('task-list').setAttribute('aria-label', view === 'trash' ? 'Deleted tasks' : 'Tasks');
  $('stat-open').textContent = String(state.tasks.filter(task => !task.completed).length);
  $('stat-today').textContent = String(state.tasks.filter(task => !task.completed && task.due && task.due <= today).length);
  $('stat-done').textContent = String(state.tasks.filter(task => task.completed).length);
  $('inbox-count').textContent = String(state.tasks.filter(task => !task.completed && !task.projectId).length);
  $('trash-count').textContent = String(deletedTasks.length);
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
  $('empty').querySelector('h3').textContent = view === 'trash' ? 'Trash is empty' : 'All clear here';
  $('empty').querySelector('p').textContent = view === 'trash'
    ? 'Deleted tasks stay on this browser until restored.'
    : 'Start with a small next step. Your future self will thank you.';
  filtered.forEach(record => {
    const task = view === 'trash' ? record.task : record;
    const item = el('li', 'task-row' + (task.completed ? ' is-completed' : ''));
    if (view === 'trash') {
      const body = el('div', 'task-body');
      body.append(el('strong', 'task-name', task.title));
      const details = el('div', 'task-details');
      details.append(el('span', 'priority priority-' + task.priority, 'P' + task.priority));
      details.append(el('span', '', 'Deleted ' + new Date(record.deletedAt).toLocaleDateString()));
      if (task.completed) details.append(el('span', '', 'Completed'));
      body.append(details);
      const restore = makeButton('Restore', 'row-button', () => restoreTrashedTask(task.id));
      restore.setAttribute('aria-label', 'Restore ' + task.title);
      item.append(body, restore);
      list.append(item);
      return;
    }
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
    const edit = makeButton('Edit', 'row-button', () => openTaskEditor(task));
    edit.setAttribute('aria-label', 'Edit ' + task.title);
    const remove = makeButton('Delete', 'row-button danger', () => {
      if (!confirm('Move this task to local Trash? You can restore it after reloading.')) return;
      if (mutate((draft, trash) => {
        moveToTrash(draft, trash, deleteTask, task.id, new Date().toISOString());
      })) {
        report('Task moved to local Trash. Restore it from the Trash view.');
      }
      render();
    });
    item.append(checkbox, body, edit, remove);
    list.append(item);
  });
  showUndo();
}
function restoreTrashedTask(id) {
  if (writeLocked) return;
  let restored;
  if (mutate((draft, trash) => {
    restored = restoreFromTrash(draft, trash, undoTaskDelete, id);
  })) report('Restored task: ' + restored.title);
  render();
}
$('undo-task-delete').addEventListener('click', () => {
  if (writeLocked || deletedTasks.length === 0) return;
  restoreTrashedTask(deletedTasks[deletedTasks.length - 1].task.id);
});
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
$('edit-task-cancel').addEventListener('click', () => taskEditor.close());
taskEditor.addEventListener('close', () => { editingTaskId = null; $('edit-task-error').textContent = ''; });
$('edit-task-form').addEventListener('submit', event => {
  event.preventDefault();
  if (writeLocked || !editingTaskId) {
    $('edit-task-error').textContent = 'Editing is unavailable. Reload before making changes.';
    return;
  }
  const id = editingTaskId;
  const updates = {
    title: $('edit-task-title').value,
    priority: $('edit-task-priority').value,
    due: $('edit-task-date').value,
    projectId: $('edit-task-project').value || null
  };
  const saved = mutate(draft => {
    const index = draft.tasks.findIndex(task => task.id === id);
    if (index < 0) throw new Error('Task no longer exists.');
    draft.tasks[index] = editTask(draft.tasks[index], updates, draft.projects);
  });
  if (!saved) {
    $('edit-task-error').textContent = $('status').textContent || 'Could not save changes.';
    return;
  }
  taskEditor.close();
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
  if (writeLocked) { report('This browser tab has stale task data. Reload before exporting a backup.'); return; }
  try {
    // Fail closed if another tab saved a newer snapshot before the storage
    // event was delivered. Otherwise export could misleadingly look current.
    if (localStorage.getItem(STORAGE_KEY) !== lastSavedRaw) {
      locked('Tasks changed in another tab. Reload before exporting a current backup.');
      return;
    }
    const data = exportBackup(state);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = el('a');
    link.href = url;
    link.download = 'goreecloud-tasks-' + localDate() + '.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    report('Backup exported (active tasks only; local Trash excluded). Verify the downloaded file.');
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
  if (!confirm('Replace active browser tasks and projects with this backup (' + summary + ')? Existing local Trash will be preserved; colliding IDs are rejected. Export current active data first.')) return;
  try {
    if (localStorage.getItem(STORAGE_KEY) !== lastSavedRaw) {
      locked('Tasks changed while importing. Reload before restoring.');
      return;
    }
    // Preserve durable Trash atomically with the imported active snapshot.
    // Any colliding IDs cause the entire import to fail closed.
    const raw = serializeLocalSnapshot(candidate, deletedTasks);
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
    $('edit-task-form').querySelectorAll('input, select, button[type="submit"]').forEach(control => { control.disabled = false; });
    report('Backup restored locally (' + summary + '). Existing local Trash was preserved.');
    render();
  } catch (error) { report('Import not saved: ' + error.message + ' Existing data was not changed.'); }
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
