import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import adapter from './freebuff-verified.mjs';

const REDACTED_LAUNCH_ID = '00000000-0000-0000-0000-000000000001';
const REDACTED_PORT = 26833;

describe('verified adapter against redacted live evidence', () => {
  it('extracts launch identity header from verified file schema', () => {
    const fileText = JSON.stringify({
      port: REDACTED_PORT,
      launchId: REDACTED_LAUNCH_ID,
    });
    const headers = adapter.extractCredential(fileText);
    assert.deepStrictEqual(headers, { 'x-freebuff-launch-id': REDACTED_LAUNCH_ID });
  });

  it('rejects files that do not match the verified schema', () => {
    assert.throws(() => adapter.extractCredential('{}'), /LOCAL_ADAPTER_BAD_CREDENTIAL_FILE/);
    assert.throws(() => adapter.extractCredential('{"port":26833}'), /LOCAL_ADAPTER_BAD_CREDENTIAL_FILE/);
    assert.throws(() => adapter.extractCredential('{"launchId":"x"}'), /LOCAL_ADAPTER_BAD_CREDENTIAL_FILE/);
    assert.throws(() => adapter.extractCredential('{"port":"26833","launchId":"x"}'), /LOCAL_ADAPTER_BAD_CREDENTIAL_FILE/);
    assert.throws(() => adapter.extractCredential(null), /LOCAL_ADAPTER_BAD_CREDENTIAL_FILE/);
  });

  it('normalizes actual live response shape without credential or real prompt text', () => {
    const liveSnapshot = {
      thread: {
        archivedAt: 1792034681525,
        id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178',
        projectId: '/home/user/src/offmenu',
        projectPath: '/home/user/src/offmenu',
        title: 'OffMenu — Worker 02 — Preserved migrated main session',
        status: 'open',
        model: 'm-cb71f819fe',
        agentMode: 'build',
        executionMode: 'local',
        executionTarget: 'local',
        turnState: 'idle',
        queuePaused: true,
        pendingWorkCount: 6,
      },
      messages: [
        { role: 'user', parts: [{ kind: 'text', text: 'REDACTED_INITIAL_USER_PROMPT' }], ts: 1792019481269 },
        { role: 'assistant', parts: [{ kind: 'reasoning', id: 'p1', text: 'REDACTED_REASONING' }, { kind: 'text', id: 'p2', text: 'REDACTED_ASSISTANT_TEXT' }], ts: 1792019481270 },
        { role: 'user', parts: [{ kind: 'text', text: 'REDACTED_SECOND_USER_PROMPT' }], ts: 1792019481280 },
      ],
      items: [{ id: '1cadb63c-c7d9-42f1-9228-75bce670f093', kind: 'prompt', state: 'queued' }],
    };

    const normalized = adapter.normalizeSnapshot(liveSnapshot, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.sessionId, '8d8caabd-881d-4fda-bb90-7c7c3f10e178');
    assert.strictEqual(normalized.paused, true);
    assert.ok(Array.isArray(normalized.messages));
    assert.strictEqual(normalized.messages.length, 3);
    assert.strictEqual(normalized.messages[0].id, 'msg-1792019481269-user');
    assert.strictEqual(normalized.messages[0].role, 'user');
    assert.strictEqual(normalized.messages[0].text, 'REDACTED_INITIAL_USER_PROMPT');
    assert.strictEqual(normalized.messages[1].id, 'msg-1792019481270-assistant');
    assert.strictEqual(normalized.messages[1].role, 'assistant');
    assert.strictEqual(normalized.messages[1].text, 'REDACTED_ASSISTANT_TEXT');
    assert.strictEqual(normalized.messages[2].id, 'msg-1792019481280-user');
    assert.strictEqual(normalized.messages[2].role, 'user');
    assert.strictEqual(normalized.messages[2].text, 'REDACTED_SECOND_USER_PROMPT');
  });

  it('rejects messages with the same timestamp and role, even with distinct message objects', () => {
    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: false },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'first' }], ts: 1, nonce: 'a' },
          { role: 'user', parts: [{ kind: 'text', text: 'second' }], ts: 1, nonce: 'b' },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
  });

  it('preserves transient fields on message objects but rejects duplicate ids only', () => {
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
      messages: [
        { role: 'user', parts: [{ kind: 'text', text: 'one' }], ts: 1, _transient: true },
        { role: 'assistant', parts: [{ kind: 'text', text: 'two' }], ts: 2, _transient: false },
      ],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.messages[0]._transient, undefined);
    assert.strictEqual(normalized.messages[1]._transient, undefined);
    assert.strictEqual(normalized.messages[0].text, 'one');
    assert.strictEqual(normalized.messages[1].text, 'two');
  });

  it('rejects the snapshot when nothing survives after dropping invalid messages', () => {
    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'bad timestamp' }], ts: 'not-a-number' },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );

    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'bad' }], ts: 0 },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );

    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [
          { role: 'system', parts: [{ kind: 'text', text: 'no text' }], ts: 1 },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );

    assert.deepStrictEqual(
      adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'keep' }], ts: 1 },
          { role: 'user', parts: [{ kind: 'text', text: 'drop' }], ts: 0 },
          { role: 'assistant', parts: [{ kind: 'text', text: 'also keep' }], ts: 2 },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      {
        sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178',
        paused: null,
        messages: [
          { id: 'msg-1-user', role: 'user', text: 'keep', timestamp: new Date(1).toISOString() },
          { id: 'msg-2-assistant', role: 'assistant', text: 'also keep', timestamp: new Date(2).toISOString() },
        ],
      }
    );
  });

  it('drops malformatted messages', () => {
    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'keep' }], ts: 1 },
          { role: 'user', parts: [{ kind: 'text', text: 'bad timestamp' }], ts: 'not-a-number' },
          { role: 'assistant', parts: [{ kind: 'text', text: 'also keep' }], ts: 2 },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );

    assert.deepStrictEqual(
      adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'keep' }], ts: 1 },
          { role: 'user', parts: [{ kind: 'text', text: 'drop' }], ts: 0 },
          { role: 'assistant', parts: [{ kind: 'text', text: 'also keep' }], ts: 2 },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      {
        sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178',
        paused: null,
        messages: [
          { id: 'msg-1-user', role: 'user', text: 'keep', timestamp: new Date(1).toISOString() },
          { id: 'msg-2-assistant', role: 'assistant', text: 'also keep', timestamp: new Date(2).toISOString() },
        ],
      }
    );
  });

  it('reconstructs temporary ids deterministically and normalizes assistant text', () => {
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: false },
      messages: [
        { role: 'assistant', parts: [{ kind: 'text', text: 'only this' }], ts: 1792021425387 },
        { role: 'user', parts: [{ kind: 'text', text: 'user part one' }, { kind: 'text', text: 'user part two' }], ts: 1000 },
      ],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.paused, false);
    assert.strictEqual(normalized.messages[0].id, 'msg-1792021425387-assistant');
    assert.strictEqual(normalized.messages[0].text, 'only this');
    assert.strictEqual(normalized.messages[1].id, 'msg-1000-user');
    assert.strictEqual(normalized.messages[1].text, 'user part oneuser part two');
  });

  it('normalizes bigint ts safely via Number conversion', () => {
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: true },
      messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: BigInt(1792019481269) }],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.paused, true);
    assert.strictEqual(normalized.messages[0].role, 'user');
    assert.strictEqual(normalized.messages[0].text, 'ok');
    // Verified live ts 1792019481269 is 2026-10-14T23:11:21.269Z in UTC; the
    // host's local wall date (2026-10-15 at UTC+11) is not what ISO strings show.
    assert.strictEqual(normalized.messages[0].timestamp, new Date(1792019481269).toISOString());
    assert.ok(normalized.messages[0].timestamp.startsWith('2026-10-14T23:11:21'));
  });

  it('uses authoritative paused from thread, and null when absent', () => {
    assert.strictEqual(
      adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: false },
        messages: [{ role: 'user', parts: [{ kind: 'text', text: 'x' }], ts: 1 }],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }).paused,
      false
    );
    assert.strictEqual(
      adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
        messages: [{ role: 'user', parts: [{ kind: 'text', text: 'x' }], ts: 2 }],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }).paused,
      null
    );
  });

  it('rejects response without matching session identity', () => {
    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '00000000-0000-0000-0000-000000000001', queuePaused: false },
        messages: [],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
  });

  it('rejects malformed responses', () => {
    assert.throws(() => adapter.normalizeSnapshot(null, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({}, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({ thread: {} }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({ thread: { id: 'x', queuePaused: true }, messages: 'oops' }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({ thread: { id: 'x' }, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
  });

  it('requires a thread object and rejects missing or non-object thread', () => {
    assert.throws(() => adapter.normalizeSnapshot({ messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({ thread: null, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({ thread: 1, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
    assert.throws(() => adapter.normalizeSnapshot({ thread: [], messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
  });

  it('uses sessionId when thread has no usable id', () => {
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { queuePaused: true }, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: null, queuePaused: true }, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '', queuePaused: true }, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: true }, messages: [] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
  });

  it('requires queuePaused to be an exact boolean when present', () => {
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: 1 }, messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 1 }] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: 'true' }, messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 2 }] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: null }, messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 3 }] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: undefined }, messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 4 }] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.throws(
      () => adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: NaN }, messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 5 }] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
    assert.deepStrictEqual(
      adapter.normalizeSnapshot({ thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: false }, messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 6 }] }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', paused: false, messages: [{ id: 'msg-6-user', role: 'user', text: 'ok', timestamp: new Date(6).toISOString() }] }
    );
  });

  it('extracts only text parts for user and assistant, ignoring reasoning', () => {
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
      messages: [
        { role: 'assistant', parts: [{ kind: 'reasoning', text: 'hidden' }, { kind: 'text', text: 'shown' }], ts: 1 },
        { role: 'user', parts: [{ kind: 'text', text: 'also shown' }], ts: 2 },
      ],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.paused, null);
    assert.strictEqual(normalized.messages.length, 2);
    assert.strictEqual(normalized.messages[0].text, 'shown');
    assert.strictEqual(normalized.messages[1].text, 'also shown');
  });

  it('joins adjacent text parts with empty string', () => {
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' },
      messages: [{ role: 'user', parts: [{ kind: 'text', text: 'user part one' }, { kind: 'text', text: 'user part two' }], ts: 1000 }],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.messages[0].text, 'user part oneuser part two');
  });

  it('skips in-flight messages with no ts yet, as observed on real captures', () => {
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: true },
      messages: [
        { role: 'user', parts: [{ kind: 'text', text: 'settled' }], ts: 1792019481269 },
        { role: 'assistant', parts: [{ kind: 'text', text: 'streaming' }] },
      ],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });

    assert.strictEqual(normalized.messages.length, 1);
    assert.strictEqual(normalized.messages[0].id, 'msg-1792019481269-user');
  });

  it('keeps cross-role same-ts pairs and rejects same-role temporary id collisions', () => {
    // Morgan-approved contract (2026-10-17), grounded in live evidence: a turn
    // boundary can place an assistant and a user message in the same
    // millisecond (observed on bac212ab). Their ids differ by role, so both
    // messages are kept as evidence.
    const normalized = adapter.normalizeSnapshot({
      thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: false },
      messages: [
        { role: 'user', parts: [{ kind: 'text', text: 'dup' }], ts: BigInt(3) },
        { role: 'assistant', parts: [{ kind: 'text', text: 'dup too' }], ts: BigInt(3) },
      ],
    }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' });
    assert.strictEqual(normalized.messages.length, 2);
    assert.strictEqual(normalized.messages[0].id, 'msg-3-user');
    assert.strictEqual(normalized.messages[1].id, 'msg-3-assistant');

    // A true temporary id collision (same ts AND role) still rejects: the
    // snapshot cannot identify the messages and must not drop one silently.
    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: false },
        messages: [
          { role: 'user', parts: [{ kind: 'text', text: 'dup' }], ts: 3 },
          { role: 'user', parts: [{ kind: 'text', text: 'dup again' }], ts: BigInt(3) },
        ],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
  });

  it('accepts matching, missing, and mismatching thread identity with exact message ids', () => {
    assert.deepStrictEqual(
      adapter.normalizeSnapshot({
        thread: { queuePaused: true },
        messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 1 }],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', paused: true, messages: [{ id: 'msg-1-user', role: 'user', text: 'ok', timestamp: new Date(1).toISOString() }] }
    );

    assert.deepStrictEqual(
      adapter.normalizeSnapshot({
        thread: { id: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', queuePaused: true },
        messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 2 }],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178', paused: true, messages: [{ id: 'msg-2-user', role: 'user', text: 'ok', timestamp: new Date(2).toISOString() }] }
    );

    assert.throws(
      () => adapter.normalizeSnapshot({
        thread: { id: '00000000-0000-0000-0000-000000000001', queuePaused: true },
        messages: [{ role: 'user', parts: [{ kind: 'text', text: 'ok' }], ts: 3 }],
      }, { sessionId: '8d8caabd-881d-4fda-bb90-7c7c3f10e178' }),
      /LOCAL_ADAPTER_BAD_SNAPSHOT/
    );
  });
});
