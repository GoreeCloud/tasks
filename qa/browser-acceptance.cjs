/* GoreeCloud Tasks browser acceptance: NODE_PATH=<playwright-and-axe-node_modules> node qa/browser-acceptance.cjs */
const {createServer}=require('node:http');
const {readFileSync,mkdirSync}=require('node:fs');
const {join,resolve,extname}=require('node:path');
const assert=require('node:assert/strict');
const {chromium,firefox}=require('playwright');
const axe=require.resolve('axe-core');
const root=resolve(__dirname,'../web');
const dest=process.env.GC_TASKS_QA_DIR||'/tmp/goreecloud-tasks-browser-qa';
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css'};
const server=createServer((req,res)=>{
  const name=decodeURIComponent((req.url||'/').split('?')[0]);
  if(!/^\/[a-zA-Z0-9._/-]*$/.test(name)||name.includes('..')){res.writeHead(400);return res.end();}
  try{let path=join(root,name==='/'?'index.html':name.slice(1));res.setHeader('Content-Type',types[extname(path)]||'application/octet-stream');res.end(readFileSync(path));}
  catch{res.writeHead(404);res.end();}
});
let count=0;
function note(name,data){count++;console.log(JSON.stringify({name,...data}));}
async function geometry(page){return page.evaluate(()=>({width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,offenders:[...document.querySelectorAll('body *')].filter(e=>{let r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1&&getComputedStyle(e).position!=='absolute'}).slice(0,8).map(e=>e.tagName.toLowerCase()+'#'+e.id+'.'+String(e.className).slice(0,40))}));}
async function axeAudit(page,label){
  await page.addScriptTag({path:axe});
  const result=await page.evaluate(()=>window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}}));
  const violations=result.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target).slice(0,5)}));
  note(label+' axe',{violations,passes:result.passes.length,incomplete:result.incomplete.length});
  assert.equal(violations.length,0,label+' axe violations');
}
async function run(engine,port){
  const browser=await engine.launch({headless:true,args:engine.name()==='chromium'?['--no-sandbox']:[]});
  const url='http://127.0.0.1:'+port+'/';
  try{
    const context=await browser.newContext({viewport:{width:1366,height:900},colorScheme:'dark',reducedMotion:'reduce'});
    const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(url,{waitUntil:'networkidle'});
    assert.equal(await page.locator('html').getAttribute('data-mode'),'light');
    assert.equal(await page.locator('html').getAttribute('data-gc-accent'),'neutral');
    await page.locator('#task-title').fill('Synthetic acceptance task');
    await page.locator('#task-form button[type=submit]').click();
    assert.equal(await page.locator('.task-row').count(),1);
    await page.getByRole('button',{name:'Edit Synthetic acceptance task'}).click();
    await page.locator('#edit-task-title').fill('Edited acceptance task');
    await page.locator('#edit-task-form button[type=submit]').click();
    assert.equal(await page.locator('.task-name').innerText(),'Edited acceptance task');
    await page.screenshot({path:join(dest,engine.name()+'-desktop-light.png'),fullPage:true});
    await page.locator('#select-visible').check();
    await page.locator('#bulk-complete').click();
    assert.equal(await page.locator('#stat-rate').innerText(),'100%');
    await page.locator('[data-view=completed]').first().click();
    await page.locator('#select-visible').check();
    await page.locator('#bulk-reopen').click();
    await page.locator('[data-view=all]').first().click();
    await page.locator('#select-visible').check();
    page.once('dialog',x=>x.accept());
    await page.locator('#bulk-trash').click();
    await page.locator('[data-view=trash]').first().click();
    await page.getByRole('button',{name:'Restore Edited acceptance task'}).click();
    await page.locator('[data-view=all]').first().click();
    assert.equal(await page.locator('.task-row').count(),1);
    await page.locator('#theme-toggle').click();
    await page.locator('#appearance-mode').selectOption('dark');
    await page.locator('#appearance-accent').selectOption('lagoon');
    await page.locator('#appearance-form button[type=submit]').click();
    await page.reload({waitUntil:'networkidle'});
    assert.equal(await page.locator('html').getAttribute('data-mode'),'dark');
    assert.equal(await page.locator('html').getAttribute('data-gc-accent'),'lagoon');
    const colors=await page.evaluate(()=>({button:getComputedStyle(document.querySelector('.primary-button')).backgroundColor,canvas:getComputedStyle(document.body).backgroundColor}));
    const geo=await geometry(page);
    note(engine.name()+' desktop',{colors,geo,errors});
    assert.ok(geo.scrollWidth<=geo.width+1,'desktop overflow');
    assert.deepEqual(errors,[]);
    await axeAudit(page,engine.name()+' desktop');
    await page.screenshot({path:join(dest,engine.name()+'-desktop.png'),fullPage:true});
    await page.locator('#search').focus();await page.locator('#search').blur();await page.keyboard.press('/');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'search');
    await page.locator('#search').blur();await page.keyboard.press('n');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'task-title');
    // Portable schema-one backup must restore into an independent empty profile.
    const [download]=await Promise.all([
      page.waitForEvent('download'), page.locator('#export-data').click()
    ]);
    const chunks=[];for await(const chunk of await download.createReadStream())chunks.push(chunk);
    const backup=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    assert.equal(backup.schema,1);
    assert.equal(backup.tasks.length,1);
    const restoreContext=await browser.newContext();
    const restorePage=await restoreContext.newPage();
    await restorePage.goto(url,{waitUntil:'networkidle'});
    restorePage.once('dialog',dialog=>dialog.accept());
    await restorePage.locator('#import-file').setInputFiles({
      name:'synthetic-tasks.json',mimeType:'application/json',
      buffer:Buffer.from(JSON.stringify(backup))
    });
    await restorePage.getByText('Edited acceptance task').waitFor();
    assert.equal(await restorePage.locator('.task-row').count(),1);
    note(engine.name()+' backup roundtrip',{schema:backup.schema,taskCount:backup.tasks.length});
    await restoreContext.close();
    // Editing a task with notes must upgrade its export to schema 2, without
    // changing the original task identity or completion metadata.
    await page.getByRole('button',{name:'Edit Edited acceptance task'}).click();
    await page.locator('#edit-task-description').fill('Private context 🧭\nSecond line');
    await page.locator('#edit-task-form button[type=submit]').click();
    assert.equal(await page.locator('.task-description').innerText(),'Private context 🧭\nSecond line');
    const [notesDownload]=await Promise.all([
      page.waitForEvent('download'),page.locator('#export-data').click()
    ]);
    const notesChunks=[];
    for await(const chunk of await notesDownload.createReadStream())notesChunks.push(chunk);
    const schemaTwo=JSON.parse(Buffer.concat(notesChunks).toString('utf8'));
    assert.equal(schemaTwo.schema,2);
    assert.equal(schemaTwo.tasks[0].description,'Private context 🧭\nSecond line');
    const notesContext=await browser.newContext();
    const notesPage=await notesContext.newPage();
    await notesPage.goto(url,{waitUntil:'networkidle'});
    notesPage.once('dialog',dialog=>dialog.accept());
    await notesPage.locator('#import-file').setInputFiles({name:'notes.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(schemaTwo))});
    await notesPage.getByText('Private context 🧭').waitFor();
    await notesPage.reload({waitUntil:'networkidle'});
    assert.equal(await notesPage.locator('.task-description').innerText(),'Private context 🧭\nSecond line');
    // Search uses titles AND notes even after a fresh profile restores v2 JSON.
    await notesPage.locator('#search').fill('SECOND LINE');
    assert.equal(await notesPage.locator('.task-row').count(),1);
    await notesPage.locator('#search').fill('No matching notes');
    assert.equal(await notesPage.locator('.task-row').count(),0);
    await notesPage.locator('#search').fill('Private context');
    assert.equal(await notesPage.locator('.task-row').count(),1);
    notesPage.once('dialog',dialog=>dialog.accept());
    await notesPage.getByRole('button',{name:'Delete Edited acceptance task'}).click();
    await notesPage.locator('[data-view=trash]').first().click();
    assert.equal(await notesPage.locator('.task-row').count(),1);
    await notesPage.locator('#search').fill('SECOND LINE');
    assert.equal(await notesPage.locator('.task-row').count(),1);
    await notesPage.getByRole('button',{name:'Restore Edited acceptance task'}).click();
    await notesPage.locator('[data-view=all]').first().click();
    assert.equal(await notesPage.locator('.task-row').count(),1);
    // Explicit user action duplicates a task, without losing the original or notes.
    await notesPage.getByRole('button',{name:'Duplicate Edited acceptance task'}).click();
    assert.equal(await notesPage.locator('.task-row').count(),2);
    const [copyDownload]=await Promise.all([
      notesPage.waitForEvent('download'),notesPage.locator('#export-data').click()
    ]);
    const copyChunks=[];for await(const chunk of await copyDownload.createReadStream())copyChunks.push(chunk);
    const duplicates=JSON.parse(Buffer.concat(copyChunks).toString('utf8')).tasks;
    assert.equal(duplicates.length,2);
    assert.notEqual(duplicates[0].id,duplicates[1].id);
    assert.ok(duplicates.every(t=>t.description==='Private context 🧭\nSecond line'));
    assert.ok(duplicates.every(t=>!t.completed && t.completedAt===null));
    note(engine.name()+' duplicate notes',{count:duplicates.length,distinctIds:true});
    note(engine.name()+' notes search and Trash recovery',{matched:true,restored:true});
    note(engine.name()+' notes v2 portable roundtrip',{schema:schemaTwo.schema,notes:schemaTwo.tasks[0].description.length});
    await notesContext.close();
    await context.close();
    const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1,colorScheme:'dark'});
    const small=await mobile.newPage();const mobileErrors=[];small.on('pageerror',e=>mobileErrors.push(e.message));
    await small.goto(url,{waitUntil:'networkidle'});
    assert.equal(await small.locator('#task-form').isVisible(),false);
    await small.locator('#mobile-add-task').click();
    assert.equal(await small.locator('#mobile-add-task').getAttribute('aria-expanded'),'true');
    await small.locator('#task-title').fill('Mobile acceptance task');
    await small.locator('#task-form button[type=submit]').click();
    assert.equal(await small.locator('#task-form').isVisible(),false);
    await small.screenshot({path:join(dest,engine.name()+'-mobile-light.png'),fullPage:true});
    await small.locator('.mobile-bottom-nav [data-mobile-view=today]').click();
    assert.equal(await small.locator('#page-title').innerText(),'Today');
    await small.locator('.mobile-bottom-nav [data-mobile-view=inbox]').click();
    assert.equal(await small.locator('#page-title').innerText(),'Inbox');
    await small.locator('#mobile-browse').click();
    assert.equal(await small.locator('#mobile-browse-dialog').evaluate(el=>el.open),true);
    await small.locator('#mobile-browse-dialog [data-mobile-view=soon]').click();
    assert.equal(await small.locator('#page-title').innerText(),'Next 7 days');
    await small.locator('.mobile-bottom-nav [data-mobile-view=inbox]').click();
    await small.locator('#mobile-browse').click();
    await small.locator('#mobile-new-project').click();
    await small.locator('#project-title').fill('Synthetic mobile project');
    await small.locator('#project-form button[type=submit]').click();
    assert.equal(await small.locator('#page-title').innerText(),'Synthetic mobile project');
    await small.locator('.mobile-bottom-nav [data-mobile-view=inbox]').click();
    await small.locator('#mobile-search').click();
    assert.equal(await small.evaluate(()=>document.activeElement.id),'search');
    await small.locator('#mobile-add-task').click();
    assert.equal(await small.evaluate(()=>document.activeElement.id),'task-title');
    await small.locator('.mobile-options summary').click();
    await small.locator('#mobile-theme').click();
    await small.locator('#appearance-mode').selectOption('dark');
    await small.locator('#appearance-accent').selectOption('moss');
    await small.locator('#appearance-form button[type=submit]').click();
    const mobileGeo=await geometry(small);
    note(engine.name()+' mobile',{geo:mobileGeo,errors:mobileErrors});
    assert.ok(mobileGeo.scrollWidth<=mobileGeo.width+1,'mobile overflow');
    assert.deepEqual(mobileErrors,[]);
    await axeAudit(small,engine.name()+' mobile');
    await small.screenshot({path:join(dest,engine.name()+'-mobile.png'),fullPage:true});
    await small.evaluate(()=>{document.documentElement.style.zoom='200%';});
    const zoom=await geometry(small);
    const widths=await small.evaluate(()=>Object.fromEntries(['html','body','.shell','.sidebar','.workspace','.content','.hero','.overview','.task-panel','.task-row','.mobile-toolbar','#primary-nav'].map(s=>{let e=document.querySelector(s);return [s,{client:e.clientWidth,scroll:e.scrollWidth,rect:e.getBoundingClientRect().width,scale:getComputedStyle(e).zoom}]})));
    const media=await small.evaluate(()=>({innerWidth,media720:matchMedia('(max-width:720px)').matches,media480:matchMedia('(max-width:480px)').matches,workspaceContainer:getComputedStyle(document.querySelector('.workspace')).containerType,sidebarContainer:getComputedStyle(document.querySelector('.sidebar')).containerType,grid:getComputedStyle(document.querySelector('.list-controls')).gridTemplateColumns}));
    note(engine.name()+' zoom 200%',{geo:zoom,widths,media});
    await small.screenshot({path:join(dest,engine.name()+'-zoom.png'),fullPage:true});
    assert.ok(zoom.scrollWidth<=zoom.width+1,'zoom overflow');
    if(engine.name()==='chromium'){
      await small.emulateMedia({forcedColors:'active'});
      note('chromium forced colors',{active:await small.evaluate(()=>matchMedia('(forced-colors: active)').matches)});
    }
    await mobile.close();
  }finally{await browser.close();}
}
(async()=>{
  mkdirSync(dest,{recursive:true});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{
    await run(chromium,server.address().port);
    await run(firefox,server.address().port);
    note('complete',{screenshots:dest,checks:count});
  }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
