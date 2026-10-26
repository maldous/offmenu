// Unmounted source candidate. Dependencies are trusted server callbacks only.
// No DB, HTTP, keys, routes, restore executor or default storage reader.
export const SOURCE_IDS = Object.freeze(['nativeRecords', 'legacyUserState',
  'ownedKitchenState', 'privateDocuments', 'privateRecords', 'safeConnections',
  'attachments', 'relationships', 'payloadExtensions']);
const FIELDS = ['inventory', 'profile.full', 'settings', 'content', 'auth_metadata',
  'history', 'derived_provenance', 'attachments', 'relationships', 'extensions'];
const AXES = ['content', 'settings', 'attachments', 'relationships', 'history', 'derived_provenance'];
const TYPES = new Set(['space','location','item','lot','holding','movement','reservation',
  'waste','profile','medical_plan','settings','content','identity_link',
  'connection_metadata','auth_history','consent_history','derived_provenance']);
const EXCLUDED = Object.freeze(['credentials and sealed provider credentials',
  'tokens, cookies, sessions, secret/key material', 'effective grants and entitlements',
  'other owners’ profiles/health/stock; membership alone is insufficient',
  'public catalogue/cache copies and source bodies without export permission']);
const fail = code => { throw new Error('Owned snapshot unavailable (' + code + ').'); };
const atom = v => typeof v === 'string' && v.length > 0 && v.length <= 200 && !/[\u0000-\u001f]/u.test(v);
const plain = v => v !== null && typeof v === 'object' &&
  [Object.prototype, null].includes(Object.getPrototypeOf(v));
