import { createHash } from 'node:crypto';

// Morgan's exact target binding (2026-10-17): the fixed project restriction is
// the worker-62 checkout, target session bac212ab-b73c-4f64-a995-e57ee9ec0877.
export const PROJECT_PATH = '/home/user/src/offmenu-workers/worker-62';
export const EXCLUDED_SESSION_ID = '8d8caabd-881d-4fda-bb90-7c7c3f10e178';
export const MAX_TEXT_BYTES = 16 * 1024;
export const MAX_BRIDGE_BYTES = 256 * 1024;
export const MAX_LOCAL_BYTES = 1024 * 1024;
export const RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export class SafeError extends Error {
  constructor(code) { super(code); this.code = code; }
}
export class HttpError extends SafeError {
  constructor(status, serviceCode = null) {
    super(`HTTP_${status}`); this.status = status; this.serviceCode = serviceCode;
  }
}
export function requireThat(condition, code) { if (!condition) throw new SafeError(code); }
export function payloadHash(sessionId, text) {
  return createHash('sha256').update(JSON.stringify({ sessionId, text }), 'utf8').digest('hex');
}
export function requestMarker(request) {
  return `[freebuff-relay requestId=${request.requestId} payloadHash=${request.payloadHash}]`;
}
export function queueText(request) { return `${request.text}\n\n${requestMarker(request)}`; }

export function validateConfig(input) {
  requireThat(input && input.schemaVersion === 1, 'CONFIG_SCHEMA');
  const gateway = new URL(input.gatewayUrl);
  requireThat(gateway.protocol === 'https:' && !gateway.username && !gateway.password &&
    !gateway.search && !gateway.hash && gateway.pathname === '/', 'GATEWAY_ORIGIN_REQUIRED');
  const api = new URL(input.localApiUrl);
  requireThat(api.protocol === 'http:' && ['127.0.0.1', '[::1]'].includes(api.hostname) &&
    !api.username && !api.password && !api.search && !api.hash && api.pathname === '/', 'LOOPBACK_LITERAL_REQUIRED');
  requireThat(input.projectPath === PROJECT_PATH, 'PROJECT_NOT_ALLOWED');
  requireThat(Array.isArray(input.sessionIds) && input.sessionIds.length >= 1 && input.sessionIds.length <= 3 &&
    input.sessionIds.every(id => typeof id === 'string' && UUID4.test(id) && id !== EXCLUDED_SESSION_ID) &&
    new Set(input.sessionIds).size === input.sessionIds.length, 'SESSION_ALLOWLIST_INVALID');
  const paused = input.pausedSessionIds ?? [];
  requireThat(Array.isArray(paused) && paused.every(id => input.sessionIds.includes(id)), 'PAUSED_ALLOWLIST_INVALID');
  for (const key of ['stateDir', 'localCredentialFile', 'pollerTokenFile', 'adapterFile']) {
    requireThat(typeof input[key] === 'string' && input[key].startsWith('/') && !input[key].includes('\0'), 'ABSOLUTE_PATH_REQUIRED');
  }
  requireThat(input.localCredentialFile !== input.pollerTokenFile, 'CREDENTIALS_MUST_BE_INDEPENDENT');
  const intervalMs = input.intervalMs ?? 30000;
  requireThat(Number.isInteger(intervalMs) && intervalMs >= 1000 && intervalMs <= 60000, 'POLL_INTERVAL_INVALID');
  const snapshotIntervalMs = input.snapshotIntervalMs ?? 60000;
  requireThat(Number.isInteger(snapshotIntervalMs) && snapshotIntervalMs >= 1000 && snapshotIntervalMs <= 60000, 'SNAPSHOT_INTERVAL_INVALID');
  return Object.freeze({ ...input, gatewayUrl: gateway.origin, localApiUrl: api.origin,
    sessionIds: Object.freeze([...input.sessionIds]), pausedSessionIds: Object.freeze([...paused]), intervalMs, snapshotIntervalMs });
}

