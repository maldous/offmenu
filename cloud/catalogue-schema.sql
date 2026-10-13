CREATE TABLE IF NOT EXISTS catalogue(kind TEXT NOT NULL,id TEXT NOT NULL,country TEXT NOT NULL,document TEXT NOT NULL,search_text TEXT NOT NULL,version TEXT NOT NULL,PRIMARY KEY(kind,id));
CREATE INDEX IF NOT EXISTS catalogue_country ON catalogue(kind,country,id);
CREATE TABLE IF NOT EXISTS evidence_assertions(owner TEXT NOT NULL,id TEXT NOT NULL,subject TEXT NOT NULL,predicate TEXT NOT NULL,source_id TEXT NOT NULL,policy_id TEXT NOT NULL,market TEXT NOT NULL,document TEXT NOT NULL,fresh_until INTEGER NOT NULL,retain_until INTEGER NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(owner,id));
CREATE INDEX IF NOT EXISTS evidence_subject ON evidence_assertions(owner,subject,market);
CREATE TABLE IF NOT EXISTS source_policies(id TEXT PRIMARY KEY,document TEXT NOT NULL,revision INTEGER NOT NULL,active INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS user_data_settings(owner TEXT PRIMARY KEY,revision INTEGER NOT NULL,document TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS private_documents(owner TEXT NOT NULL,kind TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,document TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(owner,kind,id));
CREATE TABLE IF NOT EXISTS resolver_cache(key TEXT PRIMARY KEY,source_id TEXT NOT NULL,document TEXT,fresh_until INTEGER NOT NULL,retry_after INTEGER NOT NULL,failures INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS import_runs(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,version TEXT NOT NULL,records INTEGER NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL);
INSERT INTO source_policies(id,document,revision,active) VALUES('gleif','{"id": "gleif", "version": "2026-10-13", "license": "CC0-1.0", "actions": ["display", "persist", "export"], "audiences": ["public"], "countries": [], "evidenceUrl": "https://www.gleif.org/en/about/this-is-gleif", "expiresAt": null, "personalFields": "Excluded; selected organization fields only", "promotion": "user-contributed promotion disabled"}',1,1) ON CONFLICT(id) DO NOTHING;
INSERT INTO source_policies(id,document,revision,active) VALUES('wikidata','{"id": "wikidata", "version": "2026-10-13", "license": "CC0-1.0", "actions": ["display", "persist", "export"], "audiences": ["public"], "countries": [], "evidenceUrl": "https://www.wikidata.org/wiki/Wikidata:Data_access", "expiresAt": null, "personalFields": "Excluded; selected organization fields only", "promotion": "user-contributed promotion disabled"}',1,1) ON CONFLICT(id) DO NOTHING;

CREATE TABLE IF NOT EXISTS catalogue_source_countries(source_id TEXT NOT NULL,country TEXT NOT NULL,PRIMARY KEY(source_id,country));
CREATE INDEX IF NOT EXISTS catalogue_source_country ON catalogue_source_countries(country,source_id);

CREATE TABLE IF NOT EXISTS resolver_leases(key TEXT PRIMARY KEY,expires_at INTEGER NOT NULL);
