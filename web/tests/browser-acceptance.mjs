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
   const tasks=[],projects=[],violations=[],errors=[];
   let serial=0;
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
       if(method==="GET"&&endpoint==="/tasks")return response(tasks);
       if(method==="GET"&&endpoint==="/projects")return response(projects);
       if(method==="POST"&&endpoint==="/tasks"){
        const input=request.postDataJSON();
        const entry={id:"synthetic-task-"+(++serial),title:input.title,description:input.description??"",
         priority:input.priority??2,project_id:input.project_id??null,due_date:input.due_date??null,
         tags:input.tags??[],recurrence:input.recurrence??"none",completed_at:null,version:1,created_at:"2026-11-20T14:00:00Z"};
        tasks.push(entry);return response(entry,201);
       }
       if(method==="PATCH"&&/^\/tasks\/synthetic-task-\d+$/.test(endpoint)){
         const task=tasks.find(t=>endpoint.endsWith(t.id)),data=request.postDataJSON();
         if(!task||task.version!==data.expected_version)return response({detail:"Conflict"},409);
         Object.assign(task,{title:data.title??task.title,description:data.description??task.description,
            tags:data.tags??task.tags,version:task.version+1});return response(task);
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
    await page.getByRole("button",{name:"Calendar",exact:true}).click();
    await page.getByRole("region",{name:"Task calendar"}).waitFor({timeout:9000});
    const calendarWidth=await page.evaluate(()=>({
      scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth
    }));
    assert.ok(calendarWidth.scroll<=calendarWidth.client+1,
      "calendar should fit the viewport: "+JSON.stringify(calendarWidth));
    await page.getByRole("button",{name:"My tasks",exact:true}).click();
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
    assert.equal(tasks.length,1);
    assert.equal(tasks[0].title,"Synthetic revised task");
    assert.ok(tasks[0].completed_at);
    assert.equal(violations.length,0,JSON.stringify(violations));
    assert.equal(errors.length,0,JSON.stringify(errors));
    if(screenshotDir) {
      const file=join(screenshotDir,"tasks-"+name+"-"+caseName+"-focus.png");
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:file,fullPage:true});
    }
    console.log("PASSED",name,browser.version(),caseName,"synthetic create/edit/filter/complete/focus, no external requests");
    total++;
   }finally{await context.close()}
  }
 }finally{await browser.close()}
}
console.log("SCENARIOS_PASSED",total);
