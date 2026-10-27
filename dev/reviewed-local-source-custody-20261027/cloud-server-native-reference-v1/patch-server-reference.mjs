import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url),acorn=require('/workspace/shared/offmenu-next-i18n/deps/node_modules/acorn');
const hash=b=>createHash('sha256').update(b).digest('hex');
const BASE='13bd5e94c11ded5756a09edafc414791164425f4aca0b12b947849e1af60157a';
const IMPORT='import{validateSourceReferenceStock as _offmenuValidateSourceReferenceStock}from"./source-reference-stock.mjs";\n';
const DISPATCH='if(A?.foundationSourceReference||A?.sourceIdentityReference)return _offmenuValidateSourceReferenceStock(A);';
// Only inserts the helper import and reference-only dispatch. The old validator
// body remains byte-for-byte intact for all other stock. Callers/auth/storage and
// OWN_DATA_REQUIRED containment are neither rebuilt nor rewritten.
export function patchServerReferenceValidator(bytes,{expectedModuleSha256=BASE,expectedValidatorSha256}={}){
 if(!Buffer.isBuffer(bytes)||hash(bytes)!==expectedModuleSha256)throw Error('Module preimage mismatch.');
 const source=bytes.toString('utf8');if(!Buffer.from(source).equals(bytes))throw Error('Lossy module encoding.');
 if(source.includes('_offmenuValidateSourceReferenceStock'))throw Error('Server reference dispatch already present.');
 const ast=acorn.parse(source,{ecmaVersion:'latest',sourceType:'module'}),matches=ast.body.filter(n=>n.type==='FunctionDeclaration'&&n.id.name==='W');
 if(matches.length!==1)throw Error('Expected sole top-level stock validator.');
 const node=matches[0];if(node.params.length!==1||node.params[0].name!=='A')throw Error('Stock validator signature changed.');
 const before=source.slice(node.start,node.end),beforeSha256=hash(Buffer.from(before));
 if(expectedValidatorSha256&&beforeSha256!==expectedValidatorSha256)throw Error('Stock validator preimage mismatch.');
 if(!before.startsWith('function W(A){let I={id:String(A.id||crypto.randomUUID())')||before.includes('sourceIdentityReference')||before.includes('foundationSourceReference'))throw Error('Unexpected stock validator semantics.');
 const offset=node.body.start+1,output=IMPORT+source.slice(0,offset)+DISPATCH+source.slice(offset);
 if(output.slice(IMPORT.length,IMPORT.length+offset)+output.slice(IMPORT.length+offset+DISPATCH.length)!==source)throw Error('Non-dispatch server bytes changed.');
 acorn.parse(output,{ecmaVersion:'latest',sourceType:'module'});
 return {bytes:Buffer.from(output),receipt:{schema:'offmenu-server-stock-reference-dispatch/1',before:{bytes:bytes.length,sha256:hash(bytes)},after:{bytes:Buffer.byteLength(output),sha256:hash(Buffer.from(output))},validator:{name:'W',beforeBytes:Buffer.byteLength(before),beforeSha256,insertOffset:offset,insertText:DISPATCH},importText:IMPORT,unchangedOutsideInsertions:true,unchanged:['legacy validator body','state validator CA','private/shared save and load handlers','authentication','origin/revision checks','OWN_DATA_REQUIRED containment'],newModule:'source-reference-stock.mjs'}};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const [input,output,expected=BASE,validator]=process.argv.slice(2);if(!input||!output)throw Error('input and output paths required');const result=patchServerReferenceValidator(await readFile(input),{expectedModuleSha256:expected,expectedValidatorSha256:validator});await writeFile(output,result.bytes);await writeFile(output+'.server-dispatch.json',JSON.stringify(result.receipt,null,2)+'\n');console.log(JSON.stringify(result.receipt));}
