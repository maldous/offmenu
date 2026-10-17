import { DatabaseSync } from 'node:sqlite';
import { RETENTION_MS, requireThat } from './contracts.mjs';

export class Journal {
  constructor(path, now = Date.now) {
    this.now = now;
    this.db = new DatabaseSync(path, { timeout: 5000 });
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA secure_delete=ON; PRAGMA foreign_keys=ON;
      CREATE TABLE IF NOT EXISTS requests (
        request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
        text TEXT, lease_id TEXT NOT NULL, lease_expires_at INTEGER NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('accepted','sending','delivered','started','completed','failed','uncertain')),
        reason TEXT, evidence TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL, lease_id TEXT NOT NULL,
        state TEXT NOT NULL, reason TEXT, evidence TEXT, created_at INTEGER NOT NULL,
        FOREIGN KEY(request_id) REFERENCES requests(request_id)
      );`);
  }
  transaction(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const result = fn(); this.db.exec('COMMIT'); return result; }
    catch (error) { this.db.exec('ROLLBACK'); throw error; }
  }
  get(requestId) {
    const row = this.db.prepare('SELECT * FROM requests WHERE request_id=?').get(requestId);
    return row && { requestId: row.request_id, sessionId: row.session_id, payloadHash: row.payload_hash,
      text: row.text, leaseId: row.lease_id, leaseExpiresAt: row.lease_expires_at,
      state: row.state, reason: row.reason, evidence: row.evidence, createdAt: row.created_at,
      acceptedAt: row.created_at, expiresAt: row.created_at + RETENTION_MS };
  }
  accept(request) {
    return this.transaction(() => {
      const existing = this.get(request.requestId);
      if (existing) {
        requireThat(existing.payloadHash === request.payloadHash && existing.sessionId === request.sessionId &&
          existing.leaseId === request.leaseId && existing.acceptedAt === request.acceptedAt, 'REQUEST_ID_REUSE');
        return existing;
      }
      const now = this.now();
      this.db.prepare(`INSERT INTO requests (request_id,session_id,payload_hash,text,lease_id,lease_expires_at,state,created_at,updated_at)
        VALUES (?,?,?,?,?,?,'accepted',?,?)`).run(request.requestId, request.sessionId, request.payloadHash, request.text,
      request.leaseId, request.leaseExpiresAt, request.acceptedAt, now);
      return this.get(request.requestId);
    });
  }
  transition(requestId, state, { reason = null, evidence = null } = {}) {
    const transitions = { accepted: ['sending', 'failed'], sending: ['delivered', 'uncertain'],
      uncertain: ['delivered'], delivered: ['started', 'completed', 'failed'], started: ['completed', 'failed'], completed: [], failed: [] };
    return this.transaction(() => {
      const row = this.get(requestId);
      requireThat(row && transitions[row.state]?.includes(state), 'INVALID_STATE_TRANSITION');
      requireThat(reason === null || /^[A-Z0-9_]{1,128}$/.test(reason), 'UNSAFE_REASON');
      requireThat(evidence === null || (typeof evidence === 'string' && /^[A-Za-z0-9._:-]{1,512}$/.test(evidence)), 'UNSAFE_EVIDENCE');
      const now = this.now();
      this.db.prepare('UPDATE requests SET state=?,reason=?,evidence=?,updated_at=? WHERE request_id=?').run(state, reason, evidence, now, requestId);
      if (state !== 'sending') this.db.prepare('INSERT INTO reports(request_id,lease_id,state,reason,evidence,created_at) VALUES(?,?,?,?,?,?)')
        .run(requestId, row.leaseId, state, reason, evidence, row.createdAt);
      return this.get(requestId);
    });
  }
  recover() {
    for (const row of this.db.prepare("SELECT request_id FROM requests WHERE state='sending'").all()) {
      this.transition(row.request_id, 'uncertain', { reason: 'PROCESS_INTERRUPTED_AFTER_INTENT' });
    }
  }
  pending() {
    return this.db.prepare("SELECT request_id FROM requests WHERE state IN ('accepted','uncertain','delivered','started') AND text IS NOT NULL ORDER BY created_at LIMIT 100")
      .all().map(row => this.get(row.request_id));
  }
  reports() {
    return this.db.prepare('SELECT * FROM reports ORDER BY id LIMIT 100').all().map(row => ({ id: row.id,
      payload: { requestId: row.request_id, leaseId: row.lease_id, state: row.state,
        ...(row.reason ? { reason: row.reason } : {}), ...(row.evidence ? { evidence: row.evidence } : {}) } }));
  }
  acknowledge(reportId) { this.db.prepare('DELETE FROM reports WHERE id=?').run(reportId); }
  prune() {
    const cutoff = this.now() - RETENTION_MS;
    for (const row of this.db.prepare("SELECT request_id FROM requests WHERE state='accepted' AND created_at<?").all(cutoff)) {
      this.transition(row.request_id, 'failed', { reason: 'REQUEST_RETENTION_EXPIRED' });
    }
    // Tombstones deliberately remain: deleting them would permit duplicate local delivery.
    this.db.prepare('UPDATE requests SET text=NULL,evidence=NULL WHERE created_at<?').run(cutoff);
    this.db.prepare('DELETE FROM reports WHERE created_at<?').run(cutoff);
    this.db.exec('PRAGMA wal_checkpoint(TRUNCATE)');
  }
  close() { this.db.close(); }
}
