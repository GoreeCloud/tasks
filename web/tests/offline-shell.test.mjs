import test from "node:test";
import assert from "node:assert/strict";
import {mkdtemp,mkdir,readFile,rm,writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {buildOfflineShell} from "../scripts/build-offline-shell.mjs";

test("worker contains only explicitly built public static assets, never API/user files",async()=>{
  const dir=await mkdtemp(join(tmpdir(),"goreecloud-tasks-public-shell-"));
  try {
    await mkdir(join(dir,"assets"));
    await writeFile(join(dir,"index.html"),'<div id="root"></div><script src="/assets/app-001.js"></script>');
    await writeFile(join(dir,"assets","app-001.js"),"console.log('public source')");
    await writeFile(join(dir,"assets","app-001.css"),"body { margin: 0 }");
    await writeFile(join(dir,"assets","user-export.json"),"PRIVATE-SYNTHETIC-NOT-FOR-APP-SHELL");
    const manifest=await buildOfflineShell(dir);
    assert.deepEqual(manifest.paths,["/index.html","/assets/app-001.css","/assets/app-001.js"]);
    const worker=await readFile(join(dir,"offline-sw.js"),"utf8");
    assert.ok(worker.includes(manifest.cacheName));
    assert.ok(worker.includes("url.pathname.startsWith(\"/api/\")"),
      "All private API requests must bypass the service worker");
    assert.ok(worker.includes('request.headers.has("Authorization")'));
    assert.ok(!worker.includes("PRIVATE-SYNTHETIC"));
    assert.ok(!worker.includes("user-export.json"));
    const first=manifest.cacheName;
    await writeFile(join(dir,"assets","app-002.js"),"console.log('new public asset')");
    const revised=await buildOfflineShell(dir);
    assert.notEqual(revised.cacheName,first,"New asset names must change the app-shell version");
  }finally{await rm(dir,{recursive:true,force:true});}
});

test("unrecognized index or missing JS/CSS fails closed",async()=>{
  const dir=await mkdtemp(join(tmpdir(),"goreecloud-tasks-invalid-shell-"));
  try{
    await mkdir(join(dir,"assets"));
    await writeFile(join(dir,"index.html"),"not the application");
    await assert.rejects(buildOfflineShell(dir),/Unrecognized public app index/);
    await writeFile(join(dir,"index.html"),'<div id="root"></div>');
    await assert.rejects(buildOfflineShell(dir),/Built app shell needs bundled JS and CSS/);
  }finally{await rm(dir,{recursive:true,force:true});}
});
