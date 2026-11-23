import {isPublicCatalogueHeld,PUBLIC_CATALOGUE_UNAVAILABLE} from './public-catalogue-boundary.js';
import {supportedLocale} from './locale-negotiation.js';
import {OFFLINE_RESOURCE_UNAVAILABLE_AR} from './locales/offline.js';
const CACHE='offmenu-shell-v15';
// Fixed asset URLs, not entries in the UI language catalogue.
const HELP_FILES=[`/help.html`,`/help.css`,`/help.js`];
const FILES=['/','/app.js?v=i18n-1','/scanner-worker.js','/scanner-theme-init.js','/scanner.wasm','/style.css?v=i18n-1','/offmenu-tokens.css','/data-workspace.html','/data-workspace.js?v=i18n-1','/icon.svg','/receipt-bars.svg','/manifest.webmanifest','/manifest-ar.webmanifest','/offmenu-neon.css','/offmenu-neon.svg','/offmenu-neon-material.jpg',...HELP_FILES];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('offmenu-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
function offlineAsset(request,path){
 // A stale Help page in an unrelated cache must not hide a new topic.
 const options={ignoreSearch:true};
 return HELP_FILES.includes(path)?caches.open(CACHE).then(cache=>cache.match(request,options)):caches.match(request,options);
}
function offlineMessage(url,request){
 const preferred=[url.searchParams.get('uiLanguage'),...(request.headers.get('Accept-Language')||'en').split(',').map(value=>value.split(';')[0].trim())];
 return preferred.map(supportedLocale).find(Boolean)==='ar'
   ? OFFLINE_RESOURCE_UNAVAILABLE_AR : 'Offline resource unavailable';
}
self.addEventListener('fetch',e=>{const url=new URL(e.request.url);if(e.request.method!=='GET'||url.origin!==self.location.origin)return;if(isPublicCatalogueHeld(url.pathname)){e.respondWith(new Response(JSON.stringify({code:PUBLIC_CATALOGUE_UNAVAILABLE,error:'Public catalogue unavailable.'}),{status:503,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}}));return;}if((url.pathname.startsWith('/api/')||url.pathname.startsWith('/.netlify/')||url.pathname.startsWith('/oauth/')||url.pathname.startsWith('/.well-known/')||url.pathname==='/mcp'||url.pathname==='/openapi.json'))return;e.respondWith(fetch(e.request).catch(()=>offlineAsset(e.request,url.pathname).then(r=>r||new Response(offlineMessage(url,e.request),{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}}))));});
