import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url),acorn=require('/workspace/shared/offmenu-next-i18n/deps/node_modules/acorn');
const hash=b=>createHash('sha256').update(b).digest('hex');
const IMPORT='import{ownedFoundationResponse as _offmenuOwnedFoundationResponse}from"./owned-foundation-response.mjs";\n';
export function patchOwnedFoundationRoute(bytes,{expectedModuleSha256}={}){
 if(!Buffer.isBuffer(bytes)||hash(bytes)!==expectedModuleSha256)throw Error('Exact application preimage required.');
 const source=bytes.toString('utf8');if(!Buffer.from(source).equals(bytes)||source.includes('_offmenuOwnedFoundationResponse'))throw Error('Application encoding or duplicate route mismatch.');
 const ast=acorn.parse(source,{ecmaVersion:'latest',sourceType:'module'}),exports=ast.body.filter(n=>n.type==='ExportNamedDeclaration'&&n.specifiers.some(s=>s.exported.name==='default'));
 if(exports.length!==1||exports[0].specifiers.length!==1||exports[0].source)throw Error('Expected single existing default export.');
 const node=exports[0],name=node.specifiers[0].local.name;const replacement='const _offmenuOwnedFoundationApplication={...'+name+',async fetch(request,env,context){const own=await _offmenuOwnedFoundationResponse(request);return own??'+name+'.fetch(request,env,context);}};export{_offmenuOwnedFoundationApplication as default};';
 const output=IMPORT+source.slice(0,node.start)+replacement+source.slice(node.end);
 if(output.slice(IMPORT.length,IMPORT.length+node.start)+source.slice(node.start,node.end)+output.slice(IMPORT.length+node.start+replacement.length)!==source)throw Error('Unrelated handler bytes changed.');
 acorn.parse(output,{ecmaVersion:'latest',sourceType:'module'});
 return {bytes:Buffer.from(output),receipt:{schema:'offmenu-owned-foundation-route-composition/1',before:{bytes:bytes.length,sha256:hash(bytes)},after:{bytes:Buffer.byteLength(output),sha256:hash(Buffer.from(output))},defaultExport:{previousName:name,previousText:source.slice(node.start,node.end),replacement},addedImport:IMPORT,unchangedOutsideImportAndDefaultWrapper:true,onlyNewRoutes:['/api/corpus/foundation','/api/corpus/foundation/notices','/api/corpus/foundation/release'],existingHandlersRetained:true,externalProviderFallbackAdded:false}};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const[input,output,expectedModuleSha256]=process.argv.slice(2);const result=patchOwnedFoundationRoute(await readFile(input),{expectedModuleSha256});await writeFile(output,result.bytes);await writeFile(output+'.owned-foundation-route.json',JSON.stringify(result.receipt,null,2)+'\n');console.log(JSON.stringify(result.receipt));}
