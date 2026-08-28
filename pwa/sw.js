const CACHE='pdf-reader-pwa-v15';
const ASSETS=['./','index.html','manifest.json','icon.svg'];
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const u=new URL(e.request.url);e.respondWith(fetch(e.request).then(resp=>{if(u.origin===location.origin){const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}return resp}).catch(()=>caches.match(e.request).then(r=>r||caches.match('./'))))});