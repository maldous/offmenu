-- NEW schema-ready empty reference sidecar; no reference data imported here.
CREATE TABLE retained_reference_record(
 reference_record_id TEXT PRIMARY KEY NOT NULL,
 source_id TEXT NOT NULL, release_id TEXT NOT NULL,
 asset_id TEXT NOT NULL, asset_sha256 TEXT NOT NULL,
 source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),
 native_record_id TEXT, source_pointer TEXT NOT NULL,
 original_language TEXT NOT NULL, source_payload_json TEXT NOT NULL,
 parsed_record_sha256 TEXT NOT NULL,
 citation_id TEXT, citation_binding_status TEXT NOT NULL,
 parse_engine_id TEXT NOT NULL, parse_engine_version TEXT NOT NULL,
 processing_status TEXT NOT NULL,
 UNIQUE(asset_id,asset_sha256,source_ordinal)
);
CREATE TABLE dietary_source_observation(
 observation_id TEXT PRIMARY KEY NOT NULL,
 reference_record_id TEXT NOT NULL REFERENCES retained_reference_record(reference_record_id),
 source_subject_id TEXT, source_property_namespace TEXT, source_property_code TEXT,
 source_value_lexeme TEXT, source_unit_lexeme TEXT, source_basis_lexeme TEXT,
 source_method TEXT, source_qualifier TEXT,
 normalized_subject_id TEXT, normalization_status TEXT NOT NULL
);
CREATE TABLE supplier_source_actor(
 actor_record_id TEXT PRIMARY KEY NOT NULL,
 reference_record_id TEXT NOT NULL REFERENCES retained_reference_record(reference_record_id),
 source_actor_id TEXT, original_name TEXT,
 source_role_lexeme TEXT, source_location_lexeme TEXT,
 canonical_organization_id TEXT, normalization_status TEXT NOT NULL
);
CREATE TABLE supplier_source_offer(
 offer_record_id TEXT PRIMARY KEY NOT NULL,
 reference_record_id TEXT NOT NULL REFERENCES retained_reference_record(reference_record_id),
 source_offer_id TEXT, source_supplier_id TEXT, source_product_id TEXT,
 source_price_lexeme TEXT, source_currency_lexeme TEXT,
 source_quantity_lexeme TEXT, source_unit_lexeme TEXT,
 source_observed_at TEXT, source_valid_until TEXT, source_availability_lexeme TEXT,
 canonical_supplier_id TEXT, canonical_product_id TEXT, normalization_status TEXT NOT NULL
);
CREATE INDEX reference_source_records ON retained_reference_record(source_id,release_id,native_record_id,source_ordinal);
CREATE INDEX dietary_source_subject ON dietary_source_observation(source_subject_id,observation_id);
CREATE INDEX supplier_source_key ON supplier_source_actor(source_actor_id,actor_record_id);
CREATE INDEX supplier_offer_source ON supplier_source_offer(source_supplier_id,offer_record_id);
CREATE VIEW v_dietary_source_inspection AS SELECT d.*,r.source_id,r.release_id,r.original_language,r.citation_id,r.citation_binding_status,r.source_pointer FROM dietary_source_observation d JOIN retained_reference_record r USING(reference_record_id);
CREATE VIEW v_supplier_source_inspection AS SELECT s.*,r.source_id,r.release_id,r.original_language,r.citation_id,r.citation_binding_status,r.source_pointer FROM supplier_source_actor s JOIN retained_reference_record r USING(reference_record_id);
CREATE VIEW v_supplier_offer_inspection AS SELECT s.*,r.source_id,r.release_id,r.citation_id,r.citation_binding_status,r.source_pointer FROM supplier_source_offer s JOIN retained_reference_record r USING(reference_record_id);
