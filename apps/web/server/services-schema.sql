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
