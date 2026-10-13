import test from 'node:test';
import assert from 'node:assert/strict';
import {setupScanner} from '../public/scanner-ui.js';
function environment(getUserMedia){
 const elements=new Map();
 class Element {
  constructor(){this.hidden=false;this.disabled=false;this.value='';this.options=[];this.style={};this.readyState=0;this.currentTime=0;this.videoWidth=1920;this.videoHeight=1080;this.classList={add(){},remove(){}};this.attributes={};}
  getContext(){return {drawImage(){}};} play(){return Promise.resolve();} add(o){this.options.push(o);} replaceChildren(...c){this.options=c;} setAttribute(k,v){this.attributes[k]=v;}
 }
 const listeners={};
 const $=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 Object.defineProperty(globalThis,'navigator',{configurable:true,value:{mediaDevices:{getUserMedia,enumerateDevices:async()=>[]}}});
 globalThis.window={isSecureContext:true,addEventListener(){}};
 globalThis.document={getElementById:$,createElement:()=>new Element(),addEventListener:(name,cb)=>listeners[name]=cb};
 globalThis.localStorage={getItem:()=>null,setItem(){}};
 globalThis.Option=class {constructor(label,value){this.label=label;this.value=value;}};
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

test('new devices use front bench mode and saved camera choice is retained',async()=>{
 const constraints=[];const e=environment(async options=>{constraints.push(options);return camera();});
 let scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});
 assert.equal(e.$('scanner-mode').value,'bench');await scanner.start();
 assert.equal(constraints[0].video.facingMode.ideal,'user');scanner.stop();
 globalThis.localStorage.getItem=()=>JSON.stringify({mode:'stand',camera:'environment',mirror:false});
 scanner=setupScanner({canScan:()=>true,onCode(){},onStream(){}});await scanner.start();
 assert.equal(e.$('scanner-mode').value,'stand');assert.equal(constraints[1].video.facingMode.ideal,'environment');scanner.stop();
});
