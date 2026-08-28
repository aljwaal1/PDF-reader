const CACHE='pdf-reader-pwa-v12';
const ASSETS=['./','index.html','manifest.json','icon.svg','reader-fix.js'];
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  if(e.request.mode==='navigate'&&u.origin===location.origin){
    e.respondWith(fetch(e.request).then(async resp=>{
      const html=await resp.text();
      const injected=html.includes('reader-fix.js')?html:html.replace('</body>','<script src="reader-fix.js" defer></script></body>');
      const out=new Response(injected,{status:resp.status,statusText:resp.statusText,headers:{'content-type':'text/html; charset=utf-8'}});
      caches.open(CACHE).then(c=>c.put(e.request,out.clone()));
      return out;
    }).catch(()=>caches.match(e.request).then(async r=>{
      if(!r)return caches.match('./');
      const html=await r.text();
      const injected=html.includes('reader-fix.js')?html:html.replace('</body>','<script src="reader-fix.js" defer></script></body>');
      return new Response(injected,{headers:{'content-type':'text/html; charset=utf-8'}});
    })));
    return;
  }
  e.respondWith(fetch(e.request).then(resp=>{if(u.origin===location.origin){const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}return resp}).catch(()=>caches.match(e.request).then(r=>r||caches.match('./'))));
});