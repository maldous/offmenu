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
