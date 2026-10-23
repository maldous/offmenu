-- offmenu-byoc-security/1 -- additive PREPARATION, not a deployed migration.
-- Apply after cloud/schema.sql, with foreign_keys=ON. No keys or credentials seeded.
-- Existing provider_connections and original opaque identity IDs remain untouched.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sec_key_references (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  custody TEXT NOT NULL CHECK(custody IN ('server-envelope','client')),
  external_key_ref TEXT NOT NULL CHECK(length(external_key_ref) BETWEEN 1 AND 256),
  key_version INTEGER NOT NULL CHECK(key_version >= 1),
  algorithm TEXT NOT NULL CHECK(algorithm = 'AES-256-GCM'),
  status TEXT NOT NULL CHECK(status IN ('active','decrypt-only','revoked','destroyed')),
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL CHECK(expires_at > created_at),
  revoked_at INTEGER,
  destroyed_at INTEGER,
  UNIQUE(owner_user_id,id,key_version,custody),
  UNIQUE(owner_user_id,external_key_ref,key_version),
  CHECK((status != 'revoked' OR revoked_at IS NOT NULL) AND
        (status != 'destroyed' OR destroyed_at IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS sec_envelopes (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  kitchen_id TEXT REFERENCES kitchens(id),
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  purpose TEXT NOT NULL,
  provider_id TEXT NOT NULL DEFAULT '',
  format_version INTEGER NOT NULL CHECK(format_version = 1),
  custody TEXT NOT NULL CHECK(custody IN ('server-envelope','client')),
  key_ref_id TEXT NOT NULL,
  key_version INTEGER NOT NULL CHECK(key_version >= 1),
  algorithm TEXT NOT NULL CHECK(algorithm = 'AES-256-GCM'),
  nonce BLOB NOT NULL CHECK(typeof(nonce)='blob' AND length(nonce)=12),
  ciphertext BLOB NOT NULL CHECK(typeof(ciphertext)='blob' AND length(ciphertext) BETWEEN 17 AND 1048592),
  created_at INTEGER NOT NULL,
  retain_until INTEGER NOT NULL CHECK(retain_until > created_at),
  revision INTEGER NOT NULL CHECK(revision >= 1),
  UNIQUE(owner_user_id,id),
  UNIQUE(kitchen_id,owner_user_id,id),
  UNIQUE(key_ref_id,key_version,nonce),
  FOREIGN KEY(owner_user_id,key_ref_id,key_version,custody)
    REFERENCES sec_key_references(owner_user_id,id,key_version,custody)
);

-- Choices are separate: connecting privately does not grant fact/aggregate contribution.
-- A profile is an object scope, not an identity provider user or a household-wide grant.
CREATE TABLE IF NOT EXISTS sec_consents (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  actor_user_id TEXT NOT NULL,
  object_type TEXT NOT NULL CHECK(object_type IN ('connection','household_profile','private_record')),
  object_id TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK(purpose IN ('private_use','profile_share','contribute_facts','contribute_aggregate','background_refresh')),
  grantee_user_id TEXT,
  audience_kitchen_id TEXT REFERENCES kitchens(id),
  notice_version TEXT NOT NULL,
  choice TEXT NOT NULL CHECK(choice IN ('granted','denied','withdrawn')),
  revision INTEGER NOT NULL CHECK(revision >= 1),
  valid_from INTEGER NOT NULL,
  expires_at INTEGER NOT NULL CHECK(expires_at > valid_from),
  updated_at INTEGER NOT NULL,
  UNIQUE(owner_user_id,id),
  CHECK(purpose != 'profile_share' OR grantee_user_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS sec_consents_object ON sec_consents(owner_user_id,object_type,object_id,purpose);
CREATE TABLE IF NOT EXISTS sec_consent_events (
  id TEXT PRIMARY KEY,
  consent_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  actor_user_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK(revision >= 1),
  choice TEXT NOT NULL CHECK(choice IN ('granted','denied','withdrawn')),
  notice_version TEXT NOT NULL,
  occurred_at INTEGER NOT NULL,
  retain_until INTEGER NOT NULL CHECK(retain_until > occurred_at),
  UNIQUE(consent_id,revision),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id)
);
CREATE TRIGGER IF NOT EXISTS sec_consent_events_no_update BEFORE UPDATE ON sec_consent_events
BEGIN SELECT RAISE(ABORT,'consent events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS sec_consent_events_retention BEFORE DELETE ON sec_consent_events
WHEN OLD.retain_until > unixepoch()
BEGIN SELECT RAISE(ABORT,'consent event retention has not ended'); END;

CREATE TABLE IF NOT EXISTS sec_provider_connections (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  provider_id TEXT NOT NULL,
  credential_kind TEXT NOT NULL CHECK(credential_kind IN ('api_key','oauth','browser_local')),
  custody TEXT NOT NULL CHECK(custody IN ('server-envelope','client','browser-local')),
  envelope_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','active','paused','expired','revoked','deleting','deleted')),
  entitlement_revision INTEGER NOT NULL CHECK(entitlement_revision >= 1),
  consent_id TEXT NOT NULL,
  consent_revision INTEGER NOT NULL CHECK(consent_revision >= 1),
  source_policy_id TEXT NOT NULL,
  source_policy_revision INTEGER NOT NULL CHECK(source_policy_revision >= 1),
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL CHECK(expires_at > created_at),
  revoked_at INTEGER,
  deleted_at INTEGER,
  UNIQUE(owner_user_id,id),
  FOREIGN KEY(owner_user_id,envelope_id) REFERENCES sec_envelopes(owner_user_id,id),
  FOREIGN KEY(owner_user_id,consent_id) REFERENCES sec_consents(owner_user_id,id),
  CHECK((custody='browser-local' AND credential_kind='browser_local' AND envelope_id IS NULL)
     OR (custody IN ('server-envelope','client') AND (envelope_id IS NOT NULL OR status='deleted'))),
  CHECK(status != 'revoked' OR revoked_at IS NOT NULL),
  CHECK(status != 'deleted' OR (deleted_at IS NOT NULL AND envelope_id IS NULL))
);
CREATE TABLE IF NOT EXISTS sec_connection_scopes (
  owner_user_id TEXT NOT NULL,
  connection_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  resource TEXT NOT NULL,
  purpose TEXT NOT NULL,
  PRIMARY KEY(connection_id,scope,resource,purpose),
  FOREIGN KEY(owner_user_id,connection_id) REFERENCES sec_provider_connections(owner_user_id,id)
);

-- Companion revocation metadata only: no replacement IdP/session issuance and no bearer.
CREATE TABLE IF NOT EXISTS sec_sessions (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  issuer TEXT NOT NULL,
  upstream_session_ref_hash TEXT NOT NULL CHECK(length(upstream_session_ref_hash)=64),
  audience TEXT NOT NULL,
  realm TEXT NOT NULL,
  epoch INTEGER NOT NULL CHECK(epoch >= 1),
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL CHECK(expires_at > created_at),
  revoked_at INTEGER,
  UNIQUE(owner_user_id,id),
  UNIQUE(issuer,upstream_session_ref_hash)
);

-- Each store gets an acknowledgement; complete requires all planned targets + restore replay.
CREATE TABLE IF NOT EXISTS sec_deletion_requests (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  requested_at INTEGER NOT NULL,
  deadline_at INTEGER NOT NULL CHECK(deadline_at > requested_at),
  evidence_retain_until INTEGER NOT NULL CHECK(evidence_retain_until > deadline_at),
  status TEXT NOT NULL CHECK(status IN ('requested','revoking','deleting','blocked','complete')),
  restore_replay_required INTEGER NOT NULL DEFAULT 1 CHECK(restore_replay_required IN (0,1)),
  completed_at INTEGER,
  UNIQUE(owner_user_id,id),
  CHECK(status != 'complete' OR (completed_at IS NOT NULL AND restore_replay_required=0))
);
CREATE TABLE IF NOT EXISTS sec_deletion_targets (
  request_id TEXT NOT NULL REFERENCES sec_deletion_requests(id),
  target_kind TEXT NOT NULL CHECK(target_kind IN ('credential','private_cache','raw_body','assertion','search','embedding','derivative','queued_job','contributor_link','backup_replay')),
  target_ref TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','removed','not_applicable','blocked')),
  evidence_ref TEXT,
  completed_at INTEGER,
  PRIMARY KEY(request_id,target_kind,target_ref),
  CHECK(status NOT IN ('removed','not_applicable') OR (evidence_ref IS NOT NULL AND completed_at IS NOT NULL))
);
CREATE TRIGGER IF NOT EXISTS sec_deletion_no_early_complete BEFORE UPDATE OF status ON sec_deletion_requests
WHEN NEW.status='complete' AND (NOT EXISTS(SELECT 1 FROM sec_deletion_targets WHERE request_id=NEW.id)
 OR EXISTS(SELECT 1 FROM sec_deletion_targets WHERE request_id=NEW.id AND status NOT IN ('removed','not_applicable')))
BEGIN SELECT RAISE(ABORT,'deletion targets are incomplete'); END;
CREATE TRIGGER IF NOT EXISTS sec_deletion_no_complete_insert BEFORE INSERT ON sec_deletion_requests
WHEN NEW.status='complete'
BEGIN SELECT RAISE(ABORT,'deletion must begin as a request'); END;

-- Value-free, restricted, retained audit. No URL/query, free-form payload or error fields.
CREATE TABLE IF NOT EXISTS sec_audit_events (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  actor_user_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK(action IN ('connect','rotate','revoke','use','deny','consent','delete','restore_replay')),
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('allowed','denied','pending','complete')),
  occurred_at INTEGER NOT NULL,
  retain_until INTEGER NOT NULL CHECK(retain_until > occurred_at)
);
CREATE TRIGGER IF NOT EXISTS sec_audit_events_no_update BEFORE UPDATE ON sec_audit_events
BEGIN SELECT RAISE(ABORT,'audit events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS sec_audit_events_retention BEFORE DELETE ON sec_audit_events
WHEN OLD.retain_until > unixepoch()
BEGIN SELECT RAISE(ABORT,'audit retention has not ended'); END;

CREATE TRIGGER IF NOT EXISTS sec_provider_binding_insert BEFORE INSERT ON sec_provider_connections
WHEN NEW.envelope_id IS NOT NULL AND NOT EXISTS(
 SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.provider_id=NEW.provider_id AND e.object_type='connection'
 AND e.object_id=NEW.id AND e.purpose='provider_credentials' AND e.custody=NEW.custody)
BEGIN SELECT RAISE(ABORT,'credential binding mismatch'); END;
CREATE TRIGGER IF NOT EXISTS sec_provider_binding_update BEFORE UPDATE ON sec_provider_connections
WHEN NEW.envelope_id IS NOT NULL AND NOT EXISTS(
 SELECT 1 FROM sec_envelopes e WHERE e.id=NEW.envelope_id AND e.owner_user_id=NEW.owner_user_id
 AND e.kitchen_id IS NULL AND e.provider_id=NEW.provider_id AND e.object_type='connection'
 AND e.object_id=NEW.id AND e.purpose='provider_credentials' AND e.custody=NEW.custody)
BEGIN SELECT RAISE(ABORT,'credential binding mismatch'); END;
CREATE TRIGGER IF NOT EXISTS sec_envelopes_immutable BEFORE UPDATE ON sec_envelopes
BEGIN SELECT RAISE(ABORT,'replace envelope through a new bound row'); END;
CREATE TRIGGER IF NOT EXISTS sec_key_identity_immutable BEFORE UPDATE OF id,owner_user_id,custody,external_key_ref,key_version,algorithm ON sec_key_references
BEGIN SELECT RAISE(ABORT,'key identity is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sec_consent_scope_immutable BEFORE UPDATE OF id,owner_user_id,object_type,object_id,purpose,grantee_user_id,audience_kitchen_id ON sec_consents
BEGIN SELECT RAISE(ABORT,'new consent is required for a changed scope'); END;
CREATE TRIGGER IF NOT EXISTS sec_provider_consent_insert BEFORE INSERT ON sec_provider_connections
WHEN NOT EXISTS(SELECT 1 FROM sec_consents c WHERE c.id=NEW.consent_id AND c.owner_user_id=NEW.owner_user_id
 AND c.object_type='connection' AND c.object_id=NEW.id AND c.purpose='private_use')
BEGIN SELECT RAISE(ABORT,'connection consent scope mismatch'); END;
CREATE TRIGGER IF NOT EXISTS sec_provider_consent_update BEFORE UPDATE ON sec_provider_connections
WHEN NOT EXISTS(SELECT 1 FROM sec_consents c WHERE c.id=NEW.consent_id AND c.owner_user_id=NEW.owner_user_id
 AND c.object_type='connection' AND c.object_id=NEW.id AND c.purpose='private_use')
BEGIN SELECT RAISE(ABORT,'connection consent scope mismatch'); END;
CREATE TRIGGER IF NOT EXISTS sec_deletion_targets_closed_insert BEFORE INSERT ON sec_deletion_targets
WHEN EXISTS(SELECT 1 FROM sec_deletion_requests WHERE id=NEW.request_id AND status='complete')
BEGIN SELECT RAISE(ABORT,'completed deletion evidence is closed'); END;
CREATE TRIGGER IF NOT EXISTS sec_deletion_targets_closed_update BEFORE UPDATE ON sec_deletion_targets
WHEN EXISTS(SELECT 1 FROM sec_deletion_requests WHERE id IN (OLD.request_id,NEW.request_id) AND status='complete')
BEGIN SELECT RAISE(ABORT,'completed deletion evidence is closed'); END;

CREATE TRIGGER IF NOT EXISTS sec_deletion_requests_closed_update BEFORE UPDATE ON sec_deletion_requests
WHEN OLD.status='complete'
BEGIN SELECT RAISE(ABORT,'completed deletion evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sec_deletion_requests_retention BEFORE DELETE ON sec_deletion_requests
WHEN OLD.evidence_retain_until > unixepoch()
BEGIN SELECT RAISE(ABORT,'deletion evidence retention has not ended'); END;
CREATE TRIGGER IF NOT EXISTS sec_deletion_targets_closed_delete BEFORE DELETE ON sec_deletion_targets
WHEN EXISTS(SELECT 1 FROM sec_deletion_requests WHERE id=OLD.request_id AND status='complete' AND evidence_retain_until > unixepoch())
BEGIN SELECT RAISE(ABORT,'deletion evidence retention has not ended'); END;
