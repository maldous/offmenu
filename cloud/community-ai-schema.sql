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
