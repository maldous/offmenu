CREATE TABLE IF NOT EXISTS care_updates (
  id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  payload_hash TEXT NOT NULL,
  title TEXT NOT NULL,
  text TEXT NOT NULL,
  locale TEXT NOT NULL CHECK(locale IN ('en','ar')),
  state TEXT NOT NULL CHECK(state IN ('draft','published','withdrawn')),
  publish_at TEXT NOT NULL,
  release_ref TEXT,
  attribution_json TEXT NOT NULL DEFAULT '{"kind":"human"}',
  revision INTEGER NOT NULL,
  write_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS care_updates_feed ON care_updates(state,publish_at DESC,locale);
CREATE TABLE IF NOT EXISTS care_update_audit (
  id TEXT PRIMARY KEY, update_id TEXT NOT NULL, actor_id TEXT NOT NULL,
  revision INTEGER NOT NULL, action TEXT NOT NULL, paths_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_update_locks (update_id TEXT PRIMARY KEY, nonce TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS care_preferences (
  owner TEXT PRIMARY KEY, case_notifications INTEGER NOT NULL DEFAULT 1,
  community_notifications INTEGER NOT NULL DEFAULT 1, update_notifications INTEGER NOT NULL DEFAULT 1,
  email_updates INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_notifications (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('case','community','update')),
  resource_id TEXT NOT NULL, created_at TEXT NOT NULL, seen_at TEXT,
  UNIQUE(owner,kind,resource_id)
);
CREATE INDEX IF NOT EXISTS care_notifications_owner ON care_notifications(owner,seen_at,created_at DESC);
