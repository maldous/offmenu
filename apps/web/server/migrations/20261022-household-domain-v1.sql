-- OffMenu application-owned household/inventory contract v1; preparation only.
-- Apply AFTER cloud/schema.sql and 20261022-byoc-security-v1.sql, with FK enforcement.
-- No source ingestion, backfill, alteration, deletion, deployment or runtime switch.
-- Execute atomically through the migration runner, once, recording the file digest.
-- SQLite/D1 have no row-level read authorization. Every query needs trusted scope.
PRAGMA foreign_keys=ON;

CREATE TABLE household_schema_versions (
  version TEXT PRIMARY KEY, applied_at TEXT NOT NULL
);

-- Profiles are account-private, not kitchen members and not implied sharing grants.
CREATE TABLE household_profiles (
  owner_user_id TEXT NOT NULL, id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
  status TEXT NOT NULL CHECK(status IN ('active','archived','deletion_pending')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  PRIMARY KEY(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id)
);
CREATE TABLE household_profile_preferences (
  owner_user_id TEXT NOT NULL, profile_id TEXT NOT NULL, id TEXT NOT NULL,
  envelope_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision >= 1),
  status TEXT NOT NULL CHECK(status IN ('declared','unknown','withdrawn')),
  recorded_at TEXT NOT NULL,
  PRIMARY KEY(owner_user_id,id),
  FOREIGN KEY(owner_user_id,profile_id) REFERENCES household_profiles(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id)
);
CREATE TABLE household_profile_observations (
  owner_user_id TEXT NOT NULL, profile_id TEXT NOT NULL, id TEXT NOT NULL,
  envelope_id TEXT NOT NULL, consent_id TEXT NOT NULL,
  source_id TEXT NOT NULL, source_record_id TEXT NOT NULL,
  source_observation_hmac TEXT NOT NULL CHECK(length(source_observation_hmac)=64), observed_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL, retain_until INTEGER NOT NULL CHECK(retain_until > 0),
  PRIMARY KEY(owner_user_id,id), UNIQUE(owner_user_id,profile_id,source_id,source_observation_hmac),
  FOREIGN KEY(owner_user_id,profile_id) REFERENCES household_profiles(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
-- Consent binding is validated against sec_consents by the transaction adapter.
-- Multiple homes/carers are explicit grants; kitchen membership alone is insufficient.
CREATE TABLE household_profile_grants (
  owner_user_id TEXT NOT NULL, profile_id TEXT NOT NULL, id TEXT NOT NULL,
  kitchen_id TEXT NOT NULL, grantee_user_id TEXT NOT NULL, consent_id TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK(purpose IN ('meal-planning','profile-read','profile-edit','intake-recording')),
  expires_at INTEGER NOT NULL CHECK(expires_at > 0), revoked_at INTEGER,
  PRIMARY KEY(owner_user_id,id),
  FOREIGN KEY(owner_user_id,profile_id) REFERENCES household_profiles(owner_user_id,id),
  FOREIGN KEY(kitchen_id,grantee_user_id) REFERENCES kitchen_members(kitchen_id,user_id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TABLE household_contexts (
  owner_user_id TEXT NOT NULL, id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK(revision >= 1), status TEXT NOT NULL CHECK(status IN ('declared','unknown','withdrawn')),
  PRIMARY KEY(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id)
);

-- Unit definitions are explicit dimensions. Quantities use fixed micro-units,
-- not binary floats; no mass/volume/count conversion without scoped evidence.
CREATE TABLE stock_units (
  id TEXT PRIMARY KEY, dimension TEXT NOT NULL CHECK(dimension IN ('mass','volume','count','portion','package')),
  scale INTEGER NOT NULL CHECK(scale=1000000),
  UNIQUE(id,dimension)
);
INSERT INTO stock_units VALUES('g','mass',1000000),('ml','volume',1000000),('count','count',1000000),('portion','portion',1000000),('package','package',1000000);
CREATE TABLE stock_locations (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, parent_id TEXT,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  storage_kind TEXT NOT NULL CHECK(storage_kind IN ('ambient','refrigerated','frozen','other','unknown')),
  revision INTEGER NOT NULL CHECK(revision >= 1), archived_at TEXT,
  PRIMARY KEY(kitchen_id,id), CHECK(parent_id IS NULL OR parent_id != id),
  FOREIGN KEY(kitchen_id) REFERENCES kitchens(id),
  FOREIGN KEY(kitchen_id,parent_id) REFERENCES stock_locations(kitchen_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
-- Each item has a typed encrypted identity payload: barcode scheme/namespace/text,
-- source+release+record, ingredient mapping certainty, or no-barcode/private identity.
CREATE TABLE stock_items (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('product','produce','ingredient','prepared','unknown')),
  identity_status TEXT NOT NULL CHECK(identity_status IN ('unresolved','candidate','verified','conflict')),
  revision INTEGER NOT NULL CHECK(revision >= 1), created_at TEXT NOT NULL, deleted_at TEXT,
  PRIMARY KEY(kitchen_id,id), FOREIGN KEY(kitchen_id) REFERENCES kitchens(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE stock_item_mappings (
  kitchen_id TEXT NOT NULL, item_id TEXT NOT NULL, id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('is_food','usable_as','contains','possible_substitute')),
  review_status TEXT NOT NULL CHECK(review_status IN ('unreviewed','verified','rejected','conflict')),
  PRIMARY KEY(kitchen_id,id),
  FOREIGN KEY(kitchen_id,item_id) REFERENCES stock_items(kitchen_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE stock_receipts (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, owner_user_id TEXT NOT NULL,
  envelope_id TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode IN ('shelf','shopping','waste','receipt_ocr','label_ocr')),
  status TEXT NOT NULL CHECK(status IN ('draft','needs_review','reviewed','committed','cancelled','expired')),
  source_id TEXT NOT NULL, content_digest TEXT NOT NULL, consent_id TEXT,
  started_at TEXT NOT NULL, finished_at TEXT, reviewed_at TEXT,
  retain_until INTEGER NOT NULL CHECK(retain_until > 0), image_envelope_id TEXT, image_retain_until INTEGER,
  revision INTEGER NOT NULL CHECK(revision >= 1),
  PRIMARY KEY(kitchen_id,id), UNIQUE(kitchen_id,owner_user_id,source_id,content_digest),
  CHECK((image_envelope_id IS NULL AND image_retain_until IS NULL) OR
        (image_envelope_id IS NOT NULL AND image_retain_until IS NOT NULL AND image_retain_until <= retain_until)),
  CHECK(status NOT IN ('reviewed','committed') OR reviewed_at IS NOT NULL),
  FOREIGN KEY(kitchen_id) REFERENCES kitchens(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,image_envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TABLE stock_receipt_lines (
  kitchen_id TEXT NOT NULL, receipt_id TEXT NOT NULL, id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
  item_id TEXT, owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  review_decision TEXT NOT NULL CHECK(review_decision IN ('pending','include','exclude')),
  confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
  quantity_micros INTEGER CHECK(quantity_micros IS NULL OR (typeof(quantity_micros)='integer' AND quantity_micros BETWEEN 0 AND 9000000000000000)),
  unit_id TEXT, CHECK((quantity_micros IS NULL)=(unit_id IS NULL)),
  PRIMARY KEY(kitchen_id,receipt_id,id), UNIQUE(kitchen_id,receipt_id,ordinal),
  FOREIGN KEY(kitchen_id,receipt_id) REFERENCES stock_receipts(kitchen_id,id),
  FOREIGN KEY(kitchen_id,item_id) REFERENCES stock_items(kitchen_id,id), FOREIGN KEY(unit_id) REFERENCES stock_units(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE household_meal_plans (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('template','draft','active','completed','cancelled')),
  revision INTEGER NOT NULL CHECK(revision >= 1), created_at TEXT NOT NULL,
  PRIMARY KEY(kitchen_id,id), FOREIGN KEY(kitchen_id) REFERENCES kitchens(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE household_plan_meals (
  kitchen_id TEXT NOT NULL, plan_id TEXT NOT NULL, id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  planned_date TEXT NOT NULL, time_zone TEXT NOT NULL,
  meal_slot TEXT NOT NULL CHECK(meal_slot IN ('Breakfast','Lunch','Dinner','Snack','Other')),
  servings_micros INTEGER NOT NULL CHECK(typeof(servings_micros)='integer' AND servings_micros BETWEEN 1 AND 9000000000000000),
  status TEXT NOT NULL CHECK(status IN ('planned','cooked','cancelled')),
  revision INTEGER NOT NULL CHECK(revision >= 1),
  PRIMARY KEY(kitchen_id,id), FOREIGN KEY(kitchen_id,plan_id) REFERENCES household_meal_plans(kitchen_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
-- Account-private attendance never exposes member identity through kitchenProjection.
CREATE TABLE household_meal_attendance (
  owner_user_id TEXT NOT NULL, profile_id TEXT NOT NULL, kitchen_id TEXT NOT NULL, meal_id TEXT NOT NULL,
  envelope_id TEXT NOT NULL, consent_id TEXT NOT NULL,
  PRIMARY KEY(owner_user_id,profile_id,kitchen_id,meal_id),
  FOREIGN KEY(owner_user_id,profile_id) REFERENCES household_profiles(owner_user_id,id),
  FOREIGN KEY(kitchen_id,meal_id) REFERENCES household_plan_meals(kitchen_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TABLE stock_cook_batches (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, meal_id TEXT,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  servings_micros INTEGER NOT NULL CHECK(typeof(servings_micros)='integer' AND servings_micros BETWEEN 1 AND 9000000000000000),
  status TEXT NOT NULL CHECK(status IN ('cooked','partly_served','finished','undone')),
  created_at TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision >= 1),
  PRIMARY KEY(kitchen_id,id), FOREIGN KEY(kitchen_id) REFERENCES kitchens(id),
  FOREIGN KEY(kitchen_id,meal_id) REFERENCES household_plan_meals(kitchen_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE UNIQUE INDEX stock_one_active_cook_per_meal ON stock_cook_batches(kitchen_id,meal_id) WHERE meal_id IS NOT NULL AND status != 'undone';
CREATE TABLE stock_lots (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, item_id TEXT NOT NULL, location_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL, unit_id TEXT NOT NULL,
  amount_basis TEXT NOT NULL CHECK(amount_basis IN ('full-pack','package','manual','measured','unknown')),
  review_status TEXT NOT NULL CHECK(review_status IN ('needs_review','reviewed','quarantined')),
  physical_state TEXT NOT NULL CHECK(physical_state IN ('unopened','opened','frozen','thawed','decanted','prepared','unknown')),
  produced_on TEXT, use_by TEXT, best_before TEXT, review_on TEXT,
  acquired_at TEXT, opened_at TEXT, frozen_at TEXT, thawed_at TEXT, decanted_at TEXT,
  source_receipt_id TEXT, source_line_id TEXT, cook_batch_id TEXT, parent_lot_id TEXT,
  revision INTEGER NOT NULL CHECK(revision >= 1), created_at TEXT NOT NULL, deleted_at TEXT,
  PRIMARY KEY(kitchen_id,id), UNIQUE(kitchen_id,id,unit_id),
  CHECK((source_receipt_id IS NULL)=(source_line_id IS NULL)),
  CHECK(parent_lot_id IS NULL OR parent_lot_id != id),
  FOREIGN KEY(kitchen_id,item_id) REFERENCES stock_items(kitchen_id,id),
  FOREIGN KEY(kitchen_id,location_id) REFERENCES stock_locations(kitchen_id,id),
  FOREIGN KEY(unit_id) REFERENCES stock_units(id),
  FOREIGN KEY(kitchen_id,source_receipt_id,source_line_id) REFERENCES stock_receipt_lines(kitchen_id,receipt_id,id),
  FOREIGN KEY(kitchen_id,cook_batch_id) REFERENCES stock_cook_batches(kitchen_id,id),
  FOREIGN KEY(kitchen_id,parent_lot_id) REFERENCES stock_lots(kitchen_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE INDEX stock_expiry_lookup ON stock_lots(kitchen_id,use_by,best_before,review_on);
CREATE TABLE stock_lot_ownership (
  kitchen_id TEXT NOT NULL, lot_id TEXT NOT NULL, user_id TEXT NOT NULL,
  share_ppm INTEGER CHECK(share_ppm IS NULL OR (typeof(share_ppm)='integer' AND share_ppm BETWEEN 1 AND 1000000)),
  PRIMARY KEY(kitchen_id,lot_id,user_id),
  FOREIGN KEY(kitchen_id,lot_id) REFERENCES stock_lots(kitchen_id,id),
  FOREIGN KEY(kitchen_id,user_id) REFERENCES kitchen_members(kitchen_id,user_id)
);
CREATE TABLE stock_reservations (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, lot_id TEXT NOT NULL, meal_id TEXT NOT NULL, unit_id TEXT NOT NULL,
  quantity_micros INTEGER NOT NULL CHECK(typeof(quantity_micros)='integer' AND quantity_micros BETWEEN 1 AND 9000000000000000),
  status TEXT NOT NULL CHECK(status IN ('active','released','consumed')),
  needed_on TEXT NOT NULL, expires_at INTEGER, revision INTEGER NOT NULL CHECK(revision >= 1),
  PRIMARY KEY(kitchen_id,id), FOREIGN KEY(kitchen_id,lot_id,unit_id) REFERENCES stock_lots(kitchen_id,id,unit_id),
  FOREIGN KEY(kitchen_id,meal_id) REFERENCES household_plan_meals(kitchen_id,id)
);
CREATE TABLE stock_commands (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, actor_user_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL, request_hmac TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('receipt','adjust','cook','serve','waste','transfer','undo','reserve')),
  created_at TEXT NOT NULL, PRIMARY KEY(kitchen_id,id), UNIQUE(kitchen_id,actor_user_id,idempotency_key),
  FOREIGN KEY(kitchen_id) REFERENCES kitchens(id)
);
-- Immutable quantity ledger. Corrections are compensating entries, not rewrites.
CREATE TABLE stock_movements (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, command_id TEXT NOT NULL, lot_id TEXT NOT NULL, unit_id TEXT NOT NULL,
  delta_micros INTEGER NOT NULL CHECK(typeof(delta_micros)='integer' AND delta_micros != 0 AND delta_micros BETWEEN -9000000000000000 AND 9000000000000000),
  kind TEXT NOT NULL CHECK(kind IN ('acquire','adjust','consume','waste','transfer_in','transfer_out','undo')),
  cook_batch_id TEXT, reversal_of TEXT, occurred_at TEXT NOT NULL,
  PRIMARY KEY(kitchen_id,id), UNIQUE(kitchen_id,reversal_of),
  CHECK((kind='undo')=(reversal_of IS NOT NULL)),
  CHECK(kind NOT IN ('consume','waste','transfer_out') OR delta_micros < 0),
  CHECK(kind NOT IN ('acquire','transfer_in') OR delta_micros > 0),
  FOREIGN KEY(kitchen_id,command_id) REFERENCES stock_commands(kitchen_id,id),
  FOREIGN KEY(kitchen_id,lot_id,unit_id) REFERENCES stock_lots(kitchen_id,id,unit_id),
  FOREIGN KEY(kitchen_id,cook_batch_id) REFERENCES stock_cook_batches(kitchen_id,id),
  FOREIGN KEY(kitchen_id,reversal_of) REFERENCES stock_movements(kitchen_id,id)
);
CREATE TRIGGER stock_movements_no_update BEFORE UPDATE ON stock_movements BEGIN SELECT RAISE(ABORT,'stock ledger is immutable'); END;
-- Deletion is deliberately not blocked: consent/account erasure has a separate authorized purge path.
CREATE TRIGGER stock_movement_balance_guard BEFORE INSERT ON stock_movements BEGIN
 SELECT CASE WHEN COALESCE((SELECT SUM(delta_micros) FROM stock_movements WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id),0) + NEW.delta_micros NOT BETWEEN 0 AND 9000000000000000 THEN RAISE(ABORT,'stock quantity out of range') END;
 SELECT CASE WHEN NEW.kind='undo' AND NOT EXISTS(SELECT 1 FROM stock_movements m WHERE m.kitchen_id=NEW.kitchen_id AND m.id=NEW.reversal_of AND m.lot_id=NEW.lot_id AND m.unit_id=NEW.unit_id AND m.delta_micros=-NEW.delta_micros AND m.kind!='undo') THEN RAISE(ABORT,'invalid compensating movement') END;
END;
CREATE TRIGGER stock_movement_apply AFTER INSERT ON stock_movements BEGIN
 UPDATE stock_lots SET revision=revision+1 WHERE kitchen_id=NEW.kitchen_id AND id=NEW.lot_id;
END;
CREATE VIEW stock_lot_balances AS
 SELECT l.kitchen_id,l.id AS lot_id,l.unit_id,COALESCE(SUM(m.delta_micros),0) AS quantity_micros
 FROM stock_lots l LEFT JOIN stock_movements m ON m.kitchen_id=l.kitchen_id AND m.lot_id=l.id
 GROUP BY l.kitchen_id,l.id,l.unit_id;
CREATE TABLE stock_waste_observations (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, movement_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  measurement_status TEXT NOT NULL CHECK(measurement_status IN ('measured','estimated','unknown')),
  quantity_micros INTEGER CHECK(quantity_micros IS NULL OR (typeof(quantity_micros)='integer' AND quantity_micros BETWEEN 0 AND 9000000000000000)), unit_id TEXT,
  observed_at TEXT NOT NULL, PRIMARY KEY(kitchen_id,id),
  CHECK((measurement_status='unknown' AND quantity_micros IS NULL AND unit_id IS NULL) OR (measurement_status!='unknown' AND quantity_micros IS NOT NULL AND unit_id IS NOT NULL)),
  FOREIGN KEY(kitchen_id,movement_id) REFERENCES stock_movements(kitchen_id,id), FOREIGN KEY(unit_id) REFERENCES stock_units(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
-- Intake/serving and body metrics stay account-private, including recipient linkage.
CREATE TABLE household_intake_events (
  owner_user_id TEXT NOT NULL, id TEXT NOT NULL, profile_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  consent_id TEXT NOT NULL, occurred_at TEXT NOT NULL, time_zone TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('meal','snack','hydration','restaurant','substitution','serving')),
  source_id TEXT NOT NULL, source_event_id TEXT NOT NULL, retain_until INTEGER NOT NULL CHECK(retain_until > 0),
  PRIMARY KEY(owner_user_id,id), UNIQUE(owner_user_id,source_id,source_event_id),
  FOREIGN KEY(owner_user_id,profile_id) REFERENCES household_profiles(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TABLE household_shopping_lists (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('draft','active','completed','cancelled')),
  revision INTEGER NOT NULL CHECK(revision >= 1), PRIMARY KEY(kitchen_id,id),
  FOREIGN KEY(kitchen_id) REFERENCES kitchens(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE household_shopping_lines (
  kitchen_id TEXT NOT NULL, list_id TEXT NOT NULL, id TEXT NOT NULL,
  item_id TEXT, meal_id TEXT, substitute_for_id TEXT,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  quantity_micros INTEGER CHECK(quantity_micros IS NULL OR (typeof(quantity_micros)='integer' AND quantity_micros BETWEEN 0 AND 9000000000000000)), unit_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('needed','claimed','checked','purchased','removed','needs_review')),
  assigned_user_id TEXT, revision INTEGER NOT NULL CHECK(revision >= 1),
  PRIMARY KEY(kitchen_id,list_id,id), CHECK((quantity_micros IS NULL)=(unit_id IS NULL)),
  FOREIGN KEY(kitchen_id,list_id) REFERENCES household_shopping_lists(kitchen_id,id),
  FOREIGN KEY(kitchen_id,item_id) REFERENCES stock_items(kitchen_id,id),
  FOREIGN KEY(kitchen_id,meal_id) REFERENCES household_plan_meals(kitchen_id,id),
  FOREIGN KEY(kitchen_id,list_id,substitute_for_id) REFERENCES household_shopping_lines(kitchen_id,list_id,id),
  FOREIGN KEY(kitchen_id,assigned_user_id) REFERENCES kitchen_members(kitchen_id,user_id),
  FOREIGN KEY(unit_id) REFERENCES stock_units(id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE household_shopping_handoffs (
  kitchen_id TEXT NOT NULL, id TEXT NOT NULL, list_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('draft','reviewed','exported','cancelled','expired')),
  reviewed_at TEXT, retain_until INTEGER NOT NULL CHECK(retain_until > 0),
  PRIMARY KEY(kitchen_id,id), CHECK(status NOT IN ('reviewed','exported') OR reviewed_at IS NOT NULL),
  FOREIGN KEY(kitchen_id,list_id) REFERENCES household_shopping_lists(kitchen_id,id),
  FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);

CREATE TABLE stock_quantity_conversions (
 kitchen_id TEXT NOT NULL, id TEXT NOT NULL, item_id TEXT NOT NULL,
 owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
 from_unit_id TEXT NOT NULL, to_unit_id TEXT NOT NULL,
 factor_numerator INTEGER NOT NULL CHECK(typeof(factor_numerator)='integer' AND factor_numerator BETWEEN 1 AND 1000000000),
 factor_denominator INTEGER NOT NULL CHECK(typeof(factor_denominator)='integer' AND factor_denominator BETWEEN 1 AND 1000000000),
 status TEXT NOT NULL CHECK(status IN ('candidate','verified','rejected')),
 PRIMARY KEY(kitchen_id,id), CHECK(from_unit_id!=to_unit_id),
 FOREIGN KEY(kitchen_id,item_id) REFERENCES stock_items(kitchen_id,id),
 FOREIGN KEY(from_unit_id) REFERENCES stock_units(id), FOREIGN KEY(to_unit_id) REFERENCES stock_units(id),
 FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE stock_lot_events (
 kitchen_id TEXT NOT NULL, id TEXT NOT NULL, lot_id TEXT NOT NULL, command_id TEXT NOT NULL,
 owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('opened','frozen','thawed','decanted','relocated','reviewed','date_corrected','split','merged')),
 occurred_at TEXT NOT NULL, PRIMARY KEY(kitchen_id,id),
 FOREIGN KEY(kitchen_id,lot_id) REFERENCES stock_lots(kitchen_id,id),
 FOREIGN KEY(kitchen_id,command_id) REFERENCES stock_commands(kitchen_id,id),
 FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE stock_lot_checks (
 kitchen_id TEXT NOT NULL, id TEXT NOT NULL, lot_id TEXT NOT NULL,
 owner_user_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('recall','package-restriction','freshness')),
 result TEXT NOT NULL CHECK(result IN ('pass','fail','unknown','conflict')),
 checked_at TEXT NOT NULL, valid_until INTEGER,
 PRIMARY KEY(kitchen_id,id), FOREIGN KEY(kitchen_id,lot_id) REFERENCES stock_lots(kitchen_id,id),
 FOREIGN KEY(kitchen_id,owner_user_id,envelope_id) REFERENCES sec_envelopes(kitchen_id,owner_user_id,id)
);
CREATE TABLE household_saved_recipes (
 owner_user_id TEXT NOT NULL, id TEXT NOT NULL, envelope_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('private-recipe','bookmark','licensed-pack')),
 revision INTEGER NOT NULL CHECK(revision >= 1), deleted_at TEXT,
 PRIMARY KEY(owner_user_id,id), FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id)
);
CREATE TABLE household_recipe_collections (
 owner_user_id TEXT NOT NULL, id TEXT NOT NULL, envelope_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision >= 1),
 PRIMARY KEY(owner_user_id,id), FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id)
);
CREATE TABLE household_recipe_collection_members (
 owner_user_id TEXT NOT NULL, collection_id TEXT NOT NULL, recipe_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal>=0),
 PRIMARY KEY(owner_user_id,collection_id,recipe_id), UNIQUE(owner_user_id,collection_id,ordinal),
 FOREIGN KEY(owner_user_id,collection_id) REFERENCES household_recipe_collections(owner_user_id,id),
 FOREIGN KEY(owner_user_id,recipe_id) REFERENCES household_saved_recipes(owner_user_id,id)
);
CREATE TRIGGER stock_ownership_total_insert BEFORE INSERT ON stock_lot_ownership BEGIN
 SELECT CASE WHEN NEW.share_ppm + COALESCE((SELECT SUM(share_ppm) FROM stock_lot_ownership WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id),0)>1000000 THEN RAISE(ABORT,'ownership shares exceed whole') END;
END;
CREATE TRIGGER stock_ownership_total_update BEFORE UPDATE ON stock_lot_ownership BEGIN
 SELECT CASE WHEN NEW.share_ppm + COALESCE((SELECT SUM(share_ppm) FROM stock_lot_ownership WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id AND user_id!=OLD.user_id),0)>1000000 THEN RAISE(ABORT,'ownership shares exceed whole') END;
END;
CREATE TRIGGER stock_reservation_insert BEFORE INSERT ON stock_reservations WHEN NEW.status='active' BEGIN
 SELECT CASE WHEN NEW.quantity_micros + COALESCE((SELECT SUM(quantity_micros) FROM stock_reservations WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id AND status='active'),0) > COALESCE((SELECT SUM(delta_micros) FROM stock_movements WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id),0) THEN RAISE(ABORT,'reservation exceeds available stock') END;
END;
CREATE TRIGGER stock_reservation_update BEFORE UPDATE ON stock_reservations WHEN NEW.status='active' BEGIN
 SELECT CASE WHEN NEW.quantity_micros + COALESCE((SELECT SUM(quantity_micros) FROM stock_reservations WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id AND status='active' AND id!=OLD.id),0) > COALESCE((SELECT SUM(delta_micros) FROM stock_movements WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id),0) THEN RAISE(ABORT,'reservation exceeds available stock') END;
END;
CREATE TRIGGER stock_movement_reservations BEFORE INSERT ON stock_movements BEGIN
 SELECT CASE WHEN COALESCE((SELECT SUM(delta_micros) FROM stock_movements WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id),0)+NEW.delta_micros < COALESCE((SELECT SUM(quantity_micros) FROM stock_reservations WHERE kitchen_id=NEW.kitchen_id AND lot_id=NEW.lot_id AND status='active'),0) THEN RAISE(ABORT,'release or consume reservations in same transaction before stock deduction') END;
END;
CREATE TRIGGER stock_receipt_start_draft BEFORE INSERT ON stock_receipts WHEN NEW.status NOT IN ('draft','needs_review') BEGIN SELECT RAISE(ABORT,'receipt must start uncommitted'); END;
CREATE TRIGGER stock_receipt_review BEFORE UPDATE OF status ON stock_receipts WHEN NEW.status IN ('reviewed','committed') BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM stock_receipt_lines WHERE kitchen_id=NEW.kitchen_id AND receipt_id=NEW.id) OR EXISTS(SELECT 1 FROM stock_receipt_lines WHERE kitchen_id=NEW.kitchen_id AND receipt_id=NEW.id AND review_decision='pending') THEN RAISE(ABORT,'review every source line first') END;
END;
CREATE TRIGGER stock_waste_bound BEFORE INSERT ON stock_waste_observations BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM stock_movements m WHERE m.kitchen_id=NEW.kitchen_id AND m.id=NEW.movement_id AND m.kind='waste' AND (NEW.quantity_micros IS NULL OR (m.unit_id=NEW.unit_id AND NEW.quantity_micros<=-m.delta_micros))) THEN RAISE(ABORT,'waste observation exceeds confirmed discard') END;
END;
CREATE TRIGGER household_profiles_envelope_insert BEFORE INSERT ON household_profiles
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_profiles' AND e.object_id=NEW.id
 AND e.purpose='household-profile/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_profiles_envelope_update BEFORE UPDATE ON household_profiles
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_profiles' AND e.object_id=NEW.id
 AND e.purpose='household-profile/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_profile_preferences_envelope_insert BEFORE INSERT ON household_profile_preferences
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_profile_preferences' AND e.object_id=NEW.id
 AND e.purpose='household-preference/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_profile_preferences_envelope_update BEFORE UPDATE ON household_profile_preferences
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_profile_preferences' AND e.object_id=NEW.id
 AND e.purpose='household-preference/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_profile_observations_envelope_insert BEFORE INSERT ON household_profile_observations
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_profile_observations' AND e.object_id=NEW.id
 AND e.purpose='household-observation/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_profile_observations_envelope_update BEFORE UPDATE ON household_profile_observations
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_profile_observations' AND e.object_id=NEW.id
 AND e.purpose='household-observation/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_contexts_envelope_insert BEFORE INSERT ON household_contexts
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_contexts' AND e.object_id=NEW.id
 AND e.purpose='household-context/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_contexts_envelope_update BEFORE UPDATE ON household_contexts
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_contexts' AND e.object_id=NEW.id
 AND e.purpose='household-context/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_locations_envelope_insert BEFORE INSERT ON stock_locations
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_locations' AND e.object_id=NEW.id
 AND e.purpose='household-location/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_locations_envelope_update BEFORE UPDATE ON stock_locations
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_locations' AND e.object_id=NEW.id
 AND e.purpose='household-location/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_items_envelope_insert BEFORE INSERT ON stock_items
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_items' AND e.object_id=NEW.id
 AND e.purpose='household-item/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_items_envelope_update BEFORE UPDATE ON stock_items
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_items' AND e.object_id=NEW.id
 AND e.purpose='household-item/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_item_mappings_envelope_insert BEFORE INSERT ON stock_item_mappings
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_item_mappings' AND e.object_id=NEW.id
 AND e.purpose='household-mapping/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_item_mappings_envelope_update BEFORE UPDATE ON stock_item_mappings
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_item_mappings' AND e.object_id=NEW.id
 AND e.purpose='household-mapping/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_receipts_envelope_insert BEFORE INSERT ON stock_receipts
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_receipts' AND e.object_id=NEW.id
 AND e.purpose='household-receipt/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_receipts_envelope_update BEFORE UPDATE ON stock_receipts
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_receipts' AND e.object_id=NEW.id
 AND e.purpose='household-receipt/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_receipt_lines_envelope_insert BEFORE INSERT ON stock_receipt_lines
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_receipt_lines' AND e.object_id=json_array(NEW.receipt_id,NEW.id)
 AND e.purpose='household-receipt_line/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_receipt_lines_envelope_update BEFORE UPDATE ON stock_receipt_lines
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_receipt_lines' AND e.object_id=json_array(NEW.receipt_id,NEW.id)
 AND e.purpose='household-receipt_line/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_meal_plans_envelope_insert BEFORE INSERT ON household_meal_plans
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_meal_plans' AND e.object_id=NEW.id
 AND e.purpose='household-plan/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_meal_plans_envelope_update BEFORE UPDATE ON household_meal_plans
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_meal_plans' AND e.object_id=NEW.id
 AND e.purpose='household-plan/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_plan_meals_envelope_insert BEFORE INSERT ON household_plan_meals
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_plan_meals' AND e.object_id=NEW.id
 AND e.purpose='household-meal/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_plan_meals_envelope_update BEFORE UPDATE ON household_plan_meals
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_plan_meals' AND e.object_id=NEW.id
 AND e.purpose='household-meal/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_meal_attendance_envelope_insert BEFORE INSERT ON household_meal_attendance
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_meal_attendance' AND e.object_id=json_array(NEW.kitchen_id,NEW.meal_id,NEW.profile_id)
 AND e.purpose='household-attendance/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_meal_attendance_envelope_update BEFORE UPDATE ON household_meal_attendance
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_meal_attendance' AND e.object_id=json_array(NEW.kitchen_id,NEW.meal_id,NEW.profile_id)
 AND e.purpose='household-attendance/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_cook_batches_envelope_insert BEFORE INSERT ON stock_cook_batches
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_cook_batches' AND e.object_id=NEW.id
 AND e.purpose='household-cook_batch/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_cook_batches_envelope_update BEFORE UPDATE ON stock_cook_batches
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_cook_batches' AND e.object_id=NEW.id
 AND e.purpose='household-cook_batch/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_lots_envelope_insert BEFORE INSERT ON stock_lots
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_lots' AND e.object_id=NEW.id
 AND e.purpose='household-lot/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_lots_envelope_update BEFORE UPDATE ON stock_lots
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_lots' AND e.object_id=NEW.id
 AND e.purpose='household-lot/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_waste_observations_envelope_insert BEFORE INSERT ON stock_waste_observations
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_waste_observations' AND e.object_id=NEW.id
 AND e.purpose='household-waste/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_waste_observations_envelope_update BEFORE UPDATE ON stock_waste_observations
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_waste_observations' AND e.object_id=NEW.id
 AND e.purpose='household-waste/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_intake_events_envelope_insert BEFORE INSERT ON household_intake_events
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_intake_events' AND e.object_id=NEW.id
 AND e.purpose='household-intake/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_intake_events_envelope_update BEFORE UPDATE ON household_intake_events
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_intake_events' AND e.object_id=NEW.id
 AND e.purpose='household-intake/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_shopping_lists_envelope_insert BEFORE INSERT ON household_shopping_lists
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_shopping_lists' AND e.object_id=NEW.id
 AND e.purpose='household-shopping_list/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_shopping_lists_envelope_update BEFORE UPDATE ON household_shopping_lists
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_shopping_lists' AND e.object_id=NEW.id
 AND e.purpose='household-shopping_list/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_shopping_lines_envelope_insert BEFORE INSERT ON household_shopping_lines
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_shopping_lines' AND e.object_id=json_array(NEW.list_id,NEW.id)
 AND e.purpose='household-shopping_line/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_shopping_lines_envelope_update BEFORE UPDATE ON household_shopping_lines
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_shopping_lines' AND e.object_id=json_array(NEW.list_id,NEW.id)
 AND e.purpose='household-shopping_line/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_shopping_handoffs_envelope_insert BEFORE INSERT ON household_shopping_handoffs
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_shopping_handoffs' AND e.object_id=NEW.id
 AND e.purpose='household-handoff/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_shopping_handoffs_envelope_update BEFORE UPDATE ON household_shopping_handoffs
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='household_shopping_handoffs' AND e.object_id=NEW.id
 AND e.purpose='household-handoff/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_quantity_conversions_envelope_insert BEFORE INSERT ON stock_quantity_conversions
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_quantity_conversions' AND e.object_id=NEW.id
 AND e.purpose='household-conversion/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_quantity_conversions_envelope_update BEFORE UPDATE ON stock_quantity_conversions
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_quantity_conversions' AND e.object_id=NEW.id
 AND e.purpose='household-conversion/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_lot_events_envelope_insert BEFORE INSERT ON stock_lot_events
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_lot_events' AND e.object_id=NEW.id
 AND e.purpose='household-lot_event/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_lot_events_envelope_update BEFORE UPDATE ON stock_lot_events
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_lot_events' AND e.object_id=NEW.id
 AND e.purpose='household-lot_event/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_lot_checks_envelope_insert BEFORE INSERT ON stock_lot_checks
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_lot_checks' AND e.object_id=NEW.id
 AND e.purpose='household-lot_check/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER stock_lot_checks_envelope_update BEFORE UPDATE ON stock_lot_checks
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id=NEW.kitchen_id AND e.object_type='stock_lot_checks' AND e.object_id=NEW.id
 AND e.purpose='household-lot_check/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_saved_recipes_envelope_insert BEFORE INSERT ON household_saved_recipes
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_saved_recipes' AND e.object_id=NEW.id
 AND e.purpose='household-saved_recipe/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_saved_recipes_envelope_update BEFORE UPDATE ON household_saved_recipes
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_saved_recipes' AND e.object_id=NEW.id
 AND e.purpose='household-saved_recipe/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_recipe_collections_envelope_insert BEFORE INSERT ON household_recipe_collections
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_recipe_collections' AND e.object_id=NEW.id
 AND e.purpose='household-collection/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_recipe_collections_envelope_update BEFORE UPDATE ON household_recipe_collections
WHEN NOT EXISTS(SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.object_type='household_recipe_collections' AND e.object_id=NEW.id
 AND e.purpose='household-collection/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'private payload binding mismatch'); END;
CREATE TRIGGER household_profile_grant_consent BEFORE INSERT ON household_profile_grants
WHEN NOT EXISTS(SELECT 1 FROM sec_consents c WHERE c.id=NEW.consent_id AND c.owner_user_id=NEW.owner_user_id
 AND c.object_type='household_profile' AND c.object_id=NEW.profile_id AND c.purpose='profile_share'
 AND c.grantee_user_id=NEW.grantee_user_id AND c.audience_kitchen_id=NEW.kitchen_id)
BEGIN SELECT RAISE(ABORT,'profile sharing consent scope mismatch'); END;
CREATE TRIGGER household_profile_grant_consent_update BEFORE UPDATE ON household_profile_grants
WHEN NOT EXISTS(SELECT 1 FROM sec_consents c WHERE c.id=NEW.consent_id AND c.owner_user_id=NEW.owner_user_id
 AND c.object_type='household_profile' AND c.object_id=NEW.profile_id AND c.purpose='profile_share'
 AND c.grantee_user_id=NEW.grantee_user_id AND c.audience_kitchen_id=NEW.kitchen_id)
BEGIN SELECT RAISE(ABORT,'profile sharing consent scope mismatch'); END;
CREATE TRIGGER stock_receipt_status_transition BEFORE UPDATE OF status ON stock_receipts
WHEN NEW.status!=OLD.status AND NOT (
 (OLD.status='draft' AND NEW.status IN ('needs_review','cancelled','expired')) OR
 (OLD.status='needs_review' AND NEW.status IN ('reviewed','cancelled','expired')) OR
 (OLD.status='reviewed' AND NEW.status IN ('committed','cancelled','expired')) OR
 (OLD.status IN ('committed','cancelled') AND NEW.status='expired'))
BEGIN SELECT RAISE(ABORT,'invalid receipt state transition'); END;
CREATE TRIGGER stock_receipt_line_insert BEFORE INSERT ON stock_receipt_lines
WHEN NOT EXISTS(SELECT 1 FROM stock_receipts r WHERE r.kitchen_id=NEW.kitchen_id AND r.id=NEW.receipt_id AND r.status IN ('draft','needs_review'))
BEGIN SELECT RAISE(ABORT,'receipt review already finalized'); END;
CREATE TRIGGER stock_receipt_line_update BEFORE UPDATE ON stock_receipt_lines
WHEN NOT EXISTS(SELECT 1 FROM stock_receipts r WHERE r.kitchen_id=OLD.kitchen_id AND r.id=OLD.receipt_id AND r.status IN ('draft','needs_review')) OR
 NOT EXISTS(SELECT 1 FROM stock_receipts r WHERE r.kitchen_id=NEW.kitchen_id AND r.id=NEW.receipt_id AND r.status IN ('draft','needs_review'))
BEGIN SELECT RAISE(ABORT,'receipt review already finalized'); END;
-- Ownership row identity is immutable; changes of owner/lot are explicit remove/add
-- operations in one authorized transaction, so the total-share guard stays exact.
CREATE TRIGGER stock_ownership_identity_immutable BEFORE UPDATE OF kitchen_id,lot_id,user_id ON stock_lot_ownership
BEGIN SELECT RAISE(ABORT,'ownership identity is immutable'); END;
-- Measurements are observations, not mutable balances. Correct through a new
-- observation; authorized retention deletion remains a separate operation.
CREATE TRIGGER stock_waste_observation_immutable BEFORE UPDATE ON stock_waste_observations
BEGIN SELECT RAISE(ABORT,'waste observations are immutable'); END;
CREATE TRIGGER stock_reservation_identity_immutable BEFORE UPDATE OF kitchen_id,id ON stock_reservations
BEGIN SELECT RAISE(ABORT,'reservation identity is immutable'); END;
INSERT INTO household_schema_versions VALUES('offmenu-household-domain/1',strftime('%Y-%m-%dT%H:%M:%fZ','now'));
