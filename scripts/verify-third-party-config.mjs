import { readFile } from 'node:fs/promises';
import process from 'node:process';
import { parseServiceConfig } from '../cloud/service-config.mjs';
import { serviceEmailConfigured } from '../cloud/service-support.mjs';

const examplePath = new URL('../config/third-party.example.json', import.meta.url);
export const parseThirdPartyConfig = parseServiceConfig;

export async function configFromEnvironment(env = process.env) {
  const raw = env.THIRD_PARTY_CONFIG || await readFile(examplePath, 'utf8');
  return parseServiceConfig(raw);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  configFromEnvironment().then(config => process.stdout.write(`${JSON.stringify({ valid: true, configured: Boolean(process.env.THIRD_PARTY_CONFIG), enabled: { diagnostics: config.client.diagnostics.enabled, analytics: config.client.analytics.enabled, consent: Boolean(config.client.consent.siteId), feedback: Boolean(config.client.feedback.productId || config.client.feedback.boardUrl), ads: config.client.ads.approved }, server: { emailConfigured: serviceEmailConfigured(process.env), emailPrerequisites: ['BREVO_API_KEY', 'BREVO_SENDER_EMAIL', 'BREVO_SENDER_NAME', 'PROVIDER_VAULT_KEY'] } })}\n`)).catch(error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
}
