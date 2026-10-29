-- PRIVATE PORTABILITY SOURCE PROPOSAL ONLY. Worker00 is the sole actual DDL writer.
-- Apply after cloud/schema.sql, 20261022-byoc-security-v1.sql and
-- 20261022-household-domain-v1.sql, in one migration transaction with FK ON.
-- No auth/session/credential/provider tables are copied, modified or seeded.
PRAGMA foreign_keys=ON;

-- Additional field/recipient scope is conjunctive with the EXISTING live consent.
-- Rows are immutable history; revoking/changing sec_consents invalidates them.
-- This table does not supply issuer verification or grant SQL read authorization.
CREATE TABLE private_portability_consent_fields (
  owner_user_id TEXT NOT NULL, consent_id TEXT NOT NULL,
  consent_revision INTEGER NOT NULL CHECK(consent_revision>=1),
  recipient_owner_user_id TEXT NOT NULL, recipient_issuer TEXT NOT NULL,
  recipient_subject TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK(purpose IN ('privacy-access','portability','owned-backup','restore')),
  field_scope TEXT NOT NULL CHECK(field_scope IN ('inventory','profile.full','settings','content','auth_metadata','history','derived_provenance','profile.displayName','profile.dietary','profile.allergies','profile.preferences','profile.diagnoses','profile.medical_plans','attachments','relationships','extensions')),
  valid_from INTEGER NOT NULL, expires_at INTEGER NOT NULL CHECK(expires_at>valid_from),
  audit_ref TEXT NOT NULL CHECK(length(audit_ref)>0),
  PRIMARY KEY(owner_user_id,consent_id,consent_revision,recipient_owner_user_id,recipient_issuer,recipient_subject,purpose,field_scope),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TRIGGER private_portability_scope_binding BEFORE INSERT ON private_portability_consent_fields
WHEN NOT EXISTS (
  SELECT 1 FROM sec_consents c WHERE c.owner_user_id=NEW.owner_user_id
    AND c.id=NEW.consent_id AND c.revision=NEW.consent_revision AND c.choice='granted'
    AND c.purpose IN ('private_use','profile_share')
    AND NEW.valid_from>=c.valid_from AND NEW.expires_at<=c.expires_at
)
BEGIN SELECT RAISE(ABORT,'private portability scope lacks current parent consent'); END;
CREATE TRIGGER private_portability_scope_immutable BEFORE UPDATE ON private_portability_consent_fields
BEGIN SELECT RAISE(ABORT,'private portability scope is immutable history'); END;

-- Existing profiles/envelopes are reused. Clinical payload (including plan kind,
-- status, goals, observations and recommendation provenance) remains encrypted.
-- Imported clinical data never becomes an accepted/executable medical order.
CREATE TABLE household_medical_plans (
  owner_user_id TEXT NOT NULL, id TEXT NOT NULL, profile_id TEXT NOT NULL,
  envelope_id TEXT NOT NULL, consent_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK(revision>=1),
  lifecycle TEXT NOT NULL CHECK(lifecycle IN ('active','archived','deletion_pending')),
  recorded_at TEXT NOT NULL, retain_until INTEGER NOT NULL CHECK(retain_until>0),
  PRIMARY KEY(owner_user_id,id),
  FOREIGN KEY(owner_user_id,profile_id) REFERENCES household_profiles(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TRIGGER household_medical_plan_envelope_insert BEFORE INSERT ON household_medical_plans
WHEN NOT EXISTS (SELECT 1 FROM sec_envelopes e WHERE e.owner_user_id=NEW.owner_user_id
  AND e.id=NEW.envelope_id AND e.kitchen_id IS NULL AND e.object_type='household_medical_plans'
  AND e.object_id=NEW.id AND e.purpose='household-medical-plan/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'medical plan envelope binding mismatch'); END;
CREATE TRIGGER household_medical_plan_envelope_update BEFORE UPDATE ON household_medical_plans
WHEN NEW.owner_user_id!=OLD.owner_user_id OR NEW.id!=OLD.id OR NOT EXISTS (
  SELECT 1 FROM sec_envelopes e WHERE e.owner_user_id=NEW.owner_user_id
  AND e.id=NEW.envelope_id AND e.kitchen_id IS NULL AND e.object_type='household_medical_plans'
  AND e.object_id=NEW.id AND e.purpose='household-medical-plan/1' AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'medical plan envelope binding mismatch'); END;
CREATE TRIGGER household_medical_plan_consent_insert BEFORE INSERT ON household_medical_plans
WHEN NOT EXISTS (SELECT 1 FROM sec_consents c WHERE c.owner_user_id=NEW.owner_user_id
  AND c.id=NEW.consent_id AND c.object_type='household_profile' AND c.object_id=NEW.profile_id
  AND c.purpose='private_use' AND c.choice='granted')
BEGIN SELECT RAISE(ABORT,'medical plan requires granted private-use consent for this profile'); END;
CREATE TRIGGER household_medical_plan_consent_update BEFORE UPDATE ON household_medical_plans
WHEN NOT EXISTS (SELECT 1 FROM sec_consents c WHERE c.owner_user_id=NEW.owner_user_id
  AND c.id=NEW.consent_id AND c.object_type='household_profile' AND c.object_id=NEW.profile_id
  AND c.purpose='private_use' AND c.choice='granted')
BEGIN SELECT RAISE(ABORT,'medical plan requires granted private-use consent for this profile'); END;

-- Body-free, immutable transaction receipts. A real executor must atomically CAS
-- its authoritative destination revision and independent deletion/revocation
-- fences BEFORE inserting this receipt and all imported rows; SQL alone cannot
-- make remote source authority, a key service or a network call transactional.
CREATE TABLE private_restore_receipts (
  owner_user_id TEXT NOT NULL, idempotency_key TEXT NOT NULL CHECK(length(idempotency_key)=64),
  content_digest TEXT NOT NULL CHECK(length(content_digest)=64),
  source_namespace TEXT NOT NULL, source_package_checksum TEXT NOT NULL CHECK(length(source_package_checksum)=64),
  destination_namespace TEXT NOT NULL, destination_issuer TEXT NOT NULL, destination_subject TEXT NOT NULL,
  source_consent_revision INTEGER NOT NULL CHECK(source_consent_revision>=1),
  destination_consent_revision INTEGER NOT NULL CHECK(destination_consent_revision>=1),
  expected_revision INTEGER NOT NULL CHECK(expected_revision>=0),
  committed_revision INTEGER NOT NULL CHECK(committed_revision=expected_revision+1),
  committed_at INTEGER NOT NULL, authority_digest TEXT NOT NULL CHECK(length(authority_digest)=64),
  manifest_digest TEXT NOT NULL CHECK(length(manifest_digest)=64 AND manifest_digest NOT GLOB '*[^0-9a-f]*'),
  PRIMARY KEY(owner_user_id,idempotency_key)
);
CREATE TRIGGER private_restore_receipt_immutable BEFORE UPDATE ON private_restore_receipts
BEGIN SELECT RAISE(ABORT,'restore receipt is immutable'); END;

-- Restored data lands as owned encrypted data/history, never in auth/grant tables.
-- This is NOT an automatic materializer into live stock/profile projections.
-- envelope_id identifies the whole sealed bundle; record pointers select its
-- typed records. Attachments and relationships are committed in that same bundle.
CREATE TABLE private_owned_imports (
  owner_user_id TEXT NOT NULL, record_type TEXT NOT NULL CHECK(record_type IN (
    'space','location','item','lot','holding','movement','reservation','waste','profile',
    'medical_plan','settings','content','identity_link','connection_metadata',
    'auth_history','consent_history','derived_provenance')),
  record_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
  source_namespace TEXT NOT NULL, source_record_id TEXT NOT NULL,
  source_package_id TEXT NOT NULL, envelope_id TEXT NOT NULL,
  record_digest TEXT NOT NULL CHECK(length(record_digest)=64),
  disposition TEXT NOT NULL CHECK(disposition IN ('owned-data','history-only','clinical-review-required')),
  PRIMARY KEY(owner_user_id,record_type,record_id),
  CHECK((record_type IN ('identity_link','connection_metadata','auth_history','consent_history','movement','waste') AND disposition='history-only')
     OR (record_type='medical_plan' AND disposition='clinical-review-required')
     OR (record_type NOT IN ('identity_link','connection_metadata','auth_history','consent_history','movement','waste','medical_plan') AND disposition='owned-data')),
  FOREIGN KEY(owner_user_id,idempotency_key) REFERENCES private_restore_receipts(owner_user_id,idempotency_key) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id)
);
-- Receipt precedes its imports in the SAME atomic transaction. Its immutable
-- manifest digest selects the exact authenticated purpose; native package ID,
-- owner and empty provider binding remain independently checked.
CREATE TRIGGER private_owned_imports_binding BEFORE INSERT ON private_owned_imports
WHEN NOT EXISTS (SELECT 1 FROM sec_envelopes e JOIN private_restore_receipts r
  ON r.owner_user_id=NEW.owner_user_id AND r.idempotency_key=NEW.idempotency_key
  WHERE e.owner_user_id=NEW.owner_user_id
  AND e.id=NEW.envelope_id AND e.kitchen_id IS NULL AND e.object_type='private-portable-package'
  AND e.object_id=NEW.source_package_id AND e.purpose='owned_data_portability/manifest1:'||r.manifest_digest AND e.provider_id='')
BEGIN SELECT RAISE(ABORT,'restore bundle envelope binding mismatch'); END;
CREATE TRIGGER private_owned_imports_immutable BEFORE UPDATE ON private_owned_imports
BEGIN SELECT RAISE(ABORT,'restored records require an explicit new conflict resolution'); END;

INSERT INTO household_schema_versions VALUES('offmenu-private-portability/1',strftime('%Y-%m-%dT%H:%M:%fZ','now'));
