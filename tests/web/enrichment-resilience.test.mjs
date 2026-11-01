import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createOffMenuHandler} from '../../apps/web/server/handler.mjs';

// UIF-102 / OM-C037 / CACHE-06: synthetic source/consumer cut only.
// No live GLEIF terms/adoption, whole-row acceptance, or historical seed rights
// are established here. The local policy is fabricated test data, not activation.
const query = 'UIF102 SYNTHETIC ORGANIZATION';
const envelope = () => ({data: [{
  id: 'UIF102-SYNTHETIC-NOT-A-REAL-LEI',
  attributes: {entity: {legalName: {name: query}, jurisdiction: 'ZZ', status: 'SYNTHETIC'}},
}]});
const syntheticPolicy = {
  id: 'gleif', version: 'uif102-synthetic-only/1',
  actions: ['display', 'persist'], audiences: ['public'], countries: [],
  evidenceUrl: 'https://synthetic.invalid/uif102',
};

function database() {
  const db = new DatabaseSync(':memory:');
  try {
    // Use production DDL, excluding every seed INSERT and unrelated table.
    const ddl = ['schema.sql', 'catalogue-schema.sql'].map(file =>
      readFileSync(new URL('../../apps/web/server/' + file, import.meta.url), 'utf8')).join('\n');
    for (const table of ['source_policies', 'integration_limits', 'resolver_cache', 'resolver_leases']) {
      const statement = ddl.match(new RegExp('^CREATE TABLE IF NOT EXISTS ' + table + '\\s*\\([^;]+;', 'm'));
      assert.ok(statement, 'Production DDL missing: ' + table);
      db.exec(statement[0]);
    }
    db.prepare('INSERT INTO source_policies(id,document,revision,active) VALUES(?,?,?,?)')
      .run('gleif', JSON.stringify(syntheticPolicy), 1, 1);
    // Only adapt the D1 interface. All SQL, conflicts, leases and cache decisions
    // execute in SQLite; no resolver behavior is implemented by this adapter.
    const env = {DB: {prepare(sql) {
      const statement = db.prepare(sql);
      const bound = args => ({
        async first() { return statement.get(...args) ?? null; },
        async all() { return {results: statement.all(...args)}; },
        async run() { return {success: true, meta: statement.run(...args)}; },
      });
      return {...bound([]), bind(...args) { return bound(args); }};
    }}};
    return {db, env};
  } catch (error) {
    db.close();
    throw error;
  }
}

function barrier() {
  let release;
  const promise = new Promise(resolve => { release = resolve; });
  return {promise, release};
}

async function fixture(run) {
  const savedFetch = globalThis.fetch;
  const SavedDate = globalThis.Date;
  let now = SavedDate.parse('2030-01-01T00:00:00.000Z');
  const plans = [], allPlans = [], unexpected = [], pending = [];
  let fetches = 0;
  let db;
  // Installed before constructing the handler or making any route call. There
  // is deliberately no path to savedFetch: unplanned requests fail closed.
  globalThis.fetch = async (input, options) => {
    fetches++;
    const plan = plans.shift();
    try {
      assert.ok(plan, 'Unplanned fetch');
      const target = new URL(input instanceof Request ? input.url : String(input));
      assert.equal(target.origin, 'https://api.gleif.org');
      assert.equal(target.pathname, '/api/v1/lei-records');
      assert.deepEqual([...target.searchParams], [
        ['filter[entity.legalName]', query], ['page[size]', '10'],
      ]);
      assert.equal(options.redirect, 'manual');
      assert.equal(options.headers.Accept, 'application/json');
      assert.ok(options.signal instanceof AbortSignal);
    } catch (error) {
      unexpected.push(error.message);
      throw error;
    }
    plan.entered.release();
    await plan.response.promise;
    return Response.json(plan.body, {status: plan.status});
  };
  globalThis.Date = class extends SavedDate {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  };
  try {
    const memory = database();
    db = memory.db;
    const handler = createOffMenuHandler({photoFetch: globalThis.fetch});
    const f = {
      db,
      get fetches() { return fetches; },
      get now() { return now; },
      advanceBeyond(timestamp) {
        assert.ok(timestamp >= now);
        now = timestamp + 1;
      },
      expectFetch(body, status = 200, held = false) {
        const plan = {body, status, entered: barrier(), response: barrier()};
        plans.push(plan);
        allPlans.push(plan);
        if (!held) plan.response.release();
        return plan;
      },
      call(value = query) {
        const url = new URL('https://synthetic.invalid/api/catalogue/enrich');
        url.searchParams.set('source', 'gleif');
        url.searchParams.set('query', value);
        const response = handler.fetch(new Request(url), memory.env);
        pending.push(response);
        return response;
      },
      cache() {
        const rows = db.prepare('SELECT * FROM resolver_cache').all();
        assert.equal(rows.length, 1);
        assert.equal(rows[0].source_id, 'gleif');
        return rows[0];
      },
      leases(count = 0) {
        assert.equal(db.prepare('SELECT count(*) AS n FROM resolver_leases').get().n, count);
      },
    };
    await run(f);
    assert.equal(plans.length, 0, 'Every planned synthetic response must be consumed');
  } finally {
    // Release even when an assertion fails, then drain before restoring globals
    // and closing SQLite. No test can leave a suspended provider operation.
    for (const plan of allPlans) plan.response.release();
    try {
      await Promise.allSettled(pending);
      assert.deepEqual(unexpected, [], 'Zero unexpected requests; no real network fallback');
      if (db) assert.equal(db.prepare('SELECT count(*) AS n FROM resolver_leases').get().n, 0);
    } finally {
      globalThis.fetch = savedFetch;
      globalThis.Date = SavedDate;
      db?.close();
    }
  }
}

