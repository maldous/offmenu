-- Additive singleton settings and value-free administrative audit trail.
CREATE TABLE IF NOT EXISTS app_settings (
  id TEXT PRIMARY KEY CHECK(id='global'),
  revision INTEGER NOT NULL CHECK(revision >= 1),
  settings_json TEXT NOT NULL,
  sealed_credentials TEXT,
  write_id TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings_audit (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  paths_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS app_settings_audit_revision ON app_settings_audit(revision DESC);
