import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {assertNoPublicAuthoring} from '../../scripts/public-html-boundary.mjs';

const read=file=>readFileSync(new URL('../../'+file,import.meta.url),'utf8');

test('the normal generated Worker and every emitted public HTML body exclude private authoring material',()=>{
  const generated=read('apps/web/server/generated.mjs');
  assert.doesNotThrow(()=>assertNoPublicAuthoring(generated));
  const worker=read('dist/worker.mjs');
  assert.doesNotThrow(()=>assertNoPublicAuthoring(worker));
  const [assetsLine,releaseLine]=generated.split('\n',2);
  assert.ok(assetsLine.startsWith('const ASSETS='),'generated assets envelope');
  assert.ok(releaseLine.startsWith('const RELEASE='),'generated release envelope');
  const parse=(line,prefix)=>{try{return JSON.parse(line.slice(prefix.length,-1));}catch{assert.fail('Invalid generated envelope');}};
  const assets=parse(assetsLine,'const ASSETS=');
  const release=parse(releaseLine,'const RELEASE=');
  assert.equal(release.sourceCommit,execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim());
  assert.ok(worker.includes(release.sourceCommit),'minified Worker retains its built source identity');
  const htmlKeys=Object.keys(assets).filter(name=>name.endsWith('.html'));
  for (const name of ['index.html','data-workspace.html','shelf-scanner.html','help.html']) assert.ok(htmlKeys.includes(name),name+' is emitted');
  for (const name of htmlKeys) assert.doesNotThrow(()=>assertNoPublicAuthoring(assets[name]));
  assert.equal((assets['index.html'].match(/data-close="account-dialog"/g)||[]).length,1);
});
