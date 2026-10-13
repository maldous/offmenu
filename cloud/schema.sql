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
