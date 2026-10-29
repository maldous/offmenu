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
