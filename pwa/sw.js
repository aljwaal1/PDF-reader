const CACHE='pdf-reader-pwa-v16';
const CACHE_PREFIX='pdf-reader-pwa-';
const ASSETS=['./','index.html','manifest.json','icon.svg'];

async function clearOldCaches(){
  const keys=await caches.keys();
  await Promise.all(keys.filter(k=>k.startsWith(CACHE_PREFIX)&&k!==CACHE).map(k=>caches.delete(k)));
}

async function clearAllPwaCaches(){
  const keys=await caches.keys();
  await Promise.all(keys.filter(k=>k.startsWith(CACHE_PREFIX)).map(k=>caches.delete(k)));
}

self.addEventListener('install',e=>{
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));
});

self.addEventListener('activate',e=>{
  e.waitUntil((async()=>{
    await clearOldCaches();
    await self.clients.claim();
  })());
});

self.addEventListener('message',e=>{
  if(e.data?.type==='CLEAR_PWA_CACHE'){
    e.waitUntil((async()=>{
      await clearAllPwaCaches();
      await caches.open(CACHE).then(c=>c.addAll(ASSETS));
      const clients=await self.clients.matchAll({type:'window',includeUncontrolled:true});
      for(const client of clients) client.postMessage({type:'PWA_CACHE_CLEARED'});
    })());
  }
});

self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  const sameOrigin=u.origin===location.origin;

  e.respondWith((async()=>{
    try{
      // Always ask the network for the newest local PWA shell instead of
      // allowing Safari/Chrome HTTP cache to keep an older index/service file.
      const request=sameOrigin?new Request(e.request,{cache:'no-store'}):e.request;
      const resp=await fetch(request);
      if(sameOrigin&&resp.ok){
        const copy=resp.clone();
        caches.open(CACHE).then(c=>c.put(e.request,copy));
      }
      return resp;
    }catch{
      return (await caches.match(e.request))||(await caches.match('./'));
    }
  })());
});