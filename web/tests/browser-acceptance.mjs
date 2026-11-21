#!/usr/bin/env node
// Opt-in, read-only-network QA: all Tasks data is synthesized in memory.
// No application credentials, production API, browser installation, or real task writes.
import assert from "node:assert/strict";
import {existsSync,statSync} from "node:fs";
import {join,isAbsolute} from "node:path";
import {pathToFileURL} from "node:url";
const requirements=["GC_PLAYWRIGHT_CORE_MODULE","GC_CHROMIUM_BIN","GC_FIREFOX_BIN","GC_WEBKIT_BIN"];
for(const key of requirements){
 const value=process.env[key];
 if(!value||!isAbsolute(value)||!existsSync(value)||!statSync(value).isFile())
  throw Error(key+" requires an existing, inspected absolute file path (no downloads)");
}
const screenshotDir=process.env.GC_QA_SCREENSHOTS_DIR;
if(screenshotDir&&(!isAbsolute(screenshotDir)||!existsSync(screenshotDir)||!statSync(screenshotDir).isDirectory()))
 throw Error("GC_QA_SCREENSHOTS_DIR must be an existing absolute directory");
const core=await import(pathToFileURL(process.env.GC_PLAYWRIGHT_CORE_MODULE).href);
const engines=[
 ["chromium",core.chromium,process.env.GC_CHROMIUM_BIN],
 ["firefox",core.firefox,process.env.GC_FIREFOX_BIN],
 ["webkit",core.webkit,process.env.GC_WEBKIT_BIN]];
