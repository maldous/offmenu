import { markerEvidence, queueText, remoteSnapshot, requireThat, validateLease, HttpError } from './contracts.mjs';

export class Poller {
  constructor({ config, journal, local, gateway, now = Date.now, event = () => {} }) {
    this.config = config; this.journal = journal; this.local = local; this.gateway = gateway;
    this.now = now; this.event = event; this.running = false; this.lastSnapshotAt = new Map();
  }
  async flushReports() {
    for (const report of this.journal.reports()) {
      let receipt;
      try { receipt = await this.gateway.report(report.payload); }
      catch (error) {
        if (error instanceof HttpError && ((error.status === 404 && error.serviceCode === 'REQUEST_NOT_FOUND') ||
          (error.status === 403 && error.serviceCode === 'SESSION_NOT_ALLOWED'))) {
          // The gateway definitively no longer accepts this receipt. Keep the identity tombstone
          // so retiring a remote report can never authorize another local delivery.
          this.journal.acknowledge(report.id);
          this.event('REPORT_UNAVAILABLE_TERMINAL');
          continue;
        }
        throw error;
      }
      const request = this.journal.get(report.payload.requestId);
      requireThat(receipt && receipt.requestId === report.payload.requestId && receipt.payloadHash === request.payloadHash &&
        receipt.state === report.payload.state, 'REPORT_ACK_MISMATCH');
      this.journal.acknowledge(report.id);
    }
  }
  evidence(snapshot, request) {
    const evidence = markerEvidence(snapshot, request);
    return evidence && !(this.local.secrets ?? []).some(secret => secret.length >= 8 && evidence.includes(secret)) ? evidence : null;
  }
  async reconcile(request, snapshot) {
    const evidence = this.evidence(snapshot, request);
    if (request.state === 'uncertain' && evidence) this.journal.transition(request.requestId, 'delivered', { evidence });
    // No marker is never proof of absence: a snapshot may be truncated or eventually consistent.
    // No run lifecycle is inferred from queue success, assistant text, or an idle/busy flag.
  }
  async handle(request) {
    let saved = this.journal.accept(request);
    if (saved.state !== 'accepted') {
      if (saved.state === 'uncertain' && saved.text !== null) {
        await this.reconcile(saved, await this.local.snapshot(saved.sessionId));
      }
      return;
    }
    if (this.config.pausedSessionIds.includes(saved.sessionId)) {
      this.journal.transition(saved.requestId, 'failed', { reason: 'SESSION_CONFIGURED_PAUSED' }); return;
    }
    if (Math.min(saved.leaseExpiresAt, saved.expiresAt) <= this.now()) {
      this.journal.transition(saved.requestId, 'failed', { reason: 'LEASE_EXPIRED_BEFORE_ATTEMPT' }); return;
    }
    const snapshot = await this.local.snapshot(saved.sessionId);
    if (snapshot.paused !== false) {
      this.journal.transition(saved.requestId, 'failed', { reason: snapshot.paused === true ? 'SESSION_PAUSED' : 'PAUSE_STATE_UNKNOWN' }); return;
    }
    if (Math.min(saved.leaseExpiresAt, saved.expiresAt) <= this.now()) {
      this.journal.transition(saved.requestId, 'failed', { reason: 'LEASE_EXPIRED_BEFORE_ATTEMPT' }); return;
    }
    // This FULL-synchronous transaction commits before the only state-changing local API call.
    saved = this.journal.transition(saved.requestId, 'sending');
    try {
      await this.local.queue(saved.sessionId, queueText(saved));
      // A 2xx alone has an unverified semantic contract; require exact user-message readback.
      const readback = await this.local.snapshot(saved.sessionId);
      const evidence = this.evidence(readback, saved);
      this.journal.transition(saved.requestId, evidence ? 'delivered' : 'uncertain', evidence ? { evidence } : { reason: 'QUEUE_RESPONSE_WITHOUT_READBACK' });
    } catch {
      this.journal.transition(saved.requestId, 'uncertain', { reason: 'QUEUE_ATTEMPT_OUTCOME_UNKNOWN' });
    }
  }
  async tick() {
    requireThat(!this.running, 'CONCURRENT_TICK'); this.running = true;
    try {
      this.journal.prune();
      await this.flushReports();
      for (const sessionId of this.config.sessionIds) {
        const last = this.lastSnapshotAt.get(sessionId);
        if (last !== undefined && this.now() - last < this.config.snapshotIntervalMs) continue;
        try {
          const snapshot = await this.local.snapshot(sessionId);
          if (this.config.pausedSessionIds.includes(sessionId)) snapshot.paused = true;
          await this.gateway.snapshot(remoteSnapshot(snapshot, this.now(), this.local.secrets));
          this.lastSnapshotAt.set(sessionId, this.now());
          for (const request of this.journal.pending().filter(row => row.sessionId === sessionId && row.state === 'uncertain')) {
            await this.reconcile(request, snapshot);
          }
        } catch { this.event('SESSION_SNAPSHOT_UNAVAILABLE'); }
      }
      await this.flushReports();
      // Accepted records survived a pre-attempt crash and may safely continue within their lease.
      for (const request of this.journal.pending().filter(row => row.state === 'accepted')) await this.handle(request);
      const response = await this.gateway.poll();
      requireThat(response && Object.hasOwn(response, 'lease') && Array.isArray(response.commands) && response.commands.length === 0,
        'POLL_RESPONSE_INVALID');
      if (response.lease !== null) await this.handle(validateLease(response.lease, this.config, this.now()));
      await this.flushReports();
    } finally { this.running = false; }
  }
}
