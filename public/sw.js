const CACHE='offmenu-shell-v9-research';
const FILES=['/','/app.js?v=research-2','/scanner-worker.js','/scanner.wasm','/style.css?v=research-2','/recipes.json?v=research-2','/data-workspace.html','/data-workspace.js?v=global-2','/afcd-nutrient-details.json','/icon.svg','/manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('offmenu-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const url=new URL(e.request.url);if(e.request.method!=='GET'||url.origin!==self.location.origin||(url.pathname.startsWith('/api/')||url.pathname.startsWith('/.netlify/')))return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request).then(r=>r||new Response('Offline resource unavailable',{status:503}))));});