const frames=[["desktop-light",900,800,false],["mobile-dark",390,844,true],["compact-light",320,760,false]];
const origin="http://127.0.0.1:18756";
let total=0;
for(const [name,engine,binary]of engines){
 const browser=await engine.launch({executablePath:binary,headless:true,timeout:20000});
 try{
  for(const [caseName,width,height,dark]of frames){
   const context=await browser.newContext({viewport:{width,height},colorScheme:dark?"dark":"light",reducedMotion:"reduce",serviceWorkers:"block"});
   const tasks=[],projects=[],habits=[],changes=[],violations=[],errors=[];
   let serial=0, malformedNextFeed=false;
   try{
    const page=await context.newPage();
    page.on("pageerror",e=>errors.push(e.message));
    await page.route("**/*",async route=>{
      const request=route.request(), url=new URL(request.url()), path=url.pathname;
      if(url.origin!==origin){violations.push("external request");return route.abort("blockedbyclient")}
      if(path.startsWith("/api/")){
       if(request.headers().authorization!=="Bearer fake-synthetic-token-0000000000000000"){
         violations.push("unrecognized dev-only token");return route.abort("blockedbyclient");
       }
       const method=request.method(), endpoint=path.replace(/^\/api\/v1/,"");
       const response=(body,status=200)=>route.fulfill({status,contentType:"application/json",body:JSON.stringify(body)});
       if(method==="GET"&&endpoint==="/tasks")return response(tasks.slice(0,1000));
       if(method==="GET"&&endpoint==="/sync/bootstrap")
         return response({format:"goreecloud-tasks-sync-1",cursor:tasks.length,
           tasks,projects});
       if(method==="GET"&&endpoint==="/sync/changes"){
         const after=Number(url.searchParams.get("after")??"0");
         if(malformedNextFeed) {
           malformedNextFeed=false;
           return response({format:"goreecloud-tasks-sync-1",after,
             next_cursor:after+1,has_more:false,changes:[]});
         }
         const limit=Number(url.searchParams.get("limit")??"200");
         const newer=changes.filter(e=>e.cursor>after);
         const events=newer.slice(0,limit);
         return response({format:"goreecloud-tasks-sync-1",after,
           next_cursor:events.length?events.at(-1).cursor:after,
           has_more:newer.length>events.length,changes:events});
       }
       if(method==="GET"&&endpoint==="/projects")return response(projects);
       if(method==="GET"&&endpoint==="/habits")return response(habits);
       if(method==="POST"&&endpoint==="/import/csv/preview"){
         const input=request.postDataJSON();
         assert.equal(input.format,"generic");
         assert.match(input.csv_text,/Imported from CSV/);
         return response({format:"generic",count:1,checksum:"a".repeat(64),warnings:[],
           tasks:[{title:"Imported from CSV",description:"",due_date:null,
             priority:2,tags:[],recurrence:"none",parent_index:null}]});
       }
       if(method==="POST"&&endpoint==="/import/csv"){
         const input=request.postDataJSON();
         assert.ok(request.headers()["idempotency-key"]);
         assert.equal(input.checksum,"a".repeat(64));
         const entry={id:"synthetic-task-"+(++serial),title:"Imported from CSV",description:"",
           priority:2,project_id:null,parent_id:null,due_date:null,tags:[],
           recurrence:"none",completed_at:null,version:1,created_at:"2026-11-20T14:00:00Z"};
         tasks.push(entry);
         return response({count:1,ids:[entry.id],warnings:[],checksum:input.checksum},201);
       }
       if(method==="POST"&&endpoint==="/habits"){
         const input=request.postDataJSON();
         const habit={id:"synthetic-habit-"+(++serial),name:input.name,description:input.description??"",
           version:1,current_streak:0,total_checkins:0,checked_in_today:false,as_of:"2026-11-21"};
         habits.push(habit);return response(habit,201);
       }
       if(method==="POST"&&/^\/habits\/synthetic-habit-\d+\/checkins$/.test(endpoint)){
         const habit=habits.find(h=>endpoint.includes(h.id));
         if(!habit)return response({detail:"Missing habit"},404);
         const input=request.postDataJSON();
         if(input.expected_version!==habit.version)return response({detail:"Conflict"},409);
         habit.checked_in_today=true;habit.current_streak=1;habit.total_checkins++;
         habit.version++;return response(habit,201);
       }
       if(method==="POST"&&endpoint==="/tasks"){
        const input=request.postDataJSON();
        const entry={id:"synthetic-task-"+(++serial),title:input.title,description:input.description??"",
         priority:input.priority??2,project_id:input.project_id??null,due_date:input.due_date??null,
         tags:input.tags??[],parent_id:input.parent_id??null,recurrence:input.recurrence??"none",completed_at:null,version:1,created_at:"2026-11-20T14:00:00Z"};
        tasks.push(entry);return response(entry,201);
       }
       if(method==="PATCH"&&/^\/tasks\/synthetic-task-\d+$/.test(endpoint)){
         const task=tasks.find(t=>endpoint.endsWith(t.id)),data=request.postDataJSON();
         if(!task||task.version!==data.expected_version)return response({detail:"Conflict"},409);
         Object.assign(task,{title:data.title??task.title,description:data.description??task.description,
            tags:data.tags??task.tags,priority:data.priority??task.priority,version:task.version+1});return response(task);
       }
       if(method==="POST"&&/^\/tasks\/synthetic-task-\d+\/(complete|reopen)$/.test(endpoint)){
         const task=tasks.find(t=>endpoint.includes("/"+t.id+"/"));
         if(!task)return response({detail:"Missing"},404);
         if(task.version!==request.postDataJSON().expected_version)
           return response({detail:"Task revision conflict"},409);
         task.completed_at=endpoint.endsWith("complete")?"2026-11-20T14:01:00Z":null;
         task.version++;return response(task);
       }
       if(method==="GET"&&endpoint==="/export")return response({projects,tasks});
       if(method==="GET"&&endpoint==="/export.ics")
         return route.fulfill({status:200,contentType:"text/calendar; charset=utf-8",
           headers:{"Content-Disposition":'attachment; filename="goreecloud-tasks.ics"'},
           body:"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"});
       violations.push("unexpected API "+method+" "+endpoint);return response({detail:"unexpected mock call"},500);
      }
      if(request.method()!=="GET"){violations.push("unexpected content mutation");return route.abort("blockedbyclient")}
      return route.continue();
    });
    const nav=await page.goto(origin+"/",{waitUntil:"networkidle",timeout:15000});
    assert.equal(nav?.status(),200);
    const heading=page.getByRole("heading",{name:"Where your plans come together."});
    await heading.waitFor();
    const input=page.getByLabel("Server API token");
    await input.fill("fake-synthetic-token-0000000000000000");
    await page.getByRole("button",{name:"Open workspace"}).click();
    await page.getByRole("heading",{name:"My tasks"}).waitFor({timeout:10000});
    const audit=await page.evaluate(()=>{
       const el=document.documentElement;
       return {scroll:el.scrollWidth,client:el.clientWidth,scheme:getComputedStyle(el).colorScheme,
               accent:getComputedStyle(el).getPropertyValue("--gc-brand").trim()};
    });
    console.log(name,caseName,"LOGIN",JSON.stringify(audit));
    if(audit.scroll>audit.client+1) {
      const suspect=await page.evaluate(()=>[...document.querySelectorAll("*")]
       .map(el=>{const rect=el.getBoundingClientRect(),style=getComputedStyle(el);
          return {name:el.tagName.toLowerCase()+(el.className&&typeof el.className==="string"?"."+el.className:""),
           right:Math.round(rect.right),left:Math.round(rect.left),
           w:Math.round(rect.width),scroll:el.scrollWidth,
           cssMinW:style.minWidth,grid:style.gridTemplateColumns,overflow:style.overflowX};})
       .filter(x=>x.right>innerWidth+2&&x.w>0)
       .sort((a,b)=>b.right-a.right).slice(0,24));
      console.log("OVERFLOW_ITEMS",JSON.stringify(suspect));
    }
    assert.ok(audit.scroll<=audit.client+1,"document overflow "+JSON.stringify(audit));
    if(dark)assert.match(audit.scheme,/dark/,"root scheme should follow OS preference");
    const taskTitle="Synthetic review task";
    await page.getByLabel("Task title").fill(taskTitle);
    await page.getByRole("button",{name:/Add task/}).click();
    await page.getByRole("button",{name:"Complete "+taskTitle}).waitFor({timeout:9000});
    await page.locator(".task-description").filter({hasText:taskTitle}).click();
    await page.getByRole("heading",{name:"Task details"}).waitFor();
    await page.getByLabel("Title",{exact:true}).fill("Synthetic revised task");
    await page.getByRole("button",{name:"Save changes"}).click();
    await page.getByRole("button",{name:"Complete Synthetic revised task"}).waitFor({timeout:9000});
    await page.locator(".task-description").filter({hasText:"Synthetic revised task"}).click();
    await page.getByLabel("New subtask title").fill("Synthetic child task");
    await page.getByRole("button",{name:"Add subtask"}).click();
    await page.getByRole("button",{name:"Complete Synthetic child task"}).waitFor({timeout:9000});
    assert.equal(tasks.find(t=>t.title==="Synthetic child task")?.parent_id,tasks[0].id);
    await page.getByRole("button",{name:"Close task details"}).click();
    await page.getByRole("button",{name:"Complete Synthetic child task"}).click();
    await page.getByRole("button",{name:"Calendar",exact:true}).click();
    await page.getByRole("region",{name:"Task calendar"}).waitFor({timeout:9000});
    const calendarWidth=await page.evaluate(()=>({
      scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth
    }));
    assert.ok(calendarWidth.scroll<=calendarWidth.client+1,
      "calendar should fit the viewport: "+JSON.stringify(calendarWidth));
    await page.getByRole("button",{name:"Board",exact:true}).click();
    await page.getByRole("region",{name:"Priority task board"}).waitFor({timeout:9000});
    const boardGeometry=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}));
    assert.ok(boardGeometry.scroll<=boardGeometry.client+1,"board should not overflow viewport");
    await page.getByRole("button",{name:"Move Synthetic revised task to P3"}).click();
    await page.getByRole("button",{name:"Move Synthetic revised task to P4"}).waitFor({timeout:9000});
    assert.equal(tasks[0].priority,3);
    await page.getByRole("button",{name:"Habits",exact:true}).click();
    await page.getByRole("region",{name:"Daily habit tracker"}).waitFor({timeout:9000});
    await page.getByLabel("Habit name").fill("Synthetic daily habit");
    await page.getByRole("button",{name:/Create habit/}).click();
    await page.getByRole("button",{name:"Check in today for Synthetic daily habit"}).waitFor({timeout:9000});
    await page.getByRole("button",{name:"Check in today for Synthetic daily habit"}).click();
    await page.getByRole("button",{name:"Undo today's check-in for Synthetic daily habit"}).waitFor({timeout:9000});
    assert.equal(habits.length,1);
    assert.equal(habits[0].current_streak,1);
    const habitGeometry=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}));
    assert.ok(habitGeometry.scroll<=habitGeometry.client+1,"habits should not overflow viewport");
    await page.getByRole("button",{name:"Import",exact:true}).click();
    await page.getByRole("region",{name:"CSV task migration"}).waitFor({timeout:9000});
    await page.getByLabel("Choose CSV file").setInputFiles({
      name:"invalid-encoding.csv",mimeType:"text/csv",buffer:Buffer.from([0xff,0xfe,0xfa])
    });
    await page.getByRole("alert").filter({hasText:"UTF-8"}).waitFor({timeout:9000});
    assert.equal(tasks.length,2,"Invalid UTF-8 must not import tasks");
    await page.getByLabel("Choose CSV file").setInputFiles({
      name:"synthetic-tasks.csv",mimeType:"text/csv",
      buffer:Buffer.from("title,priority\nImported from CSV,2\n")
    });
    await page.getByRole("button",{name:"Preview import"}).click();
    await page.getByRole("heading",{name:"Ready to import 1 tasks"}).waitFor({timeout:9000});
    assert.equal(tasks.length,2,"Preview must not commit any task data");
    const importGeometry=await page.evaluate(()=>({
      scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth
    }));
    assert.ok(importGeometry.scroll<=importGeometry.client+1,"import should fit viewport");
    await page.getByRole("button",{name:"Confirm import 1 tasks"}).click();
    await page.getByRole("status").filter({hasText:"1 tasks imported"}).waitFor({timeout:9000});
    assert.equal(tasks.length,3);
    await page.getByRole("button",{name:"My tasks",exact:true}).click();
    await page.getByRole("button",{name:"Complete Imported from CSV"}).click();
    const promisedExport=page.waitForEvent("download");
    await page.getByRole("button",{name:"Export calendar",exact:true}).click();
    const downloaded=await promisedExport;
    assert.equal(downloaded.suggestedFilename(),"goreecloud-tasks.ics");
    if(screenshotDir){
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:join(screenshotDir,"tasks-"+name+"-"+caseName+"-tasklist.png"),fullPage:true});
    }
    await page.getByLabel("Search tasks").fill("does-not-match");
    assert.equal(await page.getByRole("button",{name:"Complete Synthetic revised task"}).count(),0);
    await page.getByLabel("Search tasks").fill("");
    await page.getByRole("button",{name:"Complete Synthetic revised task"}).click();
    await page.getByRole("button",{name:"Completed",exact:true}).click();
    await page.getByRole("button",{name:"Reopen Synthetic revised task"}).waitFor({timeout:9000});
    await page.getByRole("button",{name:"Offline",exact:true}).click();
    await page.getByRole("region",{name:"Encrypted offline workspace"}).waitFor({timeout:9000});
    const offlinePass="test-only-vault-passphrase-1234567890";
    await page.getByLabel("Offline vault passphrase").fill(offlinePass);
    await page.getByLabel("Confirm offline passphrase").fill(offlinePass);
    await page.getByRole("button",{name:"Enable vault from server"}).click();
    await page.getByRole("heading",{name:"Draft a standalone task"}).waitFor({timeout:12000});
    await page.getByLabel("Offline task title").fill("Drafted while offline");
    await page.getByRole("button",{name:"Save encrypted draft"}).click();
    await page.getByRole("region",{name:"Pending offline drafts"}).getByText("Drafted while offline").waitFor({timeout:9000});
    assert.equal(tasks.length,3,"Offline draft must not reach the server");
    const stored=await page.evaluate(async()=>{
      const db=await new Promise((resolve,reject)=>{
        const req=indexedDB.open("goreecloud-tasks-offline-v1");
        req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
      });
      const result=await new Promise((resolve,reject)=>{
        const req=db.transaction("secrets").objectStore("secrets").get("vault");
        req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
      });db.close();return result;
    });
    assert.equal(stored.format,"goreecloud-tasks-offline-aesgcm-1");
    assert.ok(stored.salt&&stored.nonce&&stored.data);
    assert.ok(!JSON.stringify(stored).includes("Drafted while offline"),
      "IndexedDB must contain ciphertext, not plaintext task titles");
    await page.getByRole("button",{name:"Lock",exact:true}).click();
    await page.getByLabel("Offline vault passphrase").fill("wrong-password-that-is-long-enough");
    await page.getByRole("button",{name:"Unlock vault"}).click();
    await page.getByRole("alert").filter({hasText:"Incorrect passphrase"}).waitFor({timeout:12000});
    await page.getByLabel("Offline vault passphrase").fill(offlinePass);
    await page.getByRole("button",{name:"Unlock vault"}).click();
    await page.getByRole("region",{name:"Pending offline drafts"}).getByText("Drafted while offline").waitFor({timeout:12000});
    await page.getByRole("region",{name:"Cached task titles"}).getByRole("button",{name:"Edit offline title"}).first().click();
    await page.getByLabel("Edit offline title").fill("This should never overwrite a newer server title");
    await page.getByRole("button",{name:"Queue edit"}).click();
    await page.getByRole("region",{name:"Pending offline drafts"}).getByText("This should never overwrite").waitFor({timeout:9000});
    tasks[0].version++;// Synthetic concurrent server revision: the offline edit must conflict.
    await page.getByRole("button",{name:"Sync now"}).click();
    await page.getByRole("alert").filter({hasText:"Sync stopped at a conflict"}).waitFor({timeout:12000});
    await page.getByRole("region",{name:"Pending offline drafts"}).getByText("CONFLICT").waitFor({timeout:9000});
    assert.equal(tasks.length,4,"Earlier acknowledged create persists despite a later conflict");
    assert.equal(tasks[0].title,"Synthetic revised task","Conflict must not overwrite server data");
    await page.getByRole("region",{name:"Pending offline drafts"}).getByRole("button",{name:"Discard draft"}).click();
    await page.getByRole("button",{name:"Sync now"}).click();
    await page.getByRole("status").filter({hasText:"Server sync completed"}).waitFor({timeout:12000});
    assert.equal(tasks.length,4,"Explicit sync must commit one draft exactly once");
    const newTask={id:"synthetic-task-"+(++serial),title:"From incremental sync",description:"",
      priority:2,project_id:null,parent_id:null,due_date:null,tags:[],recurrence:"none",
      completed_at:null,version:1,created_at:"2026-11-20T14:00:00Z"};
    tasks.push(newTask);
    changes.push({cursor:5,entity:"task",entity_id:newTask.id,operation:"upsert",
      payload:{...newTask},created_at:"2026-11-20T14:02:00Z"});
    malformedNextFeed=true;
    await page.getByRole("button",{name:"Pull server changes"}).click();
    await page.getByRole("alert").filter({hasText:"cursor discontinuity"}).waitFor({timeout:9000});
    assert.equal(await page.getByRole("region",{name:"Cached task titles"}).getByText("From incremental sync").count(),0,
      "Invalid changefeed page must not mutate the encrypted cache");
    await page.getByRole("button",{name:"Pull server changes"}).click();
    await page.getByRole("region",{name:"Cached task titles"}).getByText("From incremental sync").waitFor({timeout:9000});
    changes.push({cursor:6,entity:"task",entity_id:newTask.id,operation:"delete",
      payload:null,created_at:"2026-11-20T14:03:00Z"});
    tasks.splice(tasks.indexOf(newTask),1);
    await page.getByRole("button",{name:"Pull server changes"}).click();
    await page.getByRole("status").filter({hasText:"snapshot updated from the server change feed"}).waitFor({timeout:9000});
    assert.equal(await page.getByRole("region",{name:"Cached task titles"}).getByText("From incremental sync").count(),0,
      "A server deletion tombstone must purge the encrypted cached task");
    page.once("dialog",dialog=>dialog.accept());
    await page.getByRole("button",{name:/Erase offline vault and unsynced drafts/}).click();
    await page.getByRole("heading",{name:"Enable encrypted offline vault"}).waitFor({timeout:9000});
    await page.getByRole("button",{name:"My tasks",exact:true}).click();
    await page.getByRole("button",{name:"Complete Drafted while offline"}).click();
    await page.getByRole("button",{name:"Focus",exact:true}).click();
    await page.getByRole("heading",{name:"Make space for deep work."}).waitFor({timeout:9000});
    await page.getByRole("button",{name:"Start focus"}).click();
    await page.getByRole("button",{name:"Pause"}).waitFor();
    await page.getByRole("button",{name:"Pause"}).click();
    await page.getByRole("button",{name:"Start focus"}).waitFor();
    const final=await page.evaluate(()=>({
      scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
      header:getComputedStyle(document.documentElement).colorScheme
    }));
    assert.ok(final.scroll<=final.client+1,"focus screen overflows viewport");
    assert.equal(tasks.length,4);
    assert.equal(tasks[0].title,"Synthetic revised task");
    assert.ok(tasks.every(task=>task.completed_at));
    assert.equal(violations.length,0,JSON.stringify(violations));
    assert.equal(errors.length,0,JSON.stringify(errors));
    if(screenshotDir) {
      const file=join(screenshotDir,"tasks-"+name+"-"+caseName+"-focus.png");
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:file,fullPage:true});
    }
    if(name==="chromium"&&caseName==="desktop-light"){
      // The ordinary /tasks endpoint intentionally exposes only the first
      // 1,000 rows. The React workspace MUST use the consistent full bootstrap.
      const template=tasks[0];
      for(let i=0;i<1002;i++)tasks.push({
        ...template,id:"synthetic-bulk-"+i,title:"Bulk task "+i,
        completed_at:null,version:1,parent_id:null,project_id:null
      });
      await page.getByRole("button",{name:"My tasks",exact:true}).click();
      await page.getByLabel("Task title").fill("Trigger full workspace refresh");
      await page.getByRole("button",{name:"+ Add task"}).click();
      await page.getByText("1003 active tasks across your workspace").waitFor({timeout:12000});
      assert.equal(tasks.length,1007,"Large fixture should contain all records");
      assert.equal(violations.length,0,JSON.stringify(violations));
      assert.equal(errors.length,0,JSON.stringify(errors));
    }
    console.log("PASSED",name,browser.version(),caseName,"synthetic create/edit/filter/complete/focus plus full 1000+ snapshot, no external requests");
    total++;
   }finally{await context.close()}
  }
 }finally{await browser.close()}
}
console.log("SCENARIOS_PASSED",total);
