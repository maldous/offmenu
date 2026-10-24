-- Local curated proposal schema. Worker00 alone writes actual gold.

PRAGMA foreign_keys = ON;

CREATE TABLE gold_runs (
  run_id TEXT PRIMARY KEY NOT NULL,
  packet_sha256 TEXT NOT NULL,
  qualification_sha256 TEXT NOT NULL,
  data_class TEXT NOT NULL CHECK(data_class IN ('synthetic','real-qualified')),
  watermark_json TEXT NOT NULL CHECK(json_valid(watermark_json))
);

CREATE TABLE gold_citations (
  citation_id TEXT PRIMARY KEY NOT NULL,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);

CREATE TABLE gold_entities (
  entity_id TEXT PRIMARY KEY NOT NULL,
  resource_id TEXT NOT NULL,
  domain TEXT NOT NULL CHECK(domain IN ('barcodes','ingredients','recipes','dietary','suppliers','citations')),
  entity_type TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('verified','inferred','held','conflict')),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);

CREATE TABLE gold_occurrences (
  occurrence_id TEXT PRIMARY KEY NOT NULL,
  domain TEXT NOT NULL CHECK(domain IN ('barcodes','ingredients','recipes','dietary','suppliers','citations')),
  source_key TEXT NOT NULL,
  source_version TEXT NOT NULL,
  record_id TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  normalized_artifact_sha256 TEXT,
  committed_watermark TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('verified','inferred','held','conflict')),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);

CREATE TABLE gold_entity_occurrences (
  entity_id TEXT,
  occurrence_id TEXT NOT NULL,
  PRIMARY KEY(entity_id,occurrence_id),
  FOREIGN KEY(entity_id) REFERENCES gold_entities(entity_id),
  FOREIGN KEY(occurrence_id) REFERENCES gold_occurrences(occurrence_id)
);

CREATE TABLE gold_texts (
  text_id TEXT PRIMARY KEY NOT NULL,
  source_text_id TEXT NOT NULL,
  entity_id TEXT,
  occurrence_id TEXT NOT NULL,
  language TEXT,
  original_text TEXT NOT NULL,
  english_text TEXT,
  state TEXT NOT NULL CHECK(state IN ('verified','inferred','held','conflict')),
  evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
  FOREIGN KEY(entity_id) REFERENCES gold_entities(entity_id),
  FOREIGN KEY(occurrence_id) REFERENCES gold_occurrences(occurrence_id)
);

CREATE TABLE gold_claims (
  claim_id TEXT PRIMARY KEY NOT NULL,
  assertion_id TEXT NOT NULL,
  entity_id TEXT,
  property_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('verified','inferred','held','conflict')),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  FOREIGN KEY(entity_id) REFERENCES gold_entities(entity_id)
);

CREATE TABLE gold_edges (
  edge_id TEXT PRIMARY KEY NOT NULL,
  relation_id TEXT NOT NULL,
  subject_id TEXT,
  predicate_id TEXT NOT NULL,
  object_id TEXT,
  state TEXT NOT NULL CHECK(state IN ('verified','conditional','inferred','held','conflict')),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  FOREIGN KEY(subject_id) REFERENCES gold_entities(entity_id),
  FOREIGN KEY(object_id) REFERENCES gold_entities(entity_id)
);

CREATE TABLE gold_metrics (
  metric_id TEXT PRIMARY KEY NOT NULL,
  name_en TEXT NOT NULL,
  dimension TEXT NOT NULL,
  canonical_unit_id TEXT,
  state TEXT NOT NULL CHECK(state IN ('verified','inferred','held','conflict'))
);

CREATE TABLE gold_observations (
  observation_id TEXT PRIMARY KEY NOT NULL,
  claim_id TEXT NOT NULL,
  metric_id TEXT NOT NULL,
  entity_id TEXT,
  kind TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('verified','inferred','held','conflict')),
  context_json TEXT NOT NULL CHECK(json_valid(context_json)),
  original_json TEXT NOT NULL CHECK(json_valid(original_json)),
  comparable_json TEXT NOT NULL CHECK(json_valid(comparable_json)),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  FOREIGN KEY(claim_id) REFERENCES gold_claims(claim_id),
  FOREIGN KEY(metric_id) REFERENCES gold_metrics(metric_id),
  FOREIGN KEY(entity_id) REFERENCES gold_entities(entity_id)
);

CREATE TABLE gold_support (
  support_id TEXT PRIMARY KEY NOT NULL,
  target_kind TEXT NOT NULL,
  target_id TEXT NOT NULL,
  citation_id TEXT NOT NULL,
  support_scope TEXT NOT NULL,
  evidence_sha256 TEXT NOT NULL,
  FOREIGN KEY(citation_id) REFERENCES gold_citations(citation_id)
);

