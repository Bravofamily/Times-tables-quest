/* NumiRealm service worker: offline play after the first visit.
   The cache name follows APP_VERSION (passed as ?v= when registering), so every release gets a fresh cache.
   index.html is network-first so new releases arrive at once; version.json is never cached, so auto-update keeps working. */
const V=new URL(self.location).searchParams.get('v')||'0';
const CACHE='numirealm-v'+V;
const SHELL=['./','./index.html','./fonts/baloo2-latin-600-800.woff2','./fonts/poppins-latin-400.woff2','./fonts/poppins-latin-500.woff2','./fonts/poppins-latin-600.woff2','./fonts/poppins-latin-700.woff2']; // v22: self-hosted fonts precached for offline play
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>Promise.all(SHELL.map(u=>fetch(u,{cache:'reload'}).then(r=>r.ok?c.put(u,r):null).catch(()=>null)))).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('numirealm-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const req=e.request;if(req.method!=='GET')return;const u=new URL(req.url);if(u.origin!==self.location.origin)return;
 if(/\/version\.json$/.test(u.pathname)||/\/sw\.js$/.test(u.pathname))return; // straight to the network, never cached
 const isPage=req.mode==='navigate'||/\/(index\.html)?$/.test(u.pathname);
 if(isPage){e.respondWith(fetch(u.pathname,{cache:'no-cache'}).then(r=>{if(r&&r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put('./index.html',cp));}return r;})
  .catch(()=>caches.match('./index.html',{ignoreSearch:true}).then(r=>r||caches.match('./',{ignoreSearch:true}))));return;}
 e.respondWith(caches.match(req,{ignoreSearch:true}).then(r=>r||fetch(req).then(n=>{if(n&&n.ok&&n.type==='basic'){const cp=n.clone();caches.open(CACHE).then(c=>c.put(req,cp));}return n;})));});