const key = r => JSON.stringify([r.type, r.id]);
const secret = /^(?:password(?:hash)?|api[_-]?key|token|oauth[_-]?token|secret|secret[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|session(?:[_-]?(?:token|cookie))?|cookie|authorization|bearer|client[_-]?secret|private[_-]?key|raw[_-]?key|wrapped[_-]?key|credentials?|sealed|credential[_-]?envelope[_-]?ref)$/iu;

// Lossless finite JSON, including literal __proto__ keys. Reject accessors,
// exotic objects and sparse arrays rather than stringify them silently.
function json(value, maxBytes = 2_000_000) {
  let nodes = 0;
  function visit(v, depth) {
    if (++nodes > 100000 || depth > 40) fail('JSON_LIMIT');
    if (v === null || typeof v === 'boolean' || typeof v === 'string') return v;
    if (typeof v === 'number' && Number.isFinite(v) && !Object.is(v, -0)) return v;
    if (Array.isArray(v)) {
      if (Object.keys(v).length !== v.length) fail('JSON_ARRAY');
      return Array.from({length:v.length}, (_, i) => {
        const d = Object.getOwnPropertyDescriptor(v, String(i));
        if (!d || !('value' in d)) fail('JSON_ACCESSOR');
        return visit(d.value, depth + 1);
      });
    }
    if (!plain(v) || Reflect.ownKeys(v).length !== Object.keys(v).length) fail('JSON_VALUE');
    const out = Object.create(null);
    for (const k of Object.keys(v)) {
      if (secret.test(k)) fail('SECRET_FIELD');
      const d = Object.getOwnPropertyDescriptor(v, k);
      if (!d || !('value' in d)) fail('JSON_ACCESSOR');
      out[k] = visit(d.value, depth + 1);
    }
    return out;
  }
  const out = visit(value, 0), text = JSON.stringify(out);
  if (new TextEncoder().encode(text).length > maxBytes) fail('SIZE');
  return JSON.parse(text);
}
function stableJSON(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(stableJSON).join(',') + ']';
  return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + stableJSON(v[k])).join(',') + '}';
}
function exact(row, fields) {
  if (!plain(row) || Object.keys(row).some(k => !fields.includes(k)) ||
      fields.some(k => !Object.hasOwn(row, k))) fail('STORAGE_SHAPE');
}
function authority(input, packageId, now) {
  // Do not run no-secret scanning on server authority; it is never exported.
  if (!plain(input)) fail('AUTHORITY');
  const a = input, c = a.consent;
  if (!atom(a.namespace) || !atom(a.identity?.ownerUserId) || !atom(a.identity?.issuer) ||
      !atom(a.identity?.subject) || a.principal?.id !== a.identity.ownerUserId ||
      !Number.isSafeInteger(a.revision) || a.revision < 0) fail('IDENTITY');
  if (!Number.isSafeInteger(now) || !Number.isSafeInteger(a.auth?.reauthenticatedAt) ||
      !Number.isSafeInteger(a.auth?.expiresAt) || a.auth.revokedAt !== null ||
      a.auth.reauthenticatedAt > now || now-a.auth.reauthenticatedAt > 300000 ||
      a.auth.expiresAt <= now) fail('REAUTHENTICATION');
  if (!c || c.ownerUserId !== a.identity.ownerUserId || c.purpose !== 'owned-backup' ||
      c.choice !== 'granted' || c.revokedAt !== null || !atom(c.id) ||
      !Number.isSafeInteger(c.revision) || c.revision < 1 ||
      !Number.isSafeInteger(c.validFrom) || !Number.isSafeInteger(c.expiresAt) ||
      c.validFrom > now || c.expiresAt <= now ||
      !Array.isArray(c.fields) || FIELDS.some(f => !c.fields.includes(f))) fail('CONSENT');
  for (const f of ['kitchens', 'allowedRecords', 'tombstones'])
    if (!Array.isArray(a[f]) || !a[f].every(atom)) fail('SCOPE');
  // Copy only the authority fence used here; avoid returning authority data.
  return structuredClone({packageId, namespace:a.namespace, identity:a.identity,
    principal:a.principal, revision:a.revision, auth:a.auth, consent:c,
    kitchens:a.kitchens, allowedRecords:a.allowedRecords, tombstones:a.tombstones});
}
function census(sources) {
  if (!Array.isArray(sources) || sources.length > 100) fail('SOURCE_CENSUS');
  const ids = new Set();
  for (const s of sources) {
    exact(s, ['id','status','revision','count']);
    if (!atom(s.id) || ids.has(s.id) || !['present','absent','unavailable'].includes(s.status) ||
        !(s.revision === null || atom(s.revision)) ||
        !(s.count === null || Number.isSafeInteger(s.count) && s.count >= 0) ||
        s.status === 'absent' && s.count !== 0 ||
        s.status === 'present' && (s.count === null || s.revision === null)) fail('SOURCE_CENSUS');
    ids.add(s.id);
  }
  return json(sources);
}
function rawRow(sourceId, row, a) {
  const specs = {
    legacyUserState:['user_id','revision','state_json','updated_at'],
    ownedKitchenState:['id','owner_user_id','revision','state_json','updated_at'],
    privateDocuments:['owner','kind','id','revision','document','updated_at'],
    privateRecords:['owner','id','kind','source_id','countries','document','updated_at'],
    safeConnections:['user_id','source_id','label','updated_at']
  };
  exact(row, specs[sourceId]);
  const owner = row.user_id ?? row.owner_user_id ?? row.owner;
  if (owner !== a.identity.ownerUserId) fail('OWNER_SCOPE');
  if (sourceId === 'ownedKitchenState' && !a.kitchens.includes(row.id)) fail('KITCHEN_SCOPE');
  const id = sourceId === 'legacyUserState' ? row.user_id : sourceId === 'safeConnections' ? row.source_id : row.id;
  if (!atom(id) || typeof row.updated_at !== 'string' || !Number.isFinite(Date.parse(row.updated_at))) fail('SOURCE_IDENTITY');
  if ('revision' in row && (!Number.isSafeInteger(row.revision) || row.revision < 1)) fail('SOURCE_REVISION');
  // Decode only ordinary JSON supplied by the already-qualified snapshot reader.
  // gz: bodies require the existing decodeStoredRecord adapter, never a new codec.
  const bodyKey = 'state_json' in row ? 'state_json' : 'document' in row ? 'document' : null;
  if (bodyKey && typeof row[bodyKey] !== 'string') fail('SOURCE_JSON');
  let body;
  if (bodyKey) {
    try { body = json(JSON.parse(row[bodyKey])); } catch (e) {
      if (e.message.startsWith('Owned snapshot unavailable')) throw e;
      fail('SOURCE_JSON');
    }
  }
  return {sourceRecordId:id, ownerUserId:owner,
    kitchenId:sourceId === 'ownedKitchenState' ? row.id : null,
    revision:row.revision ?? null, updatedAt:row.updated_at,
    storage:row, ...(bodyKey ? {decoded:body} : {}),
    effectiveAuthority:'none', restoreMode:'evidence-only'};
}

