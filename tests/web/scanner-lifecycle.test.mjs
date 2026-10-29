import test from 'node:test';
import assert from 'node:assert/strict';
import {setupScanner} from '../../apps/web/src/scanner-ui.js';
import {NATIVE_FORMATS} from '../../apps/web/src/scanner-model.js';
function environment(getUserMedia){
 const elements=new Map();
 class Element {
  constructor(){this.hidden=false;this.disabled=false;this.value='';this.options=[];this.style={};this.readyState=0;this.currentTime=0;this.videoWidth=1920;this.videoHeight=1080;this.classList={add(){},remove(){}};this.attributes={};}
  getContext(){return {drawImage(){},getImageData:(_x,_y,width,height)=>({data:new Uint8ClampedArray(width*height*4),width,height})};}
  getBoundingClientRect(){return this.rect||{left:0,top:0,width:400,height:225};}
  querySelector(selector){return selector==='.scanner-guide'?$('legacy-guide'):null;}
  play(){return Promise.resolve();} add(o){this.options.push(o);} replaceChildren(...c){this.options=c;} setAttribute(k,v){this.attributes[k]=v;}
 }
 const listeners={};
 const $=id=>{if(id==='capture-guide')return null;if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 Object.defineProperty(globalThis,'navigator',{configurable:true,value:{mediaDevices:{getUserMedia,enumerateDevices:async()=>[]}}});
 globalThis.window={isSecureContext:true,addEventListener(){}};
 globalThis.document={getElementById:$,createElement:()=>new Element(),addEventListener:(name,cb)=>listeners[name]=cb};
 globalThis.localStorage={getItem:()=>null,setItem(){}};
 globalThis.Option=class {constructor(label,value){this.label=label;this.value=value;}};
 globalThis.getComputedStyle=()=>({objectFit:'contain'});
 return {$,listeners};
}
function camera(){const track={readyState:'live',stopped:false,stop(){this.stopped=true;},addEventListener(){},getCapabilities:()=>({}),getSettings:()=>({width:1280,height:720})};return {track,getTracks:()=>[track],getVideoTracks:()=>[track]};}
test('stop during permission prompt closes late stream and never starts capture',async()=>{
 let resolve;const e=environment(()=>new Promise(r=>resolve=r));let current=null;
 const scanner=setupScanner({canScan:()=>true,onCode(){},onStream:s=>current=s});
 const starting=scanner.start();scanner.stop();const c=camera();resolve(c);await starting;
 assert.ok(c.track.stopped);assert.equal(current,null);assert.equal(e.$('video').srcObject,null);assert.equal(e.$('scan').disabled,false);
});
test('unsupported focus/torch/zoom remain hidden and visibility loss releases the camera',async()=>{
 const c=camera();const e=environment(async()=>c);let current=null;
 const scanner=setupScanner({canScan:()=>true,onCode(){},onStream:s=>current=s});await scanner.start();
 assert.equal(current,c);for(const id of ['scanner-focus-row','scanner-zoom-row','scanner-torch'])assert.ok(e.$(id).hidden,id);
 document.hidden=true;e.listeners.visibilitychange();assert.ok(c.track.stopped);assert.equal(current,null);assert.equal(e.$('scan').disabled,false);
});
test('permission denial is explained without repeated permission requests',async()=>{
 let calls=0;const e=environment(async()=>{calls++;throw {name:'NotAllowedError'};});
 const scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});await scanner.start();assert.equal(calls,1);assert.match(e.$('scanner-status').textContent,/permission is blocked/);assert.equal(e.$('scan').disabled,false);
});
test('changing setup cancels an old camera request without leaking either stream',async()=>{
 const requests=[];const e=environment(()=>new Promise(resolve=>requests.push(resolve)));
 const scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});
 const one=scanner.start();e.$('scanner-mode').value='bench';e.$('scanner-mode').onchange();
 const c1=camera(),c2=camera();requests[0](c1);requests[1](c2);await one;await new Promise(r=>setTimeout(r,0));
 assert.ok(c1.track.stopped);assert.equal(e.$('video').srcObject,c2);assert.match(e.$('video').style.transform,/scaleX\(-1\)/);scanner.stop();assert.ok(c2.track.stopped);
});

test('new phones prefer rear handheld mode and saved camera choice is retained',async()=>{
 const constraints=[];const e=environment(async options=>{constraints.push(options);return camera();});
 let scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});
 assert.equal(e.$('scanner-mode').value,'handheld');await scanner.start();
 assert.equal(constraints[0].video.facingMode.ideal,'environment');scanner.stop();
 globalThis.localStorage.getItem=()=>JSON.stringify({mode:'stand',camera:'environment',mirror:false});
 scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});await scanner.start();
 assert.equal(e.$('scanner-mode').value,'stand');assert.equal(constraints[1].video.facingMode.ideal,'environment');scanner.stop();
});

test('denied checkout permission opens neither camera nor photo decoder',async()=>{
 let requests=0,accepted=0;const e=environment(async()=>{requests++;return camera();});
 const scanner=setupScanner({canScan:()=>false,onCode(){accepted++;},onStream(){}});
 await scanner.start();e.$('scanner-photo').files=[{size:100}];await e.$('scanner-photo').onchange();
 assert.equal(requests,0);assert.equal(accepted,0);assert.equal(e.$('scanner-photo').value,'');
});

test('explicit preference storage is isolated from global storage and retains current localization',()=>{
 const e=environment(async()=>camera());const writes=[];
 const storage={getItem:key=>{assert.equal(key,'offmenu-scanner-v2');return JSON.stringify({mode:'stand',camera:'environment',mirror:false});},setItem:(...args)=>writes.push(args)};
 Object.defineProperty(globalThis,'localStorage',{configurable:true,get(){throw Error('Global storage denied');}});
 try{
 const scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){},storage});
 assert.equal(e.$('scanner-mode').value,'stand');e.$('scanner-mode').value='bench';e.$('scanner-mode').onchange();
 assert.equal(writes.length,1);assert.equal(JSON.parse(writes[0][1]).camera,'user');scanner.stop();
 }finally{Object.defineProperty(globalThis,'localStorage',{configurable:true,writable:true,value:{getItem:()=>null,setItem(){}}});}
});
test('blocked default storage remains optional and never prevents scanner setup',()=>{
 const e=environment(async()=>camera());Object.defineProperty(globalThis,'localStorage',{configurable:true,get(){throw Error('Global storage denied');}});
 try{
 const scanner=setupScanner({canScan:()=>false,onCode(){},onStream(){}});
 assert.equal(e.$('scanner-mode').value,'handheld');e.$('scanner-mode').onchange();scanner.stop();
 }finally{Object.defineProperty(globalThis,'localStorage',{configurable:true,writable:true,value:{getItem:()=>null,setItem(){}}});}
});
test('the real kitchen caller uses its scanner-guide and visible contain geometry',async()=>{
 const c=camera(),e=environment(async()=>c);let seen=null;
 e.$('legacy-guide').rect={left:40,top:20,width:320,height:180};
 e.$('video').readyState=2;e.$('video').currentTime=1;
 class Detector{static async getSupportedFormats(){return NATIVE_FORMATS;}async detect(canvas){seen={width:canvas.width,height:canvas.height};return [];}}
 globalThis.BarcodeDetector=Detector;window.BarcodeDetector=Detector;
 const scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});
 await scanner.start();
 await new Promise(resolve=>setTimeout(resolve,20));
 scanner.stop();delete globalThis.BarcodeDetector;
 assert.deepEqual(seen,{width:1536,height:864});
});
