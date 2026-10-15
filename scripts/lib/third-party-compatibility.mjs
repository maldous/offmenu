import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

export const PINNED_MAIN = '8652b312ce7989c5e4f2d49ae765d5d8daf5841d';
export const PINNED_THIRD_PARTY = '84c4732af985965c3e5b00383acaa662bdd52ea6';
export const MIGRATIONS = ['admin-schema.sql', 'admin-operations-schema.sql', 'admin-mcp-schema.sql',
  'services-schema.sql', 'care-cases-schema.sql', 'care-community-schema.sql', 'care-updates-schema.sql',
  'recipe-community-schema.sql', 'community-ai-schema.sql', 'personal-ai-schema.sql'];

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export function git(root, ...args) {
  return execFileSync('git', args, { cwd: root, env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' }, maxBuffer: 32 * 1024 * 1024 });
}

export function snapshot(root, commit) {
  if (!/^[a-f0-9]{40}$/.test(commit)) throw Error('An immutable full commit SHA is required.');
  if (git(root, 'rev-parse', commit + '^{commit}').toString().trim() !== commit) throw Error('Commit mismatch.');
  const entries = new Map();
  for (const record of git(root, 'ls-tree', '-r', '-z', commit).toString().split('\0').filter(Boolean)) {
    const [metadata, name] = record.split('\t');
    const [mode, type, oid] = metadata.split(' ');
    if (!name || name.split('/').includes('..') || name.startsWith('/')) throw Error('Unsafe snapshot path.');
    entries.set(name, { mode, type, oid, commit });
  }
  return entries;
}

const same = (a, b) => a?.mode === b?.mode && a?.type === b?.type && a?.oid === b?.oid;
export const changedPaths = (base, next) => [...new Set([...base.keys(), ...next.keys()])]
  .filter(name => !same(base.get(name), next.get(name))).sort();

// Conservative three-way composition of immutable leaf entries, without writing Git objects.
// Any distinct edit on both sides requires an explicit reviewed integration decision.
export function composeSnapshots(base, main, thirdParty) {
  const mainChanges = changedPaths(base, main), thirdPartyChanges = changedPaths(base, thirdParty);
  const mainSet = new Set(mainChanges);
  const conflicts = thirdPartyChanges.filter(name => mainSet.has(name) && !same(main.get(name), thirdParty.get(name)));
  if (conflicts.length) throw Error('Composition requires review for overlapping edits: ' + conflicts.join(', '));
  const entries = new Map(main);
  for (const name of thirdPartyChanges) {
    if (thirdParty.has(name)) entries.set(name, thirdParty.get(name)); else entries.delete(name);
  }
  const manifest = [...entries].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([path, { mode, type, oid }]) => ({ path, mode, type, oid }));
  return { entries, mainChanges, thirdPartyChanges, manifest, manifestSHA256: sha256(JSON.stringify(manifest)) };
}

export function blob(root, entry) {
  if (!entry || entry.type !== 'blob' || !['100644', '100755'].includes(entry.mode)) throw Error('Expected a regular Git blob.');
  return git(root, 'cat-file', 'blob', entry.oid);
}
