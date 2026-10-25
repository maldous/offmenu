import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraCrop} from '../public/scanner-ui.js';

test('visible cover guide maps to the same source rectangle for native and fallback decoders',()=>{
 const frame={left:0,top:0,width:400,height:800};
 const guide={left:20,top:120,width:360,height:520};
 const crop=cameraCrop(1920,1080,frame,guide);
 assert.deepEqual(crop,{sx:717,sy:162,sw:486,sh:702});
});

test('mirrored and rotated preview uses its visible source region',()=>{
 const frame={left:0,top:0,width:800,height:400};
 const guide={left:20,top:40,width:440,height:300};
 const plain=cameraCrop(1920,1080,frame,guide);
 const mirror=cameraCrop(1920,1080,frame,guide,{mirror:true});
 const rotated=cameraCrop(1920,1080,frame,guide,{rotate:true});
 assert.equal(mirror.sx,1920-plain.sx-plain.sw);
 assert.equal(rotated.sx,mirror.sx);
 assert.equal(rotated.sy,1080-plain.sy-plain.sh);
});

test('an invisible or obscured aiming guide cannot silently decode the whole frame',()=>{
 assert.equal(cameraCrop(1920,1080,{left:0,top:0,width:400,height:800},{left:500,top:0,width:100,height:100}),null);
 assert.equal(cameraCrop(0,1080,{left:0,top:0,width:400,height:800},{left:0,top:0,width:300,height:400}),null);
});

test('object-fit contain clips the guide to visible video pixels instead of letterboxing',()=>{
 const frame={left:0,top:0,width:400,height:400};
 const guide={left:40,top:20,width:320,height:360};
 const crop=cameraCrop(1920,1080,frame,guide,{fit:'contain'});
 assert.deepEqual(crop,{sx:192,sy:0,sw:1536,sh:1080});
 assert.equal(cameraCrop(1920,1080,frame,{left:40,top:0,width:320,height:70},{fit:'contain'}),null);
});
