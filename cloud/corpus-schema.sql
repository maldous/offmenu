-- Dedicated public corpus database. Never apply to the account/vault database.
CREATE TABLE IF NOT EXISTS corpus_records(source_id TEXT NOT NULL,release_id TEXT NOT NULL,id TEXT NOT NULL,kind TEXT NOT NULL,barcode TEXT NOT NULL,search_text TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(source_id,release_id,id));
CREATE INDEX IF NOT EXISTS corpus_barcode ON corpus_records(source_id,release_id,barcode,id);
CREATE INDEX IF NOT EXISTS corpus_kind ON corpus_records(source_id,release_id,kind,id);
CREATE TABLE IF NOT EXISTS corpus_releases(source_id TEXT NOT NULL,release_id TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(source_id,release_id));
CREATE TABLE IF NOT EXISTS corpus_active(source_id TEXT PRIMARY KEY,release_id TEXT NOT NULL);
