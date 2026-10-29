CREATE TABLE IF NOT EXISTS user_state (user_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, state_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (barcode TEXT PRIMARY KEY, data TEXT NOT NULL, source TEXT NOT NULL, license TEXT NOT NULL, checked_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS recipes (id TEXT PRIMARY KEY, title TEXT NOT NULL, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS price_observations (barcode TEXT PRIMARY KEY, data TEXT NOT NULL, source TEXT NOT NULL, license TEXT NOT NULL, checked_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS integration_tokens (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, user_id TEXT NOT NULL, name TEXT NOT NULL, scopes TEXT NOT NULL, resource TEXT NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, revoked_at INTEGER);
CREATE INDEX IF NOT EXISTS integration_tokens_user ON integration_tokens(user_id);
CREATE TABLE IF NOT EXISTS oauth_clients (id TEXT PRIMARY KEY, name TEXT NOT NULL, redirect_uris TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS oauth_codes (code_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, client_id TEXT NOT NULL, redirect_uri TEXT NOT NULL, challenge TEXT NOT NULL, scopes TEXT NOT NULL, resource TEXT NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS integration_limits (key TEXT NOT NULL, bucket INTEGER NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(key,bucket));
CREATE TABLE IF NOT EXISTS provider_connections (user_id TEXT NOT NULL, source_id TEXT NOT NULL, label TEXT NOT NULL, sealed TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(user_id,source_id));
CREATE TABLE IF NOT EXISTS unified_records (owner TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL, source_id TEXT NOT NULL, countries TEXT NOT NULL, document TEXT NOT NULL, updated_at TEXT NOT NULL, search_text TEXT NOT NULL DEFAULT '', PRIMARY KEY(owner,id));
CREATE INDEX IF NOT EXISTS unified_records_owner_kind ON unified_records(owner,kind);
CREATE TABLE IF NOT EXISTS kitchens (id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL, state_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS kitchen_members (kitchen_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')), PRIMARY KEY(kitchen_id,user_id));
CREATE TABLE IF NOT EXISTS kitchen_invites (token_hash TEXT PRIMARY KEY, kitchen_id TEXT NOT NULL, role TEXT NOT NULL, expires_at INTEGER NOT NULL, used_at INTEGER);

CREATE TABLE IF NOT EXISTS source_policies(id TEXT PRIMARY KEY,document TEXT NOT NULL,revision INTEGER NOT NULL,active INTEGER NOT NULL);

-- Third-party service delivery ledger (additive; preserve existing account data).
-- Additive private-service tables. Apply alongside schema.sql; do not replace it.
CREATE TABLE IF NOT EXISTS service_requests (
  id TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('support','email')),
  idempotency_key TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','sent','failed','unknown')),
  -- Payload is erased at retention expiry; the row remains as an idempotency tombstone.
  sealed TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  retain_until INTEGER NOT NULL,
  UNIQUE(owner,kind,idempotency_key)
);
CREATE INDEX IF NOT EXISTS service_requests_owner_kind_created
  ON service_requests(owner,kind,created_at DESC);
CREATE TABLE IF NOT EXISTS service_rate_limits (
  owner TEXT NOT NULL,
  kind TEXT NOT NULL,
  bucket INTEGER NOT NULL,
  count INTEGER NOT NULL,
  PRIMARY KEY(owner,kind,bucket)
);

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

-- Integrated customer care, community and delegated AI schemas.

-- admin-mcp
CREATE TABLE IF NOT EXISTS admin_mcp_proofs (
  token_id TEXT PRIMARY KEY, sealed TEXT NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS oauth_admin_proofs (
  code_hash TEXT PRIMARY KEY, sealed TEXT NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_mcp_audit (
  id TEXT PRIMARY KEY,
  token_id TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  tool TEXT NOT NULL,
  resource_id TEXT,
  action TEXT,
  status TEXT NOT NULL CHECK(status IN ('started','succeeded','failed')),
  created_at INTEGER NOT NULL,
  completed_at INTEGER
);
CREATE INDEX IF NOT EXISTS admin_mcp_audit_token_created ON admin_mcp_audit(token_id,created_at DESC);

-- care-cases
CREATE TABLE IF NOT EXISTS care_cases (id TEXT PRIMARY KEY,owner TEXT,idempotency_key TEXT,payload_hash TEXT,category TEXT NOT NULL,status TEXT NOT NULL,assigned_to TEXT,revision INTEGER NOT NULL,write_id TEXT NOT NULL,sealed TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,retain_until INTEGER NOT NULL,UNIQUE(owner,idempotency_key));
CREATE TABLE IF NOT EXISTS care_messages (id TEXT PRIMARY KEY,case_id TEXT NOT NULL,author_role TEXT NOT NULL CHECK(author_role IN ('owner','staff','internal')),idempotency_key TEXT,payload_hash TEXT,write_id TEXT NOT NULL,sealed TEXT,created_at TEXT NOT NULL,retain_until INTEGER NOT NULL,UNIQUE(case_id,idempotency_key));
CREATE TABLE IF NOT EXISTS care_case_locks (id TEXT PRIMARY KEY CHECK(id='global'),nonce TEXT NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS care_audit (id TEXT PRIMARY KEY,case_id TEXT NOT NULL,actor_id TEXT NOT NULL,revision INTEGER NOT NULL,paths_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS care_cases_staff ON care_cases(status,updated_at DESC);

-- care-community
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

-- care-updates
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

-- recipe-community
-- Public, reviewed community recipes.  Deliberately separate from a user's pantry,
-- health profile, provider connections, and private journey achievements.
CREATE TABLE IF NOT EXISTS community_profiles (
 owner_id TEXT PRIMARY KEY, community_id TEXT NOT NULL UNIQUE, alias TEXT NOT NULL, bio TEXT NOT NULL DEFAULT '', published INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS community_recipes (
 id TEXT PRIMARY KEY, author_id TEXT NOT NULL, alias TEXT NOT NULL, recipe_json TEXT NOT NULL, attribution_json TEXT NOT NULL DEFAULT '{"kind":"human"}', source_ref TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','published','hidden','rejected')), revision INTEGER NOT NULL, write_id TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS community_recipes_public ON community_recipes(status,created_at,id);
CREATE TABLE IF NOT EXISTS community_recipe_idempotency (
 owner_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, body_hash TEXT NOT NULL, recipe_id TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(owner_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS community_recipe_budget (owner_id TEXT NOT NULL, month TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(owner_id,month));
CREATE TABLE IF NOT EXISTS community_recipe_locks (subject TEXT PRIMARY KEY, nonce TEXT NOT NULL, created_at TEXT NOT NULL);
-- Shared community restriction predicate, intentionally not linked to private data.
CREATE TABLE IF NOT EXISTS care_restrictions (subject TEXT PRIMARY KEY, reason TEXT NOT NULL, until_at TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS community_recipe_votes (
 recipe_id TEXT NOT NULL, owner_id TEXT NOT NULL, value INTEGER NOT NULL CHECK(value IN (-1,1)), rating INTEGER, updated_at TEXT NOT NULL,
 PRIMARY KEY(recipe_id,owner_id)
);
CREATE TABLE IF NOT EXISTS community_recipe_comments (
 id TEXT PRIMARY KEY, recipe_id TEXT NOT NULL, author_id TEXT NOT NULL, alias TEXT NOT NULL, body TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','published','hidden','rejected')), revision INTEGER NOT NULL, write_id TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS community_recipe_comments_public ON community_recipe_comments(recipe_id,status,created_at,id);
CREATE TABLE IF NOT EXISTS community_recipe_comment_idempotency (owner_id TEXT NOT NULL, recipe_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, body_hash TEXT NOT NULL, comment_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner_id,recipe_id,idempotency_key));
CREATE TABLE IF NOT EXISTS community_recipe_audit (id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, subject_id TEXT NOT NULL, kind TEXT NOT NULL, revision INTEGER NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS community_recipe_audit_subject ON community_recipe_audit(subject_id,created_at);

-- personal-ai
-- Personal AI preferences are encrypted at rest and bound to their owner.
CREATE TABLE IF NOT EXISTS personal_ai_preferences (
  owner_id TEXT PRIMARY KEY,
  sealed TEXT NOT NULL,
  revision INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

-- community-ai
-- AI review stores decisions, never prompts or private account data.
CREATE TABLE IF NOT EXISTS community_ai_settings (
  id TEXT PRIMARY KEY CHECK(id='global'), revision INTEGER NOT NULL, settings_json TEXT NOT NULL,
  write_id TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS community_ai_audit (
  id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, revision INTEGER NOT NULL, paths_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS community_ai_budget (
  day TEXT PRIMARY KEY, used INTEGER NOT NULL, lease TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS community_ai_decisions (
  id TEXT PRIMARY KEY, candidate_kind TEXT NOT NULL, candidate_id TEXT NOT NULL, candidate_revision INTEGER NOT NULL,
  decision TEXT NOT NULL, confidence REAL NOT NULL, reason TEXT NOT NULL, model TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('claimed','applying','held','applied','failed','awaiting_agent')), lease_until INTEGER, created_at TEXT NOT NULL,
  UNIQUE(candidate_kind,candidate_id,candidate_revision)
);
CREATE INDEX IF NOT EXISTS community_ai_decisions_review ON community_ai_decisions(state,created_at);
