import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { parseThirdPartyConfig } from '../scripts/verify-third-party-config.mjs';

const base = { client: { diagnostics: { enabled: false }, analytics: { enabled: false, provider: 'zaraz', purposeId: '' }, consent: { siteId: '', cookiePolicyId: '', tcfEnabled: false }, feedback: { productId: '', boardUrl: '' }, ads: { client: '', slot: '', approved: false } }, links: { status: '', privacy: '', source: 'https://github.com/maldous/offmenu' }, seo: { googleSiteVerification: '', bingSiteVerification: '' } };
const clone = () => structuredClone(base);

test('safe third-party config remains fully disabled by default', () => {
  const config = parseThirdPartyConfig(clone());
  assert.equal(config.client.analytics.provider, 'zaraz');
  assert.equal(config.client.ads.approved, false);
  assert.equal(config.client.consent.policyLanguage, 'en');
});
test('configured services require their complete, fixed-domain settings', () => {
  const config = clone();
  config.client.consent = { siteId: '123', cookiePolicyId: '456', tcfEnabled: true };
  config.client.feedback = { productId: '7', boardUrl: 'https://feedback.sleekplan.app/offmenu' };
  config.client.ads = { client: 'ca-pub-1234567890123456', slot: '12345', approved: true };
  config.links.privacy = 'https://www.iubenda.com/privacy-policy/456';
  assert.equal(parseThirdPartyConfig(config).client.ads.slot, '12345');
});
test('partial, unapproved, or arbitrary service configuration is rejected', () => {
  const partialConsent = clone(); partialConsent.client.consent.siteId = '1';
  assert.throws(() => parseThirdPartyConfig(partialConsent), /Consent requires both/);
  const unapprovedAds = clone(); unapprovedAds.client.ads.client = 'ca-pub-1234567890123456';
  assert.doesNotThrow(() => parseThirdPartyConfig(unapprovedAds));
  const arbitraryUrl = clone(); arbitraryUrl.client.feedback = { productId: '1', boardUrl: 'https://evil.example/feedback' };
  assert.throws(() => parseThirdPartyConfig(arbitraryUrl), /Invalid feedback board/);
  const personalizedAds = clone(); personalizedAds.client.ads.personalized = true;
  assert.throws(() => parseThirdPartyConfig(personalizedAds), /Unknown ads setting/);
  const unconsentedAds = clone(); unconsentedAds.client.ads = { client: 'ca-pub-1234567890123456', slot: '12345', approved: true };
  assert.throws(() => parseThirdPartyConfig(unconsentedAds), /configured TCF consent/);
  const unsupportedPolicyLanguage = clone(); unsupportedPolicyLanguage.client.consent.policyLanguage = 'ar';
  assert.throws(() => parseThirdPartyConfig(unsupportedPolicyLanguage), /Unsupported privacy policy language/);
});

test('the disposition is exhaustive and keeps the inventory as its evidence-status authority', async () => {
  const dispositionPath = new URL('../docs/third-party-service-disposition.json', import.meta.url);
  const disposition = JSON.parse(await readFile(dispositionPath, 'utf8'));
  const actual = disposition.dispositions.flatMap(group => group.recordIds);
  assert.equal(disposition.sourceInventory.records, 149);
  assert.equal(actual.length, 149);
  assert.equal(new Set(actual).size, actual.length);
  const sourceBytes = await readFile(new URL(disposition.sourceInventory.path, dispositionPath));
  assert.equal(createHash('sha256').update(sourceBytes).digest('hex'), disposition.sourceInventory.sha256);
  const source = JSON.parse(sourceBytes);
  assert.equal(source.records.length, disposition.sourceInventory.records);
  assert.deepEqual([...actual].sort(), source.records.map(record => record.id).sort());
});
