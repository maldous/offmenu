-- Text-only public community. This is isolated from kitchens, profiles, and provider data.
CREATE TABLE IF NOT EXISTS care_topics (
  id TEXT PRIMARY KEY, author_id TEXT NOT NULL, alias TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
  category TEXT NOT NULL CHECK(category IN ('suggestion','discussion')), status TEXT NOT NULL CHECK(status IN ('pending','published','hidden')),
  revision INTEGER NOT NULL, locked INTEGER NOT NULL DEFAULT 0, pinned INTEGER NOT NULL DEFAULT 0, merged_into TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS care_topics_public ON care_topics(status,pinned,created_at,id);
CREATE TABLE IF NOT EXISTS care_replies (
  id TEXT PRIMARY KEY, topic_id TEXT NOT NULL, author_id TEXT NOT NULL, alias TEXT NOT NULL, body TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','published','hidden')), revision INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS care_replies_topic ON care_replies(topic_id,status,created_at,id);
CREATE TABLE IF NOT EXISTS care_idempotency (
  owner_id TEXT NOT NULL, scope TEXT NOT NULL, idempotency_key TEXT NOT NULL, body_hash TEXT NOT NULL, result_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(owner_id,scope,idempotency_key)
);
-- HMAC-only retry tombstones for expired sealed reports; no account identifier or request body remains.
CREATE TABLE IF NOT EXISTS care_expired_tombstones (digest TEXT PRIMARY KEY, expired_at TEXT NOT NULL);
-- Reserved operational counter namespace for community-only retention/metrics jobs.
-- Posting capacity itself is atomically derived from accepted community rows.
CREATE TABLE IF NOT EXISTS care_community_budgets (subject TEXT NOT NULL, month TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(subject,month));
CREATE TABLE IF NOT EXISTS care_follows (owner_id TEXT NOT NULL, topic_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner_id,topic_id));
CREATE TABLE IF NOT EXISTS care_flags (
  id TEXT PRIMARY KEY, topic_id TEXT NOT NULL, reporter_id TEXT NOT NULL, reason TEXT NOT NULL, sealed TEXT,
  status TEXT NOT NULL CHECK(status IN ('open','resolved')), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, retain_until INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS care_appeals (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, sealed TEXT, status TEXT NOT NULL CHECK(status IN ('open','resolved')),
  revision INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, retain_until INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS care_restrictions (subject TEXT PRIMARY KEY, reason TEXT NOT NULL, until_at TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS care_mutation_locks (subject TEXT PRIMARY KEY, nonce TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS care_admin_audit (
  id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, subject TEXT NOT NULL, kind TEXT NOT NULL, revision INTEGER, action TEXT NOT NULL, reason TEXT NOT NULL DEFAULT 'Reviewed moderation action', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS care_admin_audit_subject ON care_admin_audit(subject,created_at DESC);
