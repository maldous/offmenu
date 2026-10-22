"""Disposable SQLite contract checks. Not remote D1/application runtime acceptance."""
import sqlite3
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / 'cloud/migrations/20261022-byoc-security-v1.sql'
class SecuritySchema(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript((ROOT/'cloud/schema.sql').read_text())
        self.db.executescript(MIGRATION.read_text())
        self.db.execute("INSERT INTO kitchens VALUES('k','Fixture',1,'{}','2026-10-22')")
    def tearDown(self): self.db.close()
    def insert(self,table,**values):
        self.db.execute(f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})",list(values.values()))
    def key(self,owner='a',id='key'):
        self.insert('sec_key_references',id=id,owner_user_id=owner,custody='server-envelope',external_key_ref='opaque-fixture-'+id,key_version=1,algorithm='AES-256-GCM',status='active',created_at=1,expires_at=200)
    def envelope(self,**overrides):
        row=dict(id='env',owner_user_id='a',kitchen_id=None,object_type='connection',object_id='conn',purpose='provider_credentials',provider_id='provider',format_version=1,custody='server-envelope',key_ref_id='key',key_version=1,algorithm='AES-256-GCM',nonce=bytes(12),ciphertext=bytes(17),created_at=1,retain_until=200,revision=1)
        row.update(overrides);self.insert('sec_envelopes',**row)
    def consent(self):
        self.insert('sec_consents',id='consent',owner_user_id='a',actor_user_id='a',object_type='connection',object_id='conn',purpose='private_use',notice_version='fixture/1',choice='granted',revision=1,valid_from=1,expires_at=200,updated_at=1)
    def connection(self,**overrides):
        row=dict(id='conn',owner_user_id='a',provider_id='provider',credential_kind='api_key',custody='server-envelope',envelope_id='env',status='active',entitlement_revision=1,consent_id='consent',consent_revision=1,source_policy_id='fixture-policy',source_policy_revision=1,created_at=1,expires_at=200)
        row.update(overrides);self.insert('sec_provider_connections',**row)
    def test_repeatable_additive_preserves_legacy_ciphertext(self):
        self.db.execute("INSERT INTO provider_connections VALUES('legacy','p','Fixture','legacy-sealed','2026-10-22')")
        self.db.executescript(MIGRATION.read_text())
        self.assertEqual(self.db.execute('SELECT sealed FROM provider_connections').fetchone(),('legacy-sealed',))
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
    def test_owner_key_nonce_and_envelope_immutability(self):
        self.key();self.envelope()
        for override in [dict(id='b',owner_user_id='b'),dict(id='b'),dict(id='b',nonce=b'short'),dict(id='b',nonce=bytes([1])*12,ciphertext='PLAINTEXT')]:
            with self.assertRaises(sqlite3.IntegrityError):self.envelope(**override)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_envelopes SET owner_user_id='b'")
    def test_connection_provider_and_scope_binding(self):
        self.key();self.envelope();self.consent()
        with self.assertRaises(sqlite3.IntegrityError):self.connection(provider_id='other')
        self.connection()
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_provider_connections SET provider_id='other'")
        with self.assertRaises(sqlite3.IntegrityError):self.insert('sec_connection_scopes',owner_user_id='b',connection_id='conn',scope='lookup',resource='provider',purpose='private_use')
    def test_browser_local_cannot_persist_cookie_envelope(self):
        self.key();self.envelope();self.consent()
        with self.assertRaises(sqlite3.IntegrityError):self.connection(credential_kind='browser_local',custody='browser-local')
        self.connection(credential_kind='browser_local',custody='browser-local',envelope_id=None)
    def test_consent_revision_history_and_explicit_profile_share(self):
        self.consent()
        row=dict(id='event',consent_id='consent',owner_user_id='a',actor_user_id='a',revision=1,choice='granted',notice_version='fixture/1',occurred_at=1,retain_until=9999999999)
        self.insert('sec_consent_events',**row)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_consent_events SET choice='withdrawn'")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('DELETE FROM sec_consent_events')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_consents SET purpose='profile_share'")
    def test_deletion_requires_targets_and_restore_replay(self):
        self.insert('sec_deletion_requests',id='delete',owner_user_id='a',object_type='connection',object_id='conn',requested_at=1,deadline_at=200,evidence_retain_until=9999999999,status='requested')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_deletion_requests SET status='complete',completed_at=2,restore_replay_required=0")
        self.insert('sec_deletion_targets',request_id='delete',target_kind='backup_replay',target_ref='fixture',status='pending')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_deletion_requests SET status='complete',completed_at=2,restore_replay_required=0")
        self.db.execute("UPDATE sec_deletion_targets SET status='removed',evidence_ref='fixture-receipt',completed_at=2")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_deletion_requests SET status='complete',completed_at=2")
        self.db.execute("UPDATE sec_deletion_requests SET status='complete',completed_at=2,restore_replay_required=0")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('DELETE FROM sec_deletion_targets')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('DELETE FROM sec_deletion_requests')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_deletion_requests SET status='requested'")
        self.insert('sec_deletion_requests',id='open',owner_user_id='a',object_type='connection',object_id='open',requested_at=1,deadline_at=200,evidence_retain_until=9999999999,status='requested')
        self.insert('sec_deletion_targets',request_id='open',target_kind='search',target_ref='new',status='pending')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE sec_deletion_targets SET request_id='delete' WHERE request_id='open'")
        # An independently planned short-retention synthetic request can be purged
        # after its explicit evidence horizon; no permanent personal audit retention.
        self.insert('sec_deletion_requests',id='expired',owner_user_id='a',object_type='connection',object_id='old',requested_at=1,deadline_at=2,evidence_retain_until=3,status='requested')
        self.insert('sec_deletion_targets',request_id='expired',target_kind='backup_replay',target_ref='fixture-old',status='removed',evidence_ref='fixture-receipt',completed_at=2)
        self.db.execute("UPDATE sec_deletion_requests SET status='complete',completed_at=2,restore_replay_required=0 WHERE id='expired'")
        self.db.execute("DELETE FROM sec_deletion_targets WHERE request_id='expired'")
        self.db.execute("DELETE FROM sec_deletion_requests WHERE id='expired'")
    def test_no_new_plaintext_secret_or_generic_payload_columns(self):
        names=[r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sec_%'")]
        forbidden={'password','secret','access_token','refresh_token','cookie','body','payload','request_url'}
        for name in names:self.assertFalse(forbidden & {r[1] for r in self.db.execute(f'PRAGMA table_info({name})')})
if __name__=='__main__':unittest.main()
