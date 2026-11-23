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

test('the exact embedded retailer archive has only approved members and no authoring text',()=>{
  const [assetLine]=read('apps/web/server/generated.mjs').split('\n',1);
  const assets=JSON.parse(assetLine.slice('const ASSETS='.length,-1));
  const encoded=assets['retailer-extension.zip'];
  assert.equal(typeof encoded,'string');
  assert.ok(readFileSync(new URL('../../dist/retailer-extension.zip',import.meta.url)).toString('base64')===encoded,
    'Worker embeds the same archive as the generated download');
  const prefix='offmenu-retailer-extension/';
  const names=['manifest.json','popup.html','popup.css','offmenu-tokens.css','popup.js','README.md','icons/icon-16.png','icons/icon-48.png','icons/icon-128.png','icon.svg'];
  const source=[
    'import io, json, sys, zipfile',
    'expected = sys.argv[1:]',
    'with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as archive:',
    '    if sorted(archive.namelist()) != sorted(expected): sys.exit(3)',
    '    text = [archive.read(name).decode("utf8") for name in expected if not name.endswith(".png")]',
    '    print(json.dumps(text))',
  ].join('\n');
  let bodies;
  try {
    bodies=JSON.parse(execFileSync('python3',['-I','-S','-B','-c',source,...names.map(name=>prefix+name)],{
      input:Buffer.from(encoded,'base64'),encoding:'utf8',maxBuffer:1024*1024,timeout:5000,stdio:['pipe','pipe','pipe'],
    }));
  } catch {
    assert.fail('Public retailer archive did not have the exact approved readable members.');
  }
  assert.equal(bodies.length,7);
  for(const body of bodies) assert.doesNotThrow(()=>assertNoPublicAuthoring(body));
  const manifest=JSON.parse(bodies[0]);
  assert.ok(JSON.stringify(manifest.permissions)==='["activeTab","scripting"]');
  assert.ok(['host_permissions','optional_host_permissions','content_scripts','background'].every(key=>!Object.hasOwn(manifest,key)));
});
