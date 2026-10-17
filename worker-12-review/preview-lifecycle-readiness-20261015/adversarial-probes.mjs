// Unique reviewer runner. No producer module/API is assumed until an exact new pin arrives.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';import {pathToFileURL} from 'node:url';import path from 'node:path';import assert from 'node:assert/strict';
const hash=b=>createHash('sha256').update(b).digest('hex');
const root=path.dirname(new URL(import.meta.url).pathname);
const matrix=JSON.parse(readFileSync(path.join(root,'probe-matrix.json')));
const args=process.argv.slice(2);
if(args.length===1&&args[0]==='--check-shape'){
 assert.equal(matrix.cases.length,20);assert.equal(new Set(matrix.cases.map(c=>c.id)).size,20);
 assert.equal(matrix.cases.filter(c=>c.positive).length,2);
 for(const c of matrix.cases){assert.ok(c.pages.length);assert.ok(['lifecycle','transport'].includes(c.kind));if(!c.positive){assert.ok(Array.isArray(c.mutation.path));assert.ok(Object.hasOwn(c.mutation,'value')||Array.isArray(c.mutation.valueFrom));}}
 console.log(JSON.stringify({status:'ASSIGNED-WAITING',matrixShapeValidated:true,stagedCases:20,producerTestsExecuted:0,reason:'Exact new05 source pin/receipts and read-only driver binding absent'}));
}else{
 // selection and fixture artifacts are small JSON; exact hashes must be selected independently.
 assert.equal(args.length,4,'Usage: node adversarial-probes.mjs SELECTION.json FIXTURE.json DRIVER.mjs RESULT.json');
 assert.ok(Object.keys(process.env).every(k=>!k.startsWith('GIT_')),'Strip every inherited GIT_* before executing a reviewed driver');
 const [selectionPath,fixturePath,driverPath,resultPath]=args;const selection=JSON.parse(readFileSync(selectionPath));
 assert.equal(selection.schema,'worker12-new05-reviewed-selection/1');assert.match(selection.sourcePin,/^[a-f0-9]{40}$/);assert.notEqual(selection.sourcePin,'434b56c0200671debfceb03f7aed0889509c51be','Do not repeat old accepted review');
 const fBytes=readFileSync(fixturePath),dBytes=readFileSync(driverPath);assert.ok(fBytes.length<=1048576&&dBytes.length<=65536,'Bounded reviewer fixtures/driver');assert.equal(hash(fBytes),selection.fixtureSHA256);assert.equal(hash(dBytes),selection.driverSHA256);
 const fixtures=JSON.parse(fBytes);assert.equal(fixtures.sourcePin,selection.sourcePin);
 assert.ok(Array.isArray(selection.kinds)&&selection.kinds.length>0&&selection.kinds.every(k=>['lifecycle','transport'].includes(k)),'Select only the dependency lanes actually ready');
 const selectedCases=matrix.cases.filter(c=>selection.kinds.includes(c.kind));const pendingKinds=['lifecycle','transport'].filter(k=>!selection.kinds.includes(k));
 const driver=await import(pathToFileURL(path.resolve(driverPath)));assert.equal(typeof driver.inspectCase,'function');
 const results=[];for(const c of selectedCases){const fixture=structuredClone(fixtures[c.kind]);assert.ok(fixture,'Missing genuine positive-control fixture');if(c.mutation){let at=fixture;for(const k of c.mutation.path.slice(0,-1)){assert.ok(Object.hasOwn(at,k),'Driver fixture must normalize genuine source fields');at=at[k];}let value=c.mutation.value;if(c.mutation.valueFrom){value=fixture;for(const k of c.mutation.valueFrom)value=value[k];}at[c.mutation.path.at(-1)]=structuredClone(value);}
 const observation=await driver.inspectCase({caseId:c.id,kind:c.kind,fixture,selection});assert.equal(typeof observation.admitted,'boolean');assert.equal(observation.sideEffects,0,'Read-only review driver only');assert.equal(observation.admitted,c.positive,c.id+' acceptance/refusal mismatch');results.push({id:c.id,purpose:c.purpose,admitted:observation.admitted,evidence:observation.evidence});}
 writeFileSync(resultPath,JSON.stringify({sourcePin:selection.sourcePin,fixtureSHA256:selection.fixtureSHA256,driverSHA256:selection.driverSHA256,selectedKinds:selection.kinds,pendingKinds,results,scope:'Independent readonly validation only; owner operations/consumer flows require separate actual evidence'},null,2)+'\n');
}
