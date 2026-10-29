// Supported Playwright library APIs; no @playwright/test, CDP or profile adoption.
import { createInterface } from 'node:readline';
import { mkdir, writeFile } from 'node:fs/promises';
import { createAdmission, reservationRef, primaryCustody } from './authenticated-browser-qa-admission.mjs';
const admission = await createAdmission(); // Refuses while exact paired review is absent.
const { chromium } = await import('/home/user/.npm/_npx/31e32ef8478fbf80/node_modules/playwright/index.mjs');
const out = '/home/user/src/offmenu-workers/worker-58/output/playwright/worker58-authenticated';
await mkdir(out, { recursive: true });
const before = primaryCustody(), network = [], pageErrors = [], observations = [];
const browser = await chromium.launch({ executablePath: '/home/user/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome', headless: true });
const context = await browser.newContext({ serviceWorkers: 'block' });
await context.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.origin !== new URL(admission.packet.runner.url).origin) {
    network.push({ type: 'external-blocked', origin: url.origin, path: url.pathname });
    await route.abort(); return;
  }
  try { await admission.assertQualified(); await route.continue(); }
  catch (error) { network.push({ type: 'admission-refused', path: url.pathname, reason: error.message }); await route.abort(); }
});
const page = await context.newPage();
page.on('response', r => network.push({ path: new URL(r.url()).pathname, method: r.request().method(), status: r.status() }));
page.on('pageerror', e => pageErrors.push(e.message));
page.on('dialog', async dialog => {
  observations.push({ dialog: dialog.type(), message: dialog.message(), decision: 'accept-reserved-synthetic-confirmation' });
  if (dialog.type() === 'confirm') await dialog.accept(); else await dialog.dismiss();
});
let step = 0;
async function snapshot(label) {
  const text = await page.locator('body').ariaSnapshot();
  const path = `${out}/step-${String(++step).padStart(2, '0')}.txt`;
  await writeFile(path, text);
  observations.push({ label, path, url: page.url() });
  return { label, snapshot: text, file: path };
}
await page.goto(admission.packet.runner.url, { waitUntil: 'networkidle' });
console.log(JSON.stringify(await snapshot('initial-visible-controls')));
const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
try {
  for await (const line of input) {
    try {
      const command = JSON.parse(line);
      await admission.assertQualified();
      if (command.action === 'close') break;
      if (command.action === 'snapshot') { console.log(JSON.stringify(await snapshot(command.label ?? 'visible-controls'))); continue; }
      if (command.action === 'screenshot') { await page.screenshot({ path: `${out}/step-${step}.png`, fullPage: true }); console.log(JSON.stringify({ screenshot: `${out}/step-${step}.png` })); continue; }
      const scope = command.formText ? page.locator('form').filter({ hasText: command.formText }) : page;
      const locator = command.label ? scope.getByLabel(command.label, { exact: true }) : scope.getByRole(command.role, { name: command.name, exact: true });
      if (command.action === 'fill') await locator.fill(command.value);
      else if (command.action === 'click') await locator.click();
      else if (command.action === 'check') await locator.check();
      else throw Error('Unsupported driver action');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(350);
      console.log(JSON.stringify(await snapshot(command.action + '-visible-result')));
    } catch (error) { console.log(JSON.stringify({ actionError: error.message })); }
  }
} finally {
  await writeFile(`${out}/browser-observations.json`, JSON.stringify({ reservationRef, producer: admission.packet.producer, inputRefs: admission.packet.refs, observations, network, pageErrors, primaryBefore: before, primaryAfter: primaryCustody(), scope: 'Actual reserved QA visible UI only; no provider/Google/source07/all-eight acceptance' }, null, 2));
  await context.close(); await browser.close();
}
