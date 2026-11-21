"use strict";
// Cache only immutable, publicly built static assets plus the static app index.
// This worker never intercepts API requests or credential-bearing requests.
const CACHE_NAME=__CACHE_NAME__;
const CACHE_PREFIX="goreecloud-tasks-public-shell-";
const PRECACHE=__PRECACHE_ASSETS__;
const ALLOWED=new Set(PRECACHE);
self.addEventListener("install", function(event){
  event.waitUntil(caches.open(CACHE_NAME).then(function(cache){
    return cache.addAll(PRECACHE);
  }).then(function(){return self.skipWaiting();}));
});
self.addEventListener("activate", function(event){
  event.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(key){
      return key.startsWith(CACHE_PREFIX)&&key!==CACHE_NAME;
    }).map(function(key){return caches.delete(key);}));
  }).then(function(){return self.clients.claim();}));
});
self.addEventListener("fetch",function(event){
  const request=event.request;
  if(request.method!=="GET"||request.headers.has("Authorization"))return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin||url.pathname.startsWith("/api/")||
     url.search!=="")return;
  if(request.mode==="navigate"&&(url.pathname==="/"||url.pathname==="/index.html")){
    event.respondWith(fetch(request).catch(function(){
      return caches.match("/index.html");
    }));
    return;
  }
  if(ALLOWED.has(url.pathname)){
    event.respondWith(caches.match(url.pathname).then(function(hit){
      return hit||fetch(request);
    }));
  }
});
