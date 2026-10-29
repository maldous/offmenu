import assert from 'node:assert/strict';
import test from 'node:test';
import { serviceConfiguration } from '../../apps/web/server/service-config.mjs';
import { serviceSupportRoutes } from '../../apps/web/server/service-support.mjs';
import { diagnosticRoutes } from '../../apps/web/server/service-observability.mjs';

const vault = 'a'.repeat(64);
const services = { client: { diagnostics: { enabled: true }, analytics: { enabled: false, provider: 'zaraz', purposeId: '' }, consent: { siteId: '', cookiePolicyId: '', tcfEnabled: false, policyLanguage: 'en' }, feedback: { productId: '', boardUrl: '' }, ads: { client: '', slot: '', approved: false } }, links: {}, seo: {} };
const globals = { defaults: { country: 'AU', units: 'imperial', servings: 3, uiLanguage: 'en' }, features: { supportEmail: false, documentEmail: false }, limits: { supportRetentionDays:7, diagnosticsHourlyLimit:1, supportHourlyLimit:1, documentHourlyLimit:1 } };
const env = { DB: {}, PROVIDER_VAULT_KEY: vault, SENTRY_DSN: 'https://'+'a'.repeat(32)+'@o1.ingest.sentry.io/1', BREVO_API_KEY: 'b'.repeat(16), BREVO_SENDER_EMAIL: 'sender@example.test', BREVO_SENDER_NAME: 'OffMenu', SUPPORT_EMAIL: 'support@example.test', THIRD_PARTY_CONFIG: JSON.stringify(services), SERVICE_GLOBAL_SETTINGS: JSON.stringify(globals) };
const reply = (data, status = 200) => Response.json(data, { status });
const user = { id: 'owner', email: 'owner@example.test', confirmed_at: '2026-10-14T00:00:00.000Z' };

test('global settings project only public defaults and feature-safe email availability', () => {
  const configured = serviceConfiguration(env);
  assert.deepEqual(configured.globalDefaults, globals.defaults);
  assert.deepEqual(configured.emailFeatures, { support: false, document: false });
  assert.equal(configured.services.find(service => service.id === 'support').status, 'setup_required');
  assert(!JSON.stringify(configured).includes(env.BREVO_API_KEY));
});

test('global email feature switches stop private requests before provider or database writes', async () => {
  const request = new Request('https://app.example/api/services/support', { method: 'POST', headers: { Origin: 'https://app.example', 'content-type': 'application/json' }, body: JSON.stringify({ idempotencyKey: 'a'.repeat(16), confirmed: true, subject: 'Help', message: 'Please help' }) });
  const response = await serviceSupportRoutes(request, env, { verifiedUser: async () => user, boundedJSON: request => request.json(), reply });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error, 'Support email is not available.');
});

test('global diagnostics cap applies before outbound reporting', async () => {
  const limitedEnv = { ...env, DB: { prepare() { return { bind() { return { first: async () => ({ count: 2 }) }; } }; } } };
  const request = new Request('https://app.example/api/services/diagnostics', { method: 'POST', headers: { Origin: 'https://app.example', 'content-type': 'application/json' }, body: JSON.stringify({ consent: true, code: 'browser_error' }) });
  const response = await diagnosticRoutes(request, limitedEnv, { verifiedUser: async () => user, boundedJSON: request => request.json(), reply });
  assert.equal(response.status, 429);
  assert.equal((await response.json()).error, 'Error reporting limit reached.');
});