export function validateLease(lease, config, now = Date.now()) {
  requireThat(lease && typeof lease === 'object' && UUID4.test(lease.requestId), 'REQUEST_ID_INVALID');
  requireThat(config.sessionIds.includes(lease.sessionId) && lease.sessionId !== EXCLUDED_SESSION_ID, 'SESSION_NOT_ALLOWED');
  requireThat(typeof lease.text === 'string' && lease.text.trim().length > 0 &&
    Buffer.byteLength(lease.text) <= MAX_TEXT_BYTES && !lease.text.includes('[freebuff-relay'), 'PAYLOAD_INVALID');
  requireThat(typeof lease.payloadHash === 'string' && lease.payloadHash === payloadHash(lease.sessionId, lease.text), 'PAYLOAD_HASH_MISMATCH');
  requireThat(typeof lease.leaseId === 'string' && UUID4.test(lease.leaseId), 'LEASE_ID_INVALID');
  const expiry = typeof lease.leaseExpiresAt === 'number' ? lease.leaseExpiresAt : Date.parse(lease.leaseExpiresAt);
  requireThat(Number.isFinite(expiry) && expiry > 0 && expiry <= now + 24 * 60 * 60 * 1000, 'LEASE_EXPIRY_INVALID');
  requireThat(Number.isSafeInteger(lease.acceptedAt) && lease.acceptedAt > 0 && lease.acceptedAt <= now + 5000 &&
    Number.isSafeInteger(lease.expiresAt) && lease.expiresAt === lease.acceptedAt + RETENTION_MS, 'REQUEST_EXPIRY_INVALID');
  return { requestId: lease.requestId, sessionId: lease.sessionId, text: lease.text,
    payloadHash: lease.payloadHash, leaseId: lease.leaseId, leaseExpiresAt: expiry,
    acceptedAt: lease.acceptedAt, expiresAt: lease.expiresAt };
}

export function verifyAdapter(adapter) {
  requireThat(adapter && adapter.verified === true && adapter.schemaVersion === 1 &&
    typeof adapter.extractCredential === 'function' && typeof adapter.normalizeSnapshot === 'function', 'LOCAL_ADAPTER_UNVERIFIED');
}

export function validateCredentialHeaders(headers) {
  requireThat(headers && typeof headers === 'object' && !Array.isArray(headers), 'LOCAL_AUTH_INVALID');
  const entries = Object.entries(headers);
  requireThat(entries.length >= 1 && entries.length <= 2, 'LOCAL_AUTH_INVALID');
  // Deliberate reviewed addition (2026-10-17, foo): the verified live loopback API
  // authenticates ONLY with x-freebuff-launch-id (HTTP 200); every original
  // allowlisted name returns 401. The shipped README sanctions exactly this:
  // "Any extra credential-header requirement must be reviewed and deliberately
  // added." See VENDORING.md for the verification matrix and provenance.
  const allowed = new Set(['authorization', 'cookie', 'x-api-key', 'x-freebuff-token', 'x-freebuff-session', 'x-freebuff-launch-id']);
  const result = {};
  for (const [name, value] of entries) {
    requireThat(allowed.has(name.toLowerCase()) && !Object.hasOwn(result, name.toLowerCase()) &&
      typeof value === 'string' && value.length >= 8 && value.length <= 8192 && !/[\r\n\0]/.test(value), 'LOCAL_AUTH_INVALID');
    result[name.toLowerCase()] = value;
  }
  return result;
}

export function validateSnapshot(snapshot, sessionId) {
  requireThat(snapshot && snapshot.sessionId === sessionId &&
    [true, false, null].includes(snapshot.paused) && Array.isArray(snapshot.messages) && snapshot.messages.length <= 1000,
  'LOCAL_SNAPSHOT_INVALID');
  const messages = snapshot.messages.map(message => {
    requireThat(message && typeof message.id === 'string' && /^[A-Za-z0-9._:-]{1,128}$/.test(message.id) &&
      ['user', 'assistant', 'system'].includes(message.role) && typeof message.text === 'string' &&
      Buffer.byteLength(message.text) <= 64 * 1024 && typeof message.timestamp === 'string' &&
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(message.timestamp) &&
      Number.isFinite(Date.parse(message.timestamp)), 'LOCAL_MESSAGE_INVALID');
    return { id: message.id, role: message.role, text: message.text, timestamp: message.timestamp };
  });
  return { sessionId, paused: snapshot.paused, messages };
}

export function markerEvidence(snapshot, request) {
  const marker = requestMarker(request);
  // A marker in assistant prose is not proof of a user message being queued.
  const hit = snapshot.messages.find(message => message.role === 'user' &&
    message.text === queueText(request) && message.text.endsWith(`\n\n${marker}`));
  return hit ? `exact_marker:${hit.id}` : null;
}

export function remoteSnapshot(snapshot, now, secrets = []) {
  const redact = value => secrets.reduce((result, secret) => secret.length >= 8 ? result.split(secret).join('[redacted credential]') : result, value);
  return { sessionId: snapshot.sessionId, paused: snapshot.paused, observedAt: now,
    messages: snapshot.messages.slice(-40).map(message => ({ ...message,
      id: redact(message.id),
      text: (() => { const text = redact(message.text); return text.length <= 4096 ? text : `[truncated]\n${text.slice(-4084)}`; })()
    })) };
}
