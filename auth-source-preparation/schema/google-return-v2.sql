-- Code-only feature schema for the EXISTING application database. Not applied.
-- Hash + five-minute expiry only; never provider state, tokens, subject or email.
CREATE TABLE IF NOT EXISTS offmenu_google_return_v2 (
  nonce_hash TEXT PRIMARY KEY CHECK(length(nonce_hash)=64),
  expires_at_ms INTEGER NOT NULL
);
