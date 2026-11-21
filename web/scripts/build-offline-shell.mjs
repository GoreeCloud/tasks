import {createHash} from "node:crypto";
import {readFile,readdir,writeFile} from "node:fs/promises";
import {join,resolve} from "node:path";
import {fileURLToPath} from "node:url";

const prefix="goreecloud-tasks-public-shell-";
const allowed=/^[A-Za-z0-9][A-Za-z0-9._-]*\.(?:js|css|png|svg|webp|woff2)$/;
export async function buildOfflineShell(distDir) {
  const index=await readFile(join(distDir,"index.html"),"utf8");
  if(!index.includes('id="root"'))throw new Error("Unrecognized public app index");
  const files=await readdir(join(distDir,"assets"),{withFileTypes:true});
  const assets=files.filter(f=>f.isFile()&&allowed.test(f.name))
    .map(f=>"/assets/"+f.name).sort();
  if(!assets.some(name=>name.endsWith(".js"))||
     !assets.some(name=>name.endsWith(".css"))) {
    throw new Error("Built app shell needs bundled JS and CSS assets");
  }
  const paths=["/index.html",...assets];
  if(paths.some(path=>path.startsWith("/api/")||path.includes("?")))
    throw new Error("Private/credential-bearing cache entry prohibited");
  const digest=createHash("sha256").update(index).update(paths.join("\n")).digest("hex").slice(0,16);
  const cacheName=prefix+digest;
  const template=await readFile(fileURLToPath(new URL("./offline-sw-template.js",import.meta.url)),"utf8");
  const worker=template.replace("__CACHE_NAME__",JSON.stringify(cacheName))
    .replace("__PRECACHE_ASSETS__",JSON.stringify(paths));
  if(worker.includes("__CACHE_NAME__")||worker.includes("__PRECACHE_ASSETS__"))
    throw new Error("Offline worker template injection failed");
  await writeFile(join(distDir,"offline-sw.js"),worker,"utf8");
  return {cacheName,paths};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const manifest=await buildOfflineShell(resolve(process.cwd(),"dist"));
  process.stdout.write("Generated opt-in public app shell with "+manifest.paths.length+" static URLs\n");
}
