import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
export function verifyFixtures() {
  const manifest = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url)));
  for (const file of manifest.files) {
    assert.equal(createHash('sha256').update(readFileSync(new URL(file.path, import.meta.url))).digest('hex'), file.sha256, file.path);
  }
}
