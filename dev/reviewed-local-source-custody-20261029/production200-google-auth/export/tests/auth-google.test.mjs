import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createAuthPageController, readAuthCallbackFlags} from '../source/auth-controller.mjs';
import {routeIdentityReturn} from '../source/auth-return-bridge.mjs';
const origin='https://offmenu.aldous.info';
const config={schema:'offmenu-auth-page/1',mode:'netlify',origin,identityTransport:'real',synthetic:false,
  emailSignIn:'existing-provider',oauthAvailable:true,nextPath:'/shelf-scanner.html'};
function fixture({cfg={}, callback=null, user=null, session={authenticated:false}, overrides={}, flags={}}={}) {
  const events=[], routes=[], calls=[];
  let currentUser=user, currentSession=session;
  const identity={handleAuthCallback:async()=>callback,getSettings:async()=>({disableSignup:false,providers:{google:true,email:true}}),
    getUser:async()=>currentUser,oauthLogin:async p=>{calls.push(p);throw Object.assign(Error('Redirecting to OAuth provider'),{name:'AuthError'});},
    login:async()=>currentUser,signup:async()=>currentUser,logout:async()=>{},...overrides};
  const controller=createAuthPageController({configuration:async()=>({...config,...cfg}),identityFor:async()=>identity,
    verifySession:async()=>currentSession,navigate:p=>routes.push(p),onState:e=>events.push(e),expectedOrigin:origin,
    callbackState:()=>flags, timeoutMs:30});
  return {controller,events,routes,calls,setSession:s=>currentSession=s,setUser:u=>currentUser=u};
}
test('configured Google dispatches only the existing SDK route; unknown provider refused',async()=>{
  const f=fixture();await f.controller.start();assert.deepEqual(f.events.at(-1).providers,['google']);
  assert.equal(await f.controller.providerSignIn('other'),false);assert.equal(await f.controller.providerSignIn('google'),true);
  assert.deepEqual(f.calls,['google']);assert.equal(f.controller.getState(),'redirecting');assert.deepEqual(f.routes,[]);
});
test('runtime gate, synthetic transport and disabled provider cannot dispatch',async()=>{
  for (const opts of [{cfg:{oauthAvailable:false}},{cfg:{identityTransport:'fixture',synthetic:true}},
    {overrides:{getSettings:async()=>({providers:{google:false}})}}]) {
    const f=fixture(opts);await f.controller.start();assert.equal(await f.controller.providerSignIn('google'),false);assert.deepEqual(f.calls,[]);
  }
});
test('OAuth callback requires callback/current/server user equality and matching mode',async()=>{
  for(const opts of [
    {callback:{type:'oauth',user:{id:'a'}},user:{id:'b'},session:{authenticated:true,userId:'b',mode:'netlify'}},
    {callback:{type:'oauth',user:{id:'a'}},user:{id:'a'},session:{authenticated:true,userId:'b',mode:'netlify'}},
    {callback:{type:'oauth',user:{id:'a'}},user:{id:'a'},session:{authenticated:true,userId:'a',mode:'better-auth'}},
    {callback:{type:'oauth',user:{id:'a'}},user:{id:'a'}},
    {callback:null,user:{id:'a'},session:{authenticated:true,userId:'a',mode:'netlify'}},
    {cfg:{oauthAvailable:false},callback:{type:'oauth',user:{id:'a'}},user:{id:'a'}}]) {
    const f=fixture({...opts,flags:{oauth:true}});await f.controller.start();assert.equal(f.controller.getState(),'unavailable');
    assert.equal(await f.controller.continueToKitchen(),false);assert.deepEqual(f.routes,[]);
  }
});
test('matched callback signs in but navigation re-verifies session and uses fixed destinations',async()=>{
  const f=fixture({callback:{type:'oauth',user:{id:'a'}},user:{id:'a'},session:{authenticated:true,userId:'a',mode:'netlify'},flags:{oauth:true}});
  await f.controller.start();assert.equal(f.controller.getState(),'signed-in');assert.equal(await f.controller.continueToKitchen(),true);
  assert.deepEqual(f.routes,['/kitchen.html']);f.setSession({authenticated:false});
  assert.equal(await f.controller.continueToScanner(),false);assert.deepEqual(f.routes,['/kitchen.html']);
});
test('provider error or wrong origin cannot become a recovered signed-in user',async()=>{
  for(const more of [{flags:{error:true}},{cfg:{origin:'https://other.example'}}]) {
    const f=fixture({...more,user:{id:'a'},session:{authenticated:true,userId:'a',mode:'netlify'}});
    await f.controller.start();assert.equal(f.controller.getState(),'unavailable');assert.deepEqual(f.routes,[]);
  }
});
test('stalled callback and return verification finish within the operation deadline',async()=>{
  const never=()=>new Promise(()=>{});
  const f=fixture({flags:{oauth:true},overrides:{handleAuthCallback:never}});
  await f.controller.start();assert.equal(f.controller.getState(),'unavailable');
  const events=[];const c=createAuthPageController({configuration:async()=>config,identityFor:async()=>({
    handleAuthCallback:async()=>({type:'oauth',user:{id:'a'}}),getUser:async()=>({id:'a'}),getSettings:async()=>({})}),
    verifySession:never,callbackState:()=>({oauth:true}),expectedOrigin:origin,timeoutMs:20,onState:e=>events.push(e)});
  await c.start();assert.equal(c.getState(),'unavailable');assert.equal(events.at(-1).state,'unavailable');
});
test('stalled provider dispatch returns failure without navigating or exposing errors',async()=>{
  const f=fixture({overrides:{oauthLogin:()=>new Promise(()=>{})}});await f.controller.start();
  assert.equal(await f.controller.providerSignIn('google'),false);assert.equal(f.controller.getState(),'ready');assert.deepEqual(f.routes,[]);
});
test('email, signup and signout retain independent verified-session gates',async()=>{
  const f=fixture();await f.controller.start();assert.equal(f.events.at(-1).signupAvailable,true);
  assert.equal(await f.controller.signIn('a@example.test','synthetic'),false);
  f.setUser({id:'a'});f.setSession({authenticated:true,userId:'a',mode:'netlify'});
  assert.equal(await f.controller.signIn('a@example.test','synthetic'),true);
  assert.equal(await f.controller.signOut(),false);assert.equal(f.controller.getState(),'unavailable');
  const g=fixture();await g.controller.start();assert.equal(await g.controller.signUp('a@example.test','synthetic'),true);
  assert.equal(g.controller.getState(),'ready');
});
test('fragment return bridge retains bytes, rejects arbitrary next URLs and handles provider denial',()=>{
  for(const hash of ['#access_token=synthetic%2Bvalue&refresh_token=synthetic','#error=access_denied&error_description=Cancelled',
    '#confirmation_token=synthetic','#email_change_token=synthetic']) {
    const routes=[];const loc={href:origin+'/?next=https://evil.example/'+hash,replace:p=>routes.push(p)};
    assert.equal(routeIdentityReturn(loc),true);assert.deepEqual(routes,['/auth.html'+hash]);
  }
  for(const url of [origin+'/#section',origin+'/auth.html#access_token=synthetic',origin+'/'])
    assert.equal(routeIdentityReturn({href:url,replace:()=>assert.fail('must not redirect')}),false);
  assert.deepEqual(readAuthCallbackFlags({hash:'#access_token=synthetic'}),{oauth:true,error:false});
});
function browser(configOverride={}, callback=false) {
  const timers=[]; const trackedTimeout=(fn,ms)=>{const timer=setTimeout(fn,ms);timers.push(timer);return timer;};
  const elements=new Map(), requests=[], hrefs=[];const storage=new Map();
  function element(id=''){return {id,hidden:true,disabled:false,children:[],value:'',style:{},className:'',textContent:'',
    setAttribute(k,v){this[k]=v;},replaceChildren(){this.children=[];},append(v){this.children.push(v);},addEventListener(){},querySelectorAll(){return [];}};}
  const location={origin,hash:callback ? '#access_token='+Buffer.from('{}').toString('base64url')+'.'+Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600})).toString('base64url')+'.synthetic&refresh_token=synthetic-refresh' : '',pathname:'/auth.html',search:'',assign:p=>hrefs.push(p)};
  Object.defineProperty(location,'href',{get:()=>origin+'/auth.html',set:p=>hrefs.push(p)});
  const document={getElementById:id=>{if(!elements.has(id))elements.set(id,element(id));return elements.get(id);},
    createElement:()=>element()};
  const cookies=new Map();Object.defineProperty(document,'cookie',{get:()=>[...cookies].map(([k,v])=>k+'='+v).join('; '),set:line=>{const pair=line.split(';')[0];const i=pair.indexOf('=');const key=pair.slice(0,i);const value=pair.slice(i+1);if(/Max-Age=0/i.test(line))cookies.delete(key);else cookies.set(key,value);}});
  const fetch=async(url,opts)=>{requests.push({url:String(url),method:opts?.method||'GET'});
    if(String(url).endsWith('/api/auth-page/config'))return new Response(JSON.stringify({...config,...configOverride}),{headers:{'Content-Type':'application/json'}});
    if(String(url).endsWith('/.netlify/identity/settings'))return new Response(JSON.stringify({external:{google:true,email:true},disable_signup:false}),{headers:{'Content-Type':'application/json'}});
    if(callback && String(url).endsWith('/.netlify/identity/user')) return new Response(JSON.stringify({id:'synthetic-user',email:'synthetic@example.test',user_metadata:{},app_metadata:{provider:'google'}}),{headers:{'Content-Type':'application/json'}});
    if(callback && String(url).endsWith('/api/auth-page/session')) return new Response(JSON.stringify({authenticated:true,userId:'synthetic-user',mode:'netlify'}),{headers:{'Content-Type':'application/json'}});
    throw Error('Unexpected network '+url);
  };
  const localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
  const window={location,localStorage,addEventListener(){}};
  const context=vm.createContext({URL,URLSearchParams,Response,AbortSignal,TextDecoder,Uint8Array,fetch,document,location,window,
    localStorage,history:{replaceState(){}},setTimeout:trackedTimeout,clearTimeout,console,atob,btoa});
  return {context,elements,requests,hrefs,cleanup:()=>timers.forEach(clearTimeout)};
}
test('actual candidate bundle discovers Google, renders official branding, dispatches unchanged authorize route',async()=>{
  const f=browser();const code=fs.readFileSync(new URL('../candidate/auth.js',import.meta.url),'utf8');
  vm.runInContext(code,f.context);await vm.runInContext('A.start()',f.context);
  // A.start is started by entrypoint already; drain that actual initialization.
  for(let i=0;i<20 && vm.runInContext('A.getState()',f.context)==='loading';i++) await new Promise(r=>setTimeout(r,0));
  assert.equal(vm.runInContext('A.getState()',f.context),'ready');
  const providers=f.elements.get('auth-providers');assert.equal(providers.hidden,false);assert.equal(providers.children.length,1);
  const button=providers.children[0];assert.equal(button.className,'google-sign-in');assert.equal(button['aria-label'],'Sign in with Google');
  assert.match(button.innerHTML,/alt="Sign in with Google"/);assert.match(button.innerHTML,/data:image\/png;base64,/);
  assert.equal(await button.onclick(),true);assert.equal(f.hrefs.length,1);
  const target=new URL(f.hrefs[0]);assert.equal(target.origin,origin);assert.equal(target.pathname,'/.netlify/identity/authorize');
  assert.equal(target.searchParams.get('provider'),'google');assert.equal(target.searchParams.has('scope'),false);
  assert.equal(f.requests.length,2); // config and existing public settings; no credentials/login call
});
test('actual bundle retains hidden providers under unqualified runtime gate',async()=>{
  const f=browser({oauthAvailable:false});vm.runInContext(fs.readFileSync(new URL('../candidate/auth.js',import.meta.url),'utf8'),f.context);
  for(let i=0;i<20 && vm.runInContext('A.getState()',f.context)==='loading';i++)await new Promise(r=>setTimeout(r,0));
  assert.equal(f.elements.get('auth-providers').hidden,true);assert.equal(f.elements.get('auth-providers').children.length,0);
  assert.equal(f.elements.get('auth-provider-status').hidden,false);assert.deepEqual(f.hrefs,[]);
});

test('actual bundled SDK callback reaches matching server verification before return navigation (synthetic responses)',async t=>{
  const f=browser({},true);t.after(f.cleanup);vm.runInContext(fs.readFileSync(new URL('../candidate/auth.js',import.meta.url),'utf8'),f.context);
  for(let i=0;i<30 && vm.runInContext('A.getState()',f.context)==='loading';i++)await new Promise(r=>setTimeout(r,0));
  assert.equal(vm.runInContext('A.getState()',f.context),'signed-in');
  assert.equal(f.elements.get('continue-kitchen').hidden,false);
  assert.equal(await f.elements.get('continue-kitchen').onclick(),true);
  assert.deepEqual(f.hrefs,['/kitchen.html']);
  assert.ok(f.requests.some(r=>r.url.endsWith('/.netlify/identity/user')));
  assert.equal(f.requests.filter(r=>r.url.endsWith('/api/auth-page/session')).length,2);
});
