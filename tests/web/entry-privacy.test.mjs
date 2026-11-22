import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const html = await readFile(new URL('../../apps/web/assets/index.html', import.meta.url), 'utf8');

test('the landing and footer link to a script-independent notice before sign-in', () => {
  const header = html.match(/<header class="site-header">([\s\S]*?)<\/header>/)[1];
  const footer = html.match(/<div class="legal-footer">([\s\S]*?)<\/div>/)[1];
  const entry = '<a href="#entry-privacy" lang="en">Privacy &amp; cookies</a>';
  assert.ok(header.includes(entry) && header.indexOf(entry) < header.indexOf('id="header-login"'));
  assert.ok(footer.includes(entry));
  assert.match(footer, /Open Food Facts · ODbL \/ DbCL/);
  assert.match(footer, /Open Prices · ODbL/);
  const notice = html.match(/<section class="entry-privacy"([\s\S]*?)<\/section>/)[1];
  assert.match(notice, /data-offmenu-privacy-entry lang="en"/);
  assert.match(notice, /id="entry-privacy" tabindex="-1"/);
  assert.match(notice, /Guest without signing in/);
  assert.match(notice, /not a choice to allow optional tracking/);
  assert.match(notice, /not the full policy/);
  assert.doesNotMatch(notice, /<(?:script|link|iframe|img|form|input)\b|\b(?:src|href)=/i);
  const dialog = html.match(/<dialog id="account-dialog"([\s\S]*?)<\/dialog>/)[1];
  assert.match(dialog, /not a choice to allow optional tracking[\s\S]+id="auth-controls"/);
  assert.match(dialog, /href="#third-party-services"/);
});