export function createOwnedSnapshotExtractor({readAuthority, openSnapshot, authorizeSourceRecord, validatePayload, digest, clock} = {}) {
  if ([readAuthority, openSnapshot, authorizeSourceRecord, validatePayload, digest, clock].some(f => typeof f !== 'function'))
    fail('TRUSTED_DEPENDENCIES');
  return Object.freeze({async extractOwnedSnapshot({packageId} = {}) {
    if (!atom(packageId)) fail('PACKAGE_ID');
    const first = authority(await readAuthority({operation:'owned-backup',phase:'snapshot-before',packageId}), packageId, clock());
    const stamp = stableJSON(first);
    const recheck = async () => {
      const next = authority(await readAuthority({operation:'owned-backup',phase:'snapshot-fence',packageId}), packageId, clock());
      if (stableJSON(next) !== stamp) fail('AUTHORITY_CHANGED');
    };
    let snapshot, finished = false;
    try {
      snapshot = await openSnapshot({ownerUserId:first.identity.ownerUserId,namespace:first.namespace,packageId});
      if (!snapshot || typeof snapshot.close !== 'function') fail('SNAPSHOT_ADAPTER');
      await recheck();
      if (snapshot.ownerUserId !== first.identity.ownerUserId || snapshot.namespace !== first.namespace ||
          !atom(snapshot.revision) || typeof snapshot.readPage !== 'function' ||
          typeof snapshot.readRevision !== 'function') fail('SNAPSHOT_BINDING');
      const revision = snapshot.revision, sources = census(snapshot.sources), blockers = [];
      for (const id of SOURCE_IDS) if (!sources.some(s => s.id === id)) blockers.push('MISSING_SOURCE:' + id);
      const payload = {records:[],attachments:[],relationships:[],extensions:[],coverage:{},lossWarnings:[]};
      const seen = new Set();
      let total = 0;
      for (const source of sources) {
        if (!SOURCE_IDS.includes(source.id)) { blockers.push('UNKNOWN_SOURCE:' + source.id); continue; }
        if (source.status === 'unavailable') { blockers.push('UNAVAILABLE_SOURCE:' + source.id); continue; }
        if (source.status === 'absent') continue;
        let cursor = null, count = 0, pageCount = 0;
        const cursors = new Set(), archived = [];
        do {
          if (++pageCount > 100) fail('PAGE_LIMIT');
          const page = await snapshot.readPage({sourceId:source.id,cursor,limit:100});
          await recheck();
          if (!plain(page) || page.ownerUserId !== first.identity.ownerUserId ||
              page.namespace !== first.namespace || page.snapshotRevision !== revision ||
              page.sourceRevision !== source.revision || !Array.isArray(page.rows) || page.rows.length > 100 ||
              !Number.isSafeInteger(page.withheld) || page.withheld < 0 ||
              !(page.nextCursor === null || atom(page.nextCursor))) fail('PAGE_BINDING');
          if (page.withheld) blockers.push('WITHHELD_SOURCE:' + source.id);
          for (const input of page.rows) {
            if (++total > 10000) fail('ROW_LIMIT');
            const row = json(input);
            // Ownership is necessary but does not establish private-profile,
            // deletion or source export rights for an entire stored JSON body.
            // Require independent, current server-side source qualification.
            const allowed = await authorizeSourceRecord({sourceId:source.id,
              record:structuredClone(row),authority:structuredClone(first),action:'export'});
            await recheck();
            if (allowed !== true) fail('SOURCE_RECORD_AUTHORIZATION');
            count++;
            if (source.id === 'nativeRecords') {
              if (!TYPES.has(row.type) || row.ownerRef !== first.identity.ownerUserId ||
                  row.householdRef !== null && !first.kitchens.includes(row.householdRef) ||
                  !first.allowedRecords.includes(key(row)) || first.tombstones.includes(key(row))) fail('RECORD_SCOPE');
              payload.records.push(row);
            } else if (source.id === 'attachments') payload.attachments.push(row);
            else if (source.id === 'relationships') payload.relationships.push(row);
            else if (source.id === 'payloadExtensions') {
              // No unscoped opaque root extensions: retain them in source-owned
              // archive wrappers so owner and provenance are independently checked.
              exact(row, ['ownerUserId','namespace','extension']);
              if (row.ownerUserId !== first.identity.ownerUserId || row.namespace !== first.namespace) fail('EXTENSION_SCOPE');
              payload.extensions.push(row.extension);
            } else {
              const archive = rawRow(source.id, row, first);
              const id = JSON.stringify([source.id,row.kind ?? null,archive.sourceRecordId]);
              if (seen.has(id)) fail('DUPLICATE_SOURCE_RECORD');
              seen.add(id); archived.push(archive);
            }
          }
          cursor = page.nextCursor;
          if (cursor !== null && (cursors.has(cursor) || page.rows.length === 0)) fail('CURSOR_LOOP');
          if (cursor !== null) cursors.add(cursor);
        } while (cursor !== null);
        if (count !== source.count) blockers.push('COUNT_MISMATCH:' + source.id);
        if (archived.length) payload.extensions.push({namespace:'offmenu.snapshot.' + source.id,
          version:'1',value:{archiveRepresentationVersion:'offmenu-owned-source-archive/1',
            sourceSchemaVersion:null, sourceStore:source.id,
            sourceRevision:source.revision, snapshotRevision:revision, rows:archived}});
      }
      const after = await snapshot.readRevision();
      await recheck();
      if (!after || after.revision !== revision || stableJSON(census(after.sources)) !== stableJSON(sources))
        fail('SNAPSHOT_CHANGED');
      for (const axis of AXES) payload.coverage[axis] = blockers.length ? 'unavailable' : 'included';
      payload.lossWarnings = blockers.map(b => 'Incomplete source inventory: ' + b);
      if (new TextEncoder().encode(stableJSON(payload)).length > 1_048_576) {
        blockers.push('EXISTING_CRYPTOR_SIZE_LIMIT');
        for (const axis of AXES) payload.coverage[axis] = 'unavailable';
        payload.lossWarnings.push('Payload exceeds existing cryptor plaintext limit; no chunking supported.');
      }
      const validated = await validatePayload(json(payload));
      await recheck();
      const payloadDigest = await digest(validated);
      await recheck();
      finished = true;
      return {payload:validated,payloadDigest,
        inventory:{complete:blockers.length === 0,snapshotRevision:revision,sources},
        blockers,excluded:[...EXCLUDED]};
    } finally {
      if (snapshot && typeof snapshot.close === 'function') await snapshot.close();
      if (finished) await recheck();
    }
  }});
}
