-- Short-lived mutation guard and value-free record of public-policy operations.
-- These tables deliberately have no owner, user, credential, or policy-document data.
CREATE TABLE IF NOT EXISTS admin_operations_locks (
  source_id TEXT PRIMARY KEY,
  nonce TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_operations_audit (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  action TEXT NOT NULL CHECK(action IN ('suspended','reactivated')),
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS admin_operations_audit_source_revision
  ON admin_operations_audit(source_id, revision DESC);
