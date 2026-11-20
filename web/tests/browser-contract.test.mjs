import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
const here=new URL("../",import.meta.url);
const source=readFileSync(new URL("tests/browser-acceptance.mjs",here),"utf8");
const css=readFileSync(new URL("src/style.css",here),"utf8");
const main=readFileSync(new URL("src/main.tsx",here),"utf8");
test("real browser runner fails closed when inspected browser binaries are absent",()=>{
 const runner=new URL("tests/browser-acceptance.mjs",here);
 const r=spawnSync(process.execPath,[fileURLToPath(runner)],{
  encoding:"utf8",timeout:5000,
  env:{...process.env,GC_PLAYWRIGHT_CORE_MODULE:"",GC_CHROMIUM_BIN:"",
       GC_FIREFOX_BIN:"",GC_WEBKIT_BIN:""}});
 assert.notEqual(r.status,0);
 assert.match(r.stderr,/requires an existing, inspected absolute file path/);
});
test("synthetic task acceptance cannot authenticate or write live task data",()=>{
 assert.match(source,/127\.0\.0\.1:18756/);
 assert.match(source,/route\.fulfill\(/);
 assert.match(source,/fake-synthetic-token-0000000000000000/);
 assert.match(source,/return route\.abort\("blockedbyclient"\)/);
 assert.match(source,/page\.getByLabel\("Server API token"\)/);
 for(const action of ["Add task","Save changes","Completed","Start focus"])
  assert.ok(source.includes(action),"missing synthetic task action "+action);
 assert.doesNotMatch(source,/npm\s+install|playwright\s+install|window\.localStorage|password\.fill\(/);
});
test("Tasks keeps upstream CSS imports and does not duplicate arbitrary brand values",()=>{
 assert.ok(main.indexOf('import "./vendor/gc-ui/tokens.css";')>=0);
 assert.ok(main.indexOf('import "./style.css";')>main.indexOf('import "./vendor/gc-ui/tokens.css";'));
 assert.match(css,/--gc-brand/);
 assert.match(css,/@media\(max-width:740px\)\{\.workspace\{grid-template-columns:minmax\(0,1fr\)/);
 assert.match(css,/\.sidebar\{min-width:0;min-height:auto/);
 assert.match(css,/\.sidebar nav\[aria-label="Views"\]\{display:flex;min-width:0;max-width:100%;overflow-x:auto/);
});
