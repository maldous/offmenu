// Local adapter built from verified live endpoint responses.
// Verified response shape: top-level { thread, messages, items }; pause and queue
// state live on the thread object (thread.queuePaused / thread.pendingWorkCount)
// and there is no separate queue object.
// Verified credential file schema: { "port": <int 1..65535>, "launchId": "<uuid>" }.
// Credential text is handled only by the caller and never logged.
export default {
  schemaVersion: 1,
  verified: true,

  extractCredential(rawPrivateFileText) {
    let parsed;
    try {
      parsed = JSON.parse(rawPrivateFileText);
    } catch {
      throw new Error('LOCAL_ADAPTER_BAD_CREDENTIAL_FILE');
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('LOCAL_ADAPTER_BAD_CREDENTIAL_FILE');
    }
    if (typeof parsed.port !== 'number' || !Number.isFinite(parsed.port) || parsed.port <= 0 || parsed.port >= 65536) {
      throw new Error('LOCAL_ADAPTER_BAD_CREDENTIAL_FILE');
    }
    if (typeof parsed.launchId !== 'string' || !parsed.launchId) {
      throw new Error('LOCAL_ADAPTER_BAD_CREDENTIAL_FILE');
    }
    return {
      'x-freebuff-launch-id': parsed.launchId,
    };
  },

  // Interface fixed by the shipped poller (poller/README.md): the caller invokes
  // normalizeSnapshot(rawResponse, { sessionId }). A bare sessionId string is a
  // contract violation and fails closed.
  normalizeSnapshot(rawResponse, { sessionId } = {}) {

    if (!rawResponse || typeof rawResponse !== 'object' || Array.isArray(rawResponse)) {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    const thread = rawResponse.thread;
    if (!thread || typeof thread !== 'object' || Array.isArray(thread)) {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    if (!sessionId || typeof sessionId !== 'string') {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    const threadId = typeof thread.id === 'string' && thread.id
      ? thread.id
      : null;

    if (threadId && threadId !== sessionId) {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    let paused = null;
    if (Object.prototype.hasOwnProperty.call(thread, 'queuePaused')) {
      const qp = thread.queuePaused;
      if (qp === true) paused = true;
      else if (qp === false) paused = false;
      else throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    const rawMessages = rawResponse.messages;
    if (!rawMessages || !Array.isArray(rawMessages)) {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }
    if (!rawMessages.length) {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    const messages = [];
    const seenIds = new Set();

    for (const m of rawMessages) {
      if (!m || typeof m !== 'object' || Array.isArray(m)) {
        throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
      }
      const role = m.role;
      if (role !== 'user' && role !== 'assistant' && role !== 'system') {
        throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
      }

      // Verified rule: a message with no ts yet (still in flight, observed on the
      // trailing message of verified live captures) is skipped until it settles;
      // a present ts that is not a finite number is a schema violation and
      // rejects the snapshot; a finite ts at or below zero is skipped instead.
      if (m.ts === undefined) {
        continue;
      }
      const tsMillis = Number(m.ts);
      if (!Number.isFinite(tsMillis)) {
        throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
      }
      if (tsMillis <= 0) {
        continue;
      }

      let timestamp;
      try {
        timestamp = new Date(tsMillis).toISOString();
      } catch {
        continue;
      }
      if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(timestamp)) {
        continue;
      }

      // Verified rule: only text parts of user and assistant messages are
      // content; reasoning parts and system text are not extracted. A message
      // with no extractable text is dropped.
      let text = '';
      const parts = m.parts;
      if (Array.isArray(parts) && (role === 'user' || role === 'assistant')) {
        const textParts = [];
        for (const p of parts) {
          if (p && typeof p === 'object' && p.kind === 'text' && typeof p.text === 'string') {
            textParts.push(p.text);
          }
        }
        text = textParts.join('');
      }
      if (text === '') {
        continue;
      }

      // Verified rule (2026-10-17 contract update, Morgan-approved): the
      // temporary id is msg-<ts>-<role>. Cross-role same-millisecond pairs
      // (turn boundaries, observed live on bac212ab) carry distinct ids and
      // are kept; two kept messages may not share one temporary id (same ts
      // AND role), which rejects the snapshot instead of silently dropping
      // delivery evidence.
      const messageId = `msg-${tsMillis}-${String(role)}`;
      if (seenIds.has(messageId)) {
        throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
      }
      seenIds.add(messageId);

      messages.push({
        id: messageId,
        role,
        text,
        timestamp,
      });
    }

    if (!messages.length) {
      throw new Error('LOCAL_ADAPTER_BAD_SNAPSHOT');
    }

    return {
      sessionId: threadId || sessionId,
      paused,
      messages,
    };
  },
};
