/* NumiRealm service worker: offline play after the first visit.
   The cache name follows APP_VERSION (passed as ?v= when registering), so every release gets a fresh cache.
   all pages are network-first so new releases arrive at once; version.json is never cached, so auto-update keeps working. */
const V=new URL(self.location).searchParams.get('v')||'0';
const CACHE='numirealm-v'+V;
const SHELL=['./','./index.html','./nr-offline.js','./fonts/baloo2-latin-600-800.woff2','./fonts/poppins-latin-400.woff2','./fonts/poppins-latin-500.woff2','./fonts/poppins-latin-600.woff2','./fonts/poppins-latin-700.woff2','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png','./icons/icon-maskable-512.png','./icons/apple-touch-icon-180.png']; // v22: self-hosted fonts precached for offline play
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>Promise.all(SHELL.map(u=>fetch(u,{cache:'reload'}).then(r=>r.ok?c.put(u,r):null).catch(()=>null)))).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('numirealm-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('message',e=>{if(e.data==='skipWaiting')self.skipWaiting();});
/* v29: every HTML page and version.json is network-first (no HTTP cache). Only the game page (./ or index.html) is kept for offline play,
   under its own key, so gamenight.html or a parent page can never be stored as index.html. Parent pages, vendor/ and sw.js are never cached. */
self.addEventListener('fetch',e=>{const req=e.request;if(req.method!=='GET')return;const u=new URL(req.url);if(u.origin!==self.location.origin)return;
 if(/\/version\.json$/.test(u.pathname)||/\/sw\.js$/.test(u.pathname))return;
 if(/\/parent[^/]*\.html$/.test(u.pathname)||/\/vendor\//.test(u.pathname))return;
 const isGame=/\/(index\.html)?$/.test(u.pathname);
 const isHtml=req.mode==='navigate'||/\.html$/.test(u.pathname)||isGame;
 if(isHtml){
  if(!isGame){e.respondWith(fetch(req,{cache:'no-store'}).catch(()=>caches.match('./index.html')));return;}
  e.respondWith(fetch(u.pathname,{cache:'no-store'}).then(r=>{if(r&&r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put('./index.html',cp));}return r;})
   .catch(()=>caches.match('./index.html',{ignoreSearch:true}).then(r=>r||caches.match('./',{ignoreSearch:true}))));return;}
 e.respondWith(caches.match(req,{ignoreSearch:true}).then(r=>r||fetch(req).then(n=>{if(n&&n.ok&&n.type==='basic'){const cp=n.clone();caches.open(CACHE).then(c=>c.put(req,cp));}return n;})));});