// Reject promptly if routing fails before reaching the provider barrier.
async function entered(plan, response) {
  await Promise.race([
    plan.entered.promise,
    response.then(r => { throw new Error('Route returned before provider barrier: ' + r.status); }),
  ]);
}

test('equivalent concurrent queries share one provider fetch and release the resolver lease', async () => {
  await fixture(async f => {
    const plan = f.expectFetch(envelope(), 200, true);
    const first = f.call('  ' + query + '  ');
    try {
      await entered(plan, first);
      f.leases(1);
      const second = await f.call();
      assert.equal(second.status, 503);
      assert.equal((await second.json()).error, 'Equivalent public lookup is refreshing');
      assert.equal(f.fetches, 1);
    } finally { plan.response.release(); }
    const response = await first;
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.cache, 'miss');
    assert.equal(body.records.length, 1);
    assert.equal(body.records[0].id, 'lei:UIF102-SYNTHETIC-NOT-A-REAL-LEI');
    assert.equal(body.records[0].legalName, query);
    assert.equal(body.records[0].matchStatus, 'candidate');
    assert.deepEqual(JSON.parse(f.cache().document), body);
    assert.equal(f.fetches, 1);
    f.leases();
  });
});

test('provider 503 remains a failure, pauses retries, then recovers after stored retry_after', async () => {
  await fixture(async f => {
    f.expectFetch({error: 'UIF102 SYNTHETIC OUTAGE'}, 503);
    const failure = await f.call();
    assert.equal(failure.status, 502);
    const body = await failure.json();
    assert.equal(body.error, 'Provider unavailable (503)');
    assert.equal(Object.hasOwn(body, 'records'), false);
    const cached = f.cache();
    assert.equal(cached.document, null);
    assert.equal(cached.fresh_until, 0);
    assert.equal(cached.failures, 1);
    assert.ok(cached.retry_after > f.now);
    assert.equal(body.retryAfter, cached.retry_after);
    f.leases();
    const paused = await f.call();
    assert.equal(paused.status, 503);
    assert.deepEqual(await paused.json(), {
      error: 'Provider temporarily paused', retryAfter: cached.retry_after,
    });
    assert.equal(f.fetches, 1, 'Paused retry performs zero additional fetches');
    assert.deepEqual(f.cache(), cached);
    f.leases();
    f.advanceBeyond(cached.retry_after);
    f.expectFetch(envelope());
    const recovered = await f.call();
    assert.equal(recovered.status, 200);
    const result = await recovered.json();
    assert.equal(result.records[0].legalName, query);
    assert.equal(result.cache, 'miss');
    const success = f.cache();
    assert.deepEqual(JSON.parse(success.document), result);
    assert.equal(success.failures, 0);
    assert.equal(success.retry_after, 0);
    assert.ok(success.fresh_until > f.now);
    assert.equal(f.fetches, 2);
    f.leases();
  });
});

test('a clean provider 200 with data:[] is a valid cached no-result, distinct from outage', async () => {
  await fixture(async f => {
    f.expectFetch({data: []});
    const first = await f.call();
    assert.equal(first.status, 200);
    const body = await first.json();
    assert.deepEqual(body.records, []);
    assert.equal(body.cache, 'miss');
    assert.equal(Object.hasOwn(body, 'error'), false);
    const cached = f.cache();
    assert.deepEqual(JSON.parse(cached.document), body);
    assert.ok(cached.fresh_until > f.now);
    assert.equal(cached.failures, 0);
    assert.equal(cached.retry_after, 0);
    const repeat = await f.call();
    assert.equal(repeat.status, 200);
    assert.deepEqual(await repeat.json(), {...body, cache: 'hit'});
    assert.deepEqual(f.cache(), cached);
    assert.equal(f.fetches, 1);
    f.leases();
  });
});

test('synthetic policy withdrawal in flight denies persistence and cleans up', async () => {
  await fixture(async f => {
    const plan = f.expectFetch(envelope(), 200, true);
    const first = f.call();
    try {
      await entered(plan, first);
      f.leases(1);
      f.db.prepare('UPDATE source_policies SET active=0 WHERE id=?').run('gleif');
    } finally { plan.response.release(); }
    const response = await first;
    assert.equal(response.status, 502);
    const body = await response.json();
    assert.equal(body.error, 'Source permissions changed during lookup');
    assert.equal(Object.hasOwn(body, 'records'), false);
    const cached = f.cache();
    assert.equal(cached.document, null, 'No successful result persisted after withdrawal');
    assert.equal(cached.fresh_until, 0);
    assert.equal(cached.failures, 1);
    assert.ok(cached.retry_after > f.now);
    f.leases();
    const denied = await f.call();
    assert.equal(denied.status, 403);
    assert.equal((await denied.json()).error, 'source policy unavailable');
    assert.equal(f.fetches, 1, 'Real display admission blocks another fetch');
    assert.deepEqual(f.cache(), cached);
    f.leases();
  });
});
