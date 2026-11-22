import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {assertNoPublicAuthoring,publicHTML} from '../../scripts/public-html-boundary.mjs';

const start='<!-- impeccable-live-start -->', end='<!-- impeccable-live-end -->';
const synthetic='<script src="http://localhost:8400/live.js?token=not-a-real-token"></script>';
const read=name=>readFileSync(new URL('../../apps/web/assets/'+name,import.meta.url),'utf8');

test('production HTML preserves non-authoring bytes exactly',()=>{
  const text='<!doctype html>\n<a href="/help.html">Help</a><script src="/app.js"></script>\n';
  assert.equal(publicHTML(text),text);
});

test('production HTML removes complete local authoring blocks at every position',()=>{
  const block=start+'\n'+synthetic+'\n'+end;
  assert.equal(publicHTML(block+'<main>Guest</main>'+block),'<main>Guest</main>');
  assert.equal(publicHTML('x<!-- Impeccable-Live-Start -->\n'+synthetic+'<!-- Impeccable-Live-End -->y'),'xy');
});

test('production HTML refuses malformed authoring, unexpected nested content, and stray scripts without revealing input',()=>{
  const rejected=[
    end, start+synthetic, start+start+synthetic+end+end,
    start+'<script src="/public.js"></script>'+end,
    start+'<script src="https://example.invalid/live.js"></script>'+end,
    start+synthetic+'<main>Do not silently discard me</main>'+end,
    synthetic, '<!-- impeccable-variants-start invented -->',
    '<div data-impeccable-variant="invented"></div>',
    '<style data-impeccable-css="invented"></style>',
  ];
  for (const value of rejected) assert.throws(()=>publicHTML(value),/^Error: (?:Invalid private authoring block|Public build contains private authoring material)\.$/);
  assert.throws(()=>assertNoPublicAuthoring('let x="http://127.0.0.1:1234/live.js";'),/contains private authoring material/);
});

test('all four actual public HTML sources sanitize without losing their ordinary client entry points',()=>{
  for (const [name,script] of [['index.html','/app.js'],['data-workspace.html','/data-workspace.js'],['shelf-scanner.html','/shelf-scanner.js'],['help.html','/help.js']]) {
    const html=publicHTML(read(name));
    assert.doesNotThrow(()=>assertNoPublicAuthoring(html));
    assert.ok(html.includes('src="'+script),name+' retains its ordinary entry point');
  }
});

test('the canonical Account dialog has one native original close with its existing translation key and accessible name',()=>{
  const html=publicHTML(read('index.html'));
  const match=html.match(/<dialog id="account-dialog"[^>]*>([\s\S]*?)<\/dialog>/);
  assert.ok(match,'Account dialog remains');
  const controls=[...match[1].matchAll(/<button\b[^>]*\bdata-close="account-dialog"[^>]*>/g)].map(entry=>entry[0]);
  assert.deepEqual(controls,['<button class="dialog-close" data-close="account-dialog" aria-label="Close account panel" data-i18n-aria-label="Close account panel">']);
});
