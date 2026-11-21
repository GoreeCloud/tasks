#!/usr/bin/env node
// Isolated Chromium real service-worker acceptance. No production API,
// external network access, task credentials, browser installation or uploads.
import assert from "node:assert/strict";
import {existsSync,statSync} from "node:fs";
import {isAbsolute} from "node:path";
import {pathToFileURL} from "node:url";
for(const key of ["GC_PLAYWRIGHT_CORE_MODULE","GC_CHROMIUM_BIN"]){
  const value=process.env[key];
  if(!value||!isAbsolute(value)||!existsSync(value)||!statSync(value).isFile())
    throw Error(key+" requires an inspected absolute file path");
}
const core=await import(pathToFileURL(process.env.GC_PLAYWRIGHT_CORE_MODULE).href);
const origin="http://127.0.0.1:18758";
const browser=await core.chromium.launch({
  executablePath:process.env.GC_CHROMIUM_BIN,headless:true,timeout:20000
});
const context=await browser.newContext({serviceWorkers:"allow"});
const syntheticToken="fake-local-test-token-no-real-secrets-123456";
const vaultPassword="test-only-local-offline-vault-pass-123456";
const apiCalls=[],pageErrors=[];
try {
  const page=await context.newPage();
  page.on("pageerror",err=>pageErrors.push(err.message));
  await page.route("**/api/v1/**",async route=>{
    const req=route.request(),url=new URL(req.url());
    assert.equal(url.origin,origin);
    assert.equal(req.headers().authorization,"Bearer "+syntheticToken);
    apiCalls.push(url.pathname);
    if(url.pathname==="/api/v1/sync/bootstrap") {
      return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({
        format:"goreecloud-tasks-sync-1",cursor:1,projects:[],
        tasks:[{id:"synthetic-1",title:"Synthetic public-shell fixture",description:"",
          priority:2,project_id:null,parent_id:null,due_date:null,tags:[],
          recurrence:"none",completed_at:null,version:1,
          created_at:"2026-11-21T12:00:00Z"}]
      })});
    }
    throw Error("Unexpected API call: "+url.pathname);
  });
  await page.goto(origin,{waitUntil:"networkidle",timeout:15000});
  await page.getByLabel("Server API token").fill(syntheticToken);
  await page.getByRole("button",{name:"Open workspace"}).click();
  await page.getByRole("button",{name:"Offline",exact:true}).click();
  await page.getByLabel("Offline vault passphrase").fill(vaultPassword);
  await page.getByLabel("Confirm offline passphrase").fill(vaultPassword);
  await page.getByRole("button",{name:"Enable vault from server"}).click();
  await page.getByRole("heading",{name:"Draft a standalone task"}).waitFor({timeout:12000});
  await page.getByLabel("Offline task title").fill("Private offline-only draft");
  await page.getByRole("button",{name:"Save encrypted draft"}).click();
  await page.getByRole("region",{name:"Pending offline drafts"})
    .getByText("Private offline-only draft").waitFor({timeout:9000});
  await page.getByRole("button",{name:"Enable offline app shell"}).click();
  await page.getByRole("button",{name:"Remove offline app shell"}).waitFor({timeout:15000});
  await page.waitForFunction(()=>!!navigator.serviceWorker.controller,{timeout:15000});
  const cacheKeys=await page.evaluate(async()=>{
    const keys=await caches.keys();
    const urls=(await Promise.all(keys.map(async key=>{
      const cache=await caches.open(key);
      return (await cache.keys()).map(req=>req.url);
    }))).flat();
    return {keys,urls};
  });
  assert.ok(cacheKeys.keys.some(key=>key.startsWith("goreecloud-tasks-public-shell-")));
  assert.ok(cacheKeys.urls.some(url=>url.endsWith("/index.html")));
  assert.ok(cacheKeys.urls.some(url=>url.endsWith(".js")));
  assert.ok(cacheKeys.urls.every(url=>url.startsWith(origin+"/")&&!url.includes("/api/")));
  assert.ok(!JSON.stringify(cacheKeys).includes("Private offline-only draft"));
  const before=apiCalls.length;
  await context.setOffline(true);
  await page.reload({waitUntil:"domcontentloaded",timeout:15000});
  await page.getByRole("button",{name:"Open encrypted vault without server token"}).click();
  await page.getByRole("heading",{name:"Encrypted offline vault",exact:true}).waitFor({timeout:12000});
  await page.getByLabel("Offline vault passphrase").fill(vaultPassword);
  await page.getByRole("button",{name:"Unlock vault"}).click();
  await page.getByRole("region",{name:"Pending offline drafts"})
    .getByText("Private offline-only draft").waitFor({timeout:12000});
  assert.equal(apiCalls.length,before,"Tokenless offline viewing must not call the server");
  await context.setOffline(false);
  await page.getByRole("button",{name:"Remove offline app shell"}).click();
  await page.getByRole("button",{name:"Enable offline app shell"}).waitFor({timeout:12000});
  assert.equal((await page.evaluate(()=>caches.keys()))
    .some(key=>key.startsWith("goreecloud-tasks-public-shell-")),false);
  assert.deepEqual(pageErrors,[]);
  console.log("OFFLINE_SHELL_ACCEPTANCE_PASSED",
    "opt-in public assets, offline reload, tokenless encrypted vault, zero private caches");
}finally{await context.close();await browser.close();}