CREATE TABLE gold_unbound_support (
  reference_id TEXT PRIMARY KEY NOT NULL,
  target_kind TEXT NOT NULL,
  target_id TEXT NOT NULL,
  citation_id TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE gold_comparisons (
  comparison_id TEXT PRIMARY KEY NOT NULL,
  disposition TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_sha256 TEXT NOT NULL
);

CREATE TABLE gold_comparison_observations (
  comparison_id TEXT NOT NULL,
  observation_id TEXT NOT NULL,
  PRIMARY KEY(comparison_id,observation_id),
  FOREIGN KEY(comparison_id) REFERENCES gold_comparisons(comparison_id),
  FOREIGN KEY(observation_id) REFERENCES gold_observations(observation_id)
);

CREATE TABLE gold_holds (
  hold_id TEXT PRIMARY KEY NOT NULL,
  target_kind TEXT NOT NULL,
  target_id TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE INDEX gold_edges_subject ON gold_edges(subject_id,predicate_id);

CREATE INDEX gold_observations_metric ON gold_observations(metric_id,entity_id);

-- Verified edge endpoints must themselves qualify. Held unresolved edges retain NULLs.
CREATE TRIGGER gold_edge_qualified BEFORE INSERT ON gold_edges
WHEN NEW.state IN ('verified','conditional') AND (
 NEW.subject_id IS NULL OR NEW.object_id IS NULL OR
 NOT EXISTS(SELECT 1 FROM gold_entities WHERE entity_id=NEW.subject_id AND state='verified') OR
 NOT EXISTS(SELECT 1 FROM gold_entities WHERE entity_id=NEW.object_id AND state='verified'))
BEGIN SELECT RAISE(ABORT,'verified relationship requires qualified endpoints'); END;

-- Conditional rows cannot be silently promoted by a verified-only consumer.
CREATE TRIGGER gold_edge_alternative_insert BEFORE INSERT ON gold_edges
WHEN (NEW.state='verified' AND (
 json_type(NEW.payload_json,'$.condition') IS NOT NULL OR
 json_type(NEW.payload_json,'$.alternativeGroupId') IS NOT NULL OR
 json_type(NEW.payload_json,'$.branchId') IS NOT NULL OR
 json_type(NEW.payload_json,'$.groupId') IS NOT NULL)) OR
 (NEW.state='conditional' AND (
 NEW.predicate_id!='canonical_ingredient' OR
 json_type(NEW.payload_json,'$.condition') IS NOT 'object' OR
 json_extract(NEW.payload_json,'$.condition.kind') IS NOT 'selected-alternative'))
BEGIN SELECT RAISE(ABORT,'alternative requires typed conditional state'); END;

-- REPLACE deletes/inserts instead of updating. Check both existing identities
-- before it can discard conditional provenance, even after a hold.
CREATE TRIGGER gold_edge_alternative_identity BEFORE INSERT ON gold_edges
WHEN EXISTS(SELECT 1 FROM gold_edges old
 WHERE (old.edge_id=NEW.edge_id OR old.relation_id=NEW.relation_id)
 AND (old.state='conditional' OR json_type(old.payload_json,'$.condition') IS NOT NULL))
BEGIN SELECT RAISE(ABORT,'existing alternative identity requires retained provenance'); END;

CREATE TRIGGER gold_edge_qualified_update BEFORE UPDATE ON gold_edges
WHEN NEW.state IN ('verified','conditional') AND (
 NEW.subject_id IS NULL OR NEW.object_id IS NULL OR
 NOT EXISTS(SELECT 1 FROM gold_entities WHERE entity_id=NEW.subject_id AND state='verified') OR
 NOT EXISTS(SELECT 1 FROM gold_entities WHERE entity_id=NEW.object_id AND state='verified'))
BEGIN SELECT RAISE(ABORT,'relationship requires qualified endpoints'); END;

-- Qualification is proposed afresh; removing a condition in place is not review.
CREATE TRIGGER gold_edge_alternative_update BEFORE UPDATE ON gold_edges
WHEN ((OLD.state='conditional' OR json_type(OLD.payload_json,'$.condition') IS NOT NULL)
 AND (NEW.state='verified' OR NEW.payload_json!=OLD.payload_json
 OR NEW.edge_id!=OLD.edge_id OR NEW.relation_id!=OLD.relation_id)) OR
 (NEW.state='verified' AND (
 json_type(NEW.payload_json,'$.condition') IS NOT NULL OR
 json_type(NEW.payload_json,'$.alternativeGroupId') IS NOT NULL OR
 json_type(NEW.payload_json,'$.branchId') IS NOT NULL OR
 json_type(NEW.payload_json,'$.groupId') IS NOT NULL)) OR
 (NEW.state='conditional' AND (
 NEW.predicate_id!='canonical_ingredient' OR
 json_type(NEW.payload_json,'$.condition') IS NOT 'object' OR
 json_extract(NEW.payload_json,'$.condition.kind') IS NOT 'selected-alternative'))
BEGIN SELECT RAISE(ABORT,'alternative requires a fresh qualified proposal'); END;
