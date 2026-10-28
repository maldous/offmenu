const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict'),acorn=require('../offmenu-production-fourfix195-20261029/toolchain/node_modules/acorn');
const root=__dirname,sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const pins=JSON.parse(fs.readFileSync(root+'/accepted-build-pins.json','utf8'));
const base=fs.readFileSync(root+'/../offmenu-production-shopping197-20261029/deployed-application.mjs','utf8');
assert.equal(sha(base),'08f5ae17eec6b5bede7c746391952cd3f8190507c7ebccd6abb6cb0c66d3d4a4');
const app=fs.readFileSync(root+'/'+pins.app.path,'utf8'),helper=fs.readFileSync(root+'/'+pins.helper.path,'utf8');
assert.equal(sha(app),pins.app.sha256);assert.equal(sha(helper),pins.helper.sha256);
assert(!base.includes('__offmenuCookingWitness198'));assert(helper.includes('__offmenuCookingWitness198'));
const ast=acorn.parse(base,{ecmaVersion:'latest',sourceType:'module'}),edits=[];
for(const name of ['lg','CA','SA']){
 const n=ast.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);assert(n);const before=base.slice(n.start,n.end);let after;
 if(name==='lg'){assert(before.endsWith('return I}'));after=before.slice(0,-9)+'return __offmenuCookingWitness198.preserveCookingWitnesses(A,I)}';}
 if(name==='CA'){const old='return Object.assign(E,lg(g)),{inventory:I,products:Q,recipes:TA(A.recipes||[]),profile:E,selections:B}';assert.equal(before.split(old).length-1,1);after=before.replace(old,'return Object.assign(E,lg(g)),__offmenuCookingWitness198.finishCookingWitnessState(A,{inventory:I,products:Q,recipes:TA(A.recipes||[]),profile:E,selections:B})');}
 if(name==='SA'){const old='batches:(I.batches||[]).map(g=>({...g,events:';assert.equal(before.split(old).length-1,1);after=before.replace(old,'batches:(I.batches||[]).map(g=>({...__offmenuCookingWitness198.sharedCookingBatch(g),events:');}
 fs.writeFileSync(root+'/server-'+name+'-after.js',after);
 edits.push({start:n.start,end:n.end,before,after,kind:'server-'+name});
}
let assets=[];for(const n of ast.body)if(n.type==='VariableDeclaration')for(const d of n.declarations)if(d.init?.type==='ObjectExpression')for(const p of d.init.properties)if((p.key.value??p.key.name)==='app.js')assets.push(p.value);
assert.equal(assets.length,1);const a=assets[0];assert.equal(sha(a.value),'8baa2f039eacbe6abcabed5df59ec7a18c1981901a789045e2ad41133e627814');
edits.push({start:a.start,end:a.end,before:base.slice(a.start,a.end),after:JSON.stringify(app),kind:'embedded-app'});
let out=base;for(const e of edits.sort((a,b)=>b.start-a.start)){assert.equal(out.slice(e.start,e.end),e.before);out=out.slice(0,e.start)+e.after+out.slice(e.end);}
out=helper+'\n'+out;acorn.parse(out,{ecmaVersion:'latest',sourceType:'module'});
let reversed=out.slice(helper.length+1);for(const e of edits){assert.equal(reversed.split(e.after).length-1,1);reversed=reversed.replace(e.after,()=>e.before);}assert.equal(reversed,base);
fs.writeFileSync(root+'/deployed-application.mjs',out);
const receipt={baseSha256:sha(base),candidateSha256:sha(out),candidateBytes:Buffer.byteLength(out),appSha256:sha(app),appBytes:Buffer.byteLength(app),helperSha256:sha(helper),exactReverseReconstructsPreimage:true,changedSeams:edits.map(x=>x.kind),otherServerAndAssetBytesPreserved:true};
fs.writeFileSync(root+'/splice-receipt.json',JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt));
