import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const html = await readFile(new URL('../../apps/web/assets/index.html', import.meta.url), 'utf8');
const css = await readFile(new URL('../../apps/web/assets/style.css', import.meta.url), 'utf8');

test('the landing and footer link to a script-independent notice before sign-in', () => {
  const header = html.match(/<header class="site-header">([\s\S]*?)<\/header>/)[1];
  const footer = html.match(/<div class="legal-footer">([\s\S]*?)<\/div>/)[1];
  const entry = '<a href="#entry-privacy" lang="en" dir="ltr">Privacy &amp; cookies</a>';
  assert.ok(header.includes(entry) && header.includes('class="header-more-menu"'));
  const landingFooter = html.match(/<footer class="landing-footer">([\s\S]*?)<\/footer>/)[1];
  assert.ok(landingFooter.includes(entry));
  assert.ok(footer.includes(entry));
  assert.match(footer, /Open Food Facts · ODbL \/ DbCL/);
  assert.match(footer, /Open Prices · ODbL/);
  const notice = html.match(/<section class="entry-privacy"([\s\S]*?)<\/section>/)[1];
  assert.match(notice, /data-offmenu-privacy-entry aria-labelledby="entry-privacy"/);
  assert.match(notice, /<div lang="en" dir="ltr" data-offmenu-english-privacy-notice>/);
  assert.match(notice, /id="entry-privacy" tabindex="-1"/);
  assert.match(notice, /Guest without signing in/);
  assert.match(notice, /not a choice to allow optional tracking/);
  assert.match(notice, /not the full policy/);
  assert.doesNotMatch(notice, /<(?:script|link|iframe|img|form|input)\b|\b(?:src|href)=/i);
  const dialog = html.match(/<dialog id="account-dialog"([\s\S]*?)<\/dialog>/)[1];
  assert.match(dialog, /not a choice to allow optional tracking[\s\S]+id="auth-controls"/);
  assert.match(dialog, /href="#third-party-services">Privacy preferences/);
  assert.match(dialog, /<p lang="en" dir="ltr">You can use Guest[^<]+<\/p><p class="entry-privacy-preferences" lang="en" dir="ltr"><a href="#third-party-services"/);
});

test('English fallback is explicit and the local preferences link waits for existing controls', () => {
  const block = html.match(/<div lang="en" dir="ltr" data-offmenu-english-privacy-notice>([\s\S]*?)<\/div>/)[1];
  assert.doesNotMatch(block, /data-i18n/);
  assert.equal((block.match(/<p>/g) || []).length, 3);
  assert.match(html, /aria-labelledby="entry-privacy" lang="en" dir="ltr"/);
  assert.match(html, /<p>This privacy notice is available in English only\.<\/p>/);
  assert.doesNotMatch(html, /id="privacy-preferences"/);
  assert.match(html, /<section id="third-party-services" tabindex="-1" aria-live="polite"><\/section>/);
  assert.match(css, /\.entry-privacy-preferences\{display:none\}/);
  assert.match(css, /\.account-dialog:has\(#third-party-services form\) \.entry-privacy-preferences\{display:block\}/);
});
