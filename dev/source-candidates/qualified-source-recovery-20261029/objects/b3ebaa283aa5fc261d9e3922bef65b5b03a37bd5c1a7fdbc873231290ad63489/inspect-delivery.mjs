// On-demand, read-only immutable source inspection. No scheduler, build or app execution.
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,realpathSync} from 'node:fs';
import {resolve,relative,posix} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const [repoArg,revisionArg,outArg,parserArg] = process.argv.slice(2);
if (!repoArg || !revisionArg || !outArg || !parserArg) throw Error('Supply repository, immutable revision, external output and existing acorn module path');
const repo = realpathSync(repoArg), out = resolve(outArg);
if (!relative(repo,out).startsWith('..')) throw Error('Output must be outside the repository');
const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('GIT_')));
env.GIT_OPTIONAL_LOCKS='0';
const git = (...args) => execFileSync('git',args,{cwd:repo,env,maxBuffer:16*1024*1024,timeout:30000});
const revision = git('rev-parse','--verify',revisionArg+'^{commit}').toString().trim();
const names = git('ls-tree','-r','--name-only',revision).toString().trim().split('\n');
const tracked = new Set(names);
const parserFile=realpathSync(parserArg), {parse} = await import(pathToFileURL(parserFile));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const files=[],errors=[],functionBodies=new Map();
for (const name of names.filter(n => /\.(?:mjs|js)$/.test(n) && !/^(?:tests[^/]*|examples|research)\//.test(n))) {
  const bytes=git('show',revision+':'+name), source=bytes.toString('utf8');
  let tree;
  try {tree=parse(source,{ecmaVersion:'latest',sourceType:'module',locations:true,allowHashBang:true});}
  catch(error) {errors.push({path:name,message:error.message});continue;}
  const imports=[],functions=[],exports=[];
  function walk(node) {
    if(!node || typeof node!=='object')return;
    if(['ImportDeclaration','ExportNamedDeclaration','ExportAllDeclaration'].includes(node.type) && node.source)
      imports.push({specifier:node.source.value,line:node.loc.start.line,kind:node.type});
    if(node.type==='ImportExpression')
      imports.push({specifier:node.source.type==='Literal'?node.source.value:null,line:node.loc.start.line,kind:'dynamic-import'});
    if(node.type==='ExportNamedDeclaration') {
      if(node.declaration?.id)exports.push(node.declaration.id.name);
      for(const d of node.declaration?.declarations||[])if(d.id.type==='Identifier')exports.push(d.id.name);
      for(const s of node.specifiers||[])exports.push(s.exported.name);
    }
    if(node.type==='ExportDefaultDeclaration')exports.push('default');
    if(node.type==='FunctionDeclaration' && node.id) {
      functions.push({name:node.id.name,line:node.loc.start.line});
      const body=source.slice(node.body.start,node.body.end);
      if(body.length>=200) {
        const key=hash(body);if(!functionBodies.has(key))functionBodies.set(key,[]);
        functionBodies.get(key).push({path:name,name:node.id.name,line:node.loc.start.line,bytes:Buffer.byteLength(body)});
      }
    }
    for(const [k,v]of Object.entries(node))if(!['loc','start','end'].includes(k)) {
      if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);
    }
  }
  walk(tree);
  for(const item of imports)if(typeof item.specifier==='string'&&item.specifier.startsWith('.')) {
    const target=posix.normalize(posix.join(posix.dirname(name),item.specifier));
    item.target=target;item.tracked=tracked.has(target);
  }
  files.push({path:name,sha256:hash(bytes),bytes:bytes.length,lines:source.split('\n').length,imports,exports,functions});
}
const byPath=new Map(files.map(f=>[f.path,f]));
const roots=['public/app.js','public/sw.js','public/scanner-worker.js','public/data-workspace.js','cloud/handler.mjs','corpus/engine.mjs','extension/popup-source.js','netlify-return/i18n-source.js'];
const reachability=[];
for(const root of roots) {
  const visited=new Set(),stack=[root];
  while(stack.length) {
    const name=stack.pop();if(visited.has(name))continue;visited.add(name);
    for(const edge of byPath.get(name)?.imports||[])if(edge.target&&edge.tracked)stack.push(edge.target);
  }
  reachability.push({root,present:tracked.has(root),moduleCount:visited.size,modules:[...visited].sort()});
}
const reachable=new Set(reachability.flatMap(r=>r.modules));
const report={kind:'Derived read-only evidence snapshot; not authority, tracker, dead-code deletion list or runtime verification',repo,revision,
 parser:{path:parserFile,sha256:hash(readFileSync(parserFile))},trackedFiles:names.length,parsedSourceFiles:files.length,parseErrors:errors,
 missingRelativeImports:files.flatMap(f=>f.imports.filter(i=>i.target&&!i.tracked).map(i=>({from:f.path,...i}))),
 unresolvedDynamicImports:files.flatMap(f=>f.imports.filter(i=>i.specifier===null).map(i=>({from:f.path,...i}))),
 reachability,notReachableFromDeclaredRoots:files.filter(f=>!reachable.has(f.path)).map(f=>f.path),
 exactDuplicateFunctionBodies:[...functionBodies.entries()].filter(([,v])=>v.length>1).map(([sha256,occurrences])=>({sha256,occurrences})),files,
 limits:['Static JavaScript module graph only. HTML/assets, remote routes, Python and build-time generation require separate joins.','Not-reachable may be a tool, entrypoint or standalone component; it does not establish dead code.','No dependencies installed, network/credentials/containers/app functions invoked, source edits or tests run.']};
writeFileSync(out,JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify({revision,parsedSourceFiles:files.length,parseErrors:errors.length,missingRelativeImports:report.missingRelativeImports,exactDuplicateFunctions:report.exactDuplicateFunctionBodies.length,notReachable:report.notReachableFromDeclaredRoots})+'\n');
