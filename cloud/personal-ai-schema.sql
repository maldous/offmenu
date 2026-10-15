-- Personal AI preferences are encrypted at rest and bound to their owner.
CREATE TABLE IF NOT EXISTS personal_ai_preferences (
  owner_id TEXT PRIMARY KEY,
  sealed TEXT NOT NULL,
  revision INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
