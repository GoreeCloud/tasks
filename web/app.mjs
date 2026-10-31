import { EMPTY, hydrate, localDate, newTask, selectTasks, STORAGE_KEY } from './model.mjs';
const $ = id => document.getElementById(id);
let state = hydrate(localStorage.getItem(STORAGE_KEY));
let view = 'inbox';
let search = '';
const views = { inbox:['Inbox','A calm place to capture what matters and make progress.'], today:['Today','Make room for your most important next steps.'], upcoming:['Upcoming','See what is coming, one day at a time.'], priority:['Priority','Keep high-impact work in sight.'], all:['All tasks','Everything on your plate, in one thoughtful view.'], completed:['Completed','A record of the progress you have made.'] };
function persist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); $('status').textContent = ''; return true; }
  catch { $('status').textContent = 'Could not save locally. Check your browser storage and export a backup.'; return false; }
}
function el(tag, className, text) { const node=document.createElement(tag); if (className) node.className=className; if (text !== undefined) node.textContent=text; return node; }
function makeButton(label, className, handler) { const b=el('button',className,label); b.type='button'; b.addEventListener('click',handler); return b; }
function render() {
  const today=localDate(); const filtered=selectTasks(state.tasks,view,today,search);
  const meta=views[view] || (view.startsWith('project:') ? [state.projects.find(p=>p.id===view.slice(8))?.name || 'Project','Your project tasks, all in one place.'] : views.inbox);
  $('page-title').textContent=meta[0]; $('crumb').textContent=meta[0]; $('page-description').textContent=meta[1];
  $('stat-open').textContent=state.tasks.filter(t=>!t.completed).length;
  $('stat-today').textContent=state.tasks.filter(t=>!t.completed && t.due && t.due<=today).length;
  $('stat-done').textContent=state.tasks.filter(t=>t.completed).length;
  $('inbox-count').textContent=String(state.tasks.filter(t=>!t.completed&&!t.projectId).length);
  $('result-count').textContent='('+filtered.length+')';
  document.querySelectorAll('[data-view]').forEach(b=>{const active=b.dataset.view===view; b.classList.toggle('selected',active); if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  const projectNav=$('project-nav');projectNav.replaceChildren();
  const projectSelect=$('task-project'); const prev=projectSelect.value;
  projectSelect.replaceChildren(new Option('Inbox',''));
  state.projects.forEach(p=>{const nav=makeButton('◈  '+p.name,'nav-item project-nav',()=>{view='project:'+p.id;projectSelect.value=p.id;render();});nav.dataset.view='project:'+p.id; if(view===nav.dataset.view)nav.classList.add('selected');projectNav.append(nav);projectSelect.add(new Option(p.name,p.id));});
  projectSelect.value=view.startsWith('project:')?view.slice(8):prev;
  const list=$('task-list');list.replaceChildren();$('empty').hidden=filtered.length!==0;
  filtered.forEach(task=>{
    const item=el('li','task-row'+(task.completed?' is-completed':''));
    const check=el('input','task-checkbox');check.type='checkbox';check.checked=!!task.completed;check.setAttribute('aria-label',(task.completed?'Reopen ':'Complete ')+task.title);
    check.addEventListener('change',()=>{const old=task.completed;task.completed=check.checked;task.completedAt=check.checked?new Date().toISOString():null;if(!persist()){task.completed=old;task.completedAt=old?task.completedAt:null;}render();});
    const body=el('div','task-body');body.append(el('strong','task-name',task.title));
    const details=el('div','task-details');
    details.append(el('span','priority priority-'+task.priority,'P'+task.priority));
    if(task.due)details.append(el('span',task.due<today&&!task.completed?'due overdue':'due',task.due));
    const project=state.projects.find(p=>p.id===task.projectId);if(project)details.append(el('span','project-pill',project.name));body.append(details);
    const edit=makeButton('Edit','row-button',()=>{
      const changed=prompt('Edit task title',task.title); if(changed===null)return;
      const title=changed.trim();if(!title||title.length>240){$('status').textContent='Task title must be 1–240 characters.';return;}
      const old=task.title; task.title=title;if(!persist())task.title=old;render();
    });
    const remove=makeButton('Delete','row-button danger',()=>{if(!confirm('Delete this task?'))return; const previous=state.tasks;state.tasks=state.tasks.filter(t=>t.id!==task.id);if(!persist())state.tasks=previous;render();});
    item.append(check,body,edit,remove);list.append(item);
  });
}
$('task-form').addEventListener('submit',e=>{
  e.preventDefault();
  try { const task=newTask($('task-title').value,$('task-project').value,$('task-date').value,$('task-priority').value);state.tasks.push(task);if(!persist())state.tasks.pop();else $('task-form').reset();render();$('task-title').focus(); }
  catch(err){$('status').textContent=err.message;}
});
document.querySelectorAll('#primary-nav [data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;render();}));
$('search').addEventListener('input',e=>{search=e.target.value;render();});
const dialog=$('project-dialog');$('new-project').addEventListener('click',()=>dialog.showModal());
$('project-cancel').addEventListener('click',()=>dialog.close());
$('project-form').addEventListener('submit',e=>{
  e.preventDefault();const name=$('project-title').value.trim();if(!name)return;
  const project={id:crypto.randomUUID(),name};state.projects.push(project);
  if(!persist())state.projects.pop();else{view='project:'+project.id;dialog.close();$('project-form').reset();}render();
});
$('theme-toggle').addEventListener('click',()=>{const root=document.documentElement;const next=root.dataset.mode==='dark'?'light':'dark';root.dataset.mode=next;try{localStorage.setItem('goreecloud.tasks.theme',next);}catch{}});
const savedTheme=localStorage.getItem('goreecloud.tasks.theme');if(savedTheme==='dark'||savedTheme==='light')document.documentElement.dataset.mode=savedTheme;
$('export-data').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='goreecloud-tasks-'+localDate()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);});
render();
