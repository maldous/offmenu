"""Compact exact-identifier and terminology reconciliation, database-only.

Identifier nodes are keys, NOT verified real-world entities. Memberships and
relationships remain source assertions/candidates. This module cannot review,
translate, fetch, promote gold, merge entities, or read private app domains.
Call ingest_cache_keys with committed keys for an incremental event boundary;
backfill_page is a bounded keyset discovery helper, not a change-feed claim.
"""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3

from normalization_api import MAX_JSON_BYTES, NormalizationError
from normalization_core import (CompactNormalizationStore, artifact_digest,
    canonical_json, digest, validate_artifact, _secure_directory)
from normalization_domains import normalize_gtin

VERSION = 'offmenu-exact-reconciliation/1'
PUBLIC_DOMAINS = ('barcodes', 'ingredients', 'recipes', 'dietary', 'suppliers', 'citations')
BATCH_LIMIT = 128
MAX_BATCH_BYTES = 16 * 1024 * 1024
SOURCE_CUSTODY_BYTES = 65536  # Published normalization_engine admission contract.
# No source/provider namespace aliases are inferred. Deployments may extend this
# explicitly versioned registry; each extra namespace needs documentary provenance.
DEFAULT_REGISTRY = {
    'version': VERSION,
    'namespaces': {'gs1:gtin14': {
        'record_types': ['barcode'], 'kind': 'product_identifier', 'exclusive': True,
        'provenance': ['normalization_domains.normalize_gtin/gtin-syntax-v1'],
    }},
}


def _id(kind, *parts):
    return kind + ':' + digest(list(parts))


def _text(value, limit=4096):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def _pointer(base, key):
    return base + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _path(path, *, private=False):
    path = Path(os.path.abspath(path))
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise NormalizationError('symlink_reconciliation_path_refused')
    for suffix in ('-wal', '-shm', '-journal'):
        if Path(str(path) + suffix).is_symlink():
            raise NormalizationError('symlink_reconciliation_path_refused')
    if path.exists() and (not path.is_file() or (private and path.stat().st_mode & 0o077)):
        raise NormalizationError('regular_owned_reconciliation_file_required')
    return path


def _readonly(path, *, private=False):
    path = _path(path, private=private)
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA cache_size=-4096')
    return db


def _registry(value):
    value = json.loads(canonical_json(value))
    if set(value) != {'version', 'namespaces'} or not _text(value['version'], 256) or not isinstance(value['namespaces'], dict):
        raise NormalizationError('invalid_reconciliation_registry')
    for namespace, rule in value['namespaces'].items():
        if (not _text(namespace, 256) or not isinstance(rule, dict)
                or set(rule) != {'record_types', 'kind', 'exclusive', 'provenance'}
                or not isinstance(rule['record_types'], list) or not rule['record_types']
                or any(kind not in ('barcode', 'ingredient', 'recipe', 'menu', 'dietary_assertion', 'supplier', 'citation') for kind in rule['record_types'])
                or not _text(rule['kind'], 256) or type(rule['exclusive']) is not bool
                or not isinstance(rule['provenance'], list) or not rule['provenance']
                or any(not _text(item) for item in rule['provenance'])):
            raise NormalizationError('invalid_reconciliation_registry')
    return value


SCHEMA = '''
CREATE TABLE IF NOT EXISTS reconciliation_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS artifacts(
 cache_key TEXT PRIMARY KEY,artifact_sha256 TEXT NOT NULL,occurrence_id TEXT NOT NULL,
 slot_id TEXT NOT NULL,domain TEXT NOT NULL,source_key TEXT NOT NULL,source_version TEXT NOT NULL,
 record_id TEXT NOT NULL,content_sha256 TEXT NOT NULL,versions_sha256 TEXT NOT NULL,provenance_sha256 TEXT NOT NULL) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS artifacts_slot ON artifacts(slot_id,content_sha256);
CREATE TABLE IF NOT EXISTS nodes(node_id TEXT PRIMARY KEY,kind TEXT NOT NULL,namespace TEXT NOT NULL,scope TEXT NOT NULL,value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS memberships(cache_key TEXT NOT NULL REFERENCES artifacts(cache_key),node_id TEXT NOT NULL REFERENCES nodes(node_id),
 path TEXT NOT NULL,role TEXT NOT NULL,state TEXT NOT NULL,PRIMARY KEY(cache_key,node_id,path,role)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS memberships_node ON memberships(node_id,cache_key);
CREATE TABLE IF NOT EXISTS terms(term_id TEXT PRIMARY KEY,scope TEXT NOT NULL,language TEXT NOT NULL,
 text TEXT NOT NULL,unit TEXT NOT NULL,role TEXT NOT NULL) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS terms_lookup ON terms(scope,language,text,unit,role);
CREATE TABLE IF NOT EXISTS aliases(cache_key TEXT NOT NULL REFERENCES artifacts(cache_key),path TEXT NOT NULL,
 term_id TEXT NOT NULL REFERENCES terms(term_id),node_id TEXT NOT NULL REFERENCES nodes(node_id),
 state TEXT NOT NULL,PRIMARY KEY(cache_key,path,term_id,node_id)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS aliases_term ON aliases(term_id,node_id);
CREATE TABLE IF NOT EXISTS relations(edge_id TEXT PRIMARY KEY,cache_key TEXT NOT NULL REFERENCES artifacts(cache_key),
 path TEXT NOT NULL,kind TEXT NOT NULL,target_slot_id TEXT,target_node_id TEXT REFERENCES nodes(node_id),state TEXT NOT NULL) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS relations_target ON relations(target_slot_id);
CREATE TABLE IF NOT EXISTS measures(cache_key TEXT NOT NULL REFERENCES artifacts(cache_key),path TEXT NOT NULL,
 unit TEXT NOT NULL,dimension TEXT NOT NULL,value TEXT,min TEXT,max TEXT,basis TEXT,PRIMARY KEY(cache_key,path)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS issues(cache_key TEXT NOT NULL REFERENCES artifacts(cache_key),code TEXT NOT NULL,path TEXT NOT NULL,
 PRIMARY KEY(cache_key,code,path)) WITHOUT ROWID;
CREATE VIEW IF NOT EXISTS source_slot_conflicts AS
 SELECT slot_id FROM artifacts GROUP BY slot_id HAVING COUNT(DISTINCT content_sha256)>1;
CREATE VIEW IF NOT EXISTS effective_memberships AS
 SELECT m.*,a.domain,a.source_key,a.source_version,a.record_id,a.occurrence_id,
 CASE WHEN EXISTS(SELECT 1 FROM artifacts x WHERE x.slot_id=a.slot_id AND x.content_sha256<>a.content_sha256)
 THEN 'held_source_content_conflict' ELSE m.state END AS effective_state
 FROM memberships m JOIN artifacts a USING(cache_key);
CREATE VIEW IF NOT EXISTS effective_relations AS
 SELECT r.*, CASE WHEN EXISTS(SELECT 1 FROM artifacts x WHERE x.slot_id=a.slot_id AND x.content_sha256<>a.content_sha256)
 THEN 'held_source_content_conflict'
 WHEN r.state<>'source_asserted_candidate' THEN r.state
 WHEN r.target_node_id IS NOT NULL THEN 'source_asserted_candidate'
 WHEN EXISTS(SELECT 1 FROM artifacts x JOIN artifacts y ON x.slot_id=y.slot_id
  AND x.content_sha256<>y.content_sha256 WHERE x.slot_id=r.target_slot_id) THEN 'held_target_content_conflict'
 WHEN NOT EXISTS(SELECT 1 FROM artifacts x WHERE x.slot_id=r.target_slot_id) THEN 'unresolved_target_not_present'
 ELSE 'exact_source_reference_candidate' END AS effective_state
 FROM relations r JOIN artifacts a USING(cache_key);
'''


class ReconciliationStore:
    """Owned, policy-pinned compact sidecar; never opens source files itself."""
    BINDING = 'offmenu-compact-exact-reconciliation/1'

    def __init__(self, path, registry=None, *, disk_reserve_bytes=2 * 1024**3):
        if type(disk_reserve_bytes) is not int or not 0 <= disk_reserve_bytes <= 10**15:
            raise NormalizationError('invalid_reconciliation_disk_reserve')
        self.disk_reserve_bytes = disk_reserve_bytes
        self.registry = _registry(DEFAULT_REGISTRY if registry is None else registry)
        self.policy_sha256 = digest(self.registry)
        path = Path(os.path.abspath(path))
        _secure_directory(path.parent)
        self.path = _path(path, private=True)
        self._space(1024**2)
        if path.exists() and path.stat().st_size:
            with closing(_readonly(path, private=True)) as db:
                meta = dict(db.execute('SELECT key,value FROM reconciliation_meta'))
                if meta.get('binding') != self.BINDING or meta.get('policy_sha256') != self.policy_sha256:
                    raise NormalizationError('reconciliation_policy_or_binding_mismatch_use_new_sidecar')
        fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        self.db = sqlite3.connect(path, timeout=2)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA cache_size=-4096')
        self.db.executescript(SCHEMA)
        self.db.executemany('INSERT OR IGNORE INTO reconciliation_meta VALUES(?,?)', (
            ('binding', self.BINDING), ('policy_sha256', self.policy_sha256),
            ('registry_json', canonical_json(self.registry)), ('version', VERSION)))
        self.db.commit()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def close(self): self.db.close()

    def _space(self, needed=0):
        if shutil.disk_usage(self.path.parent).free < self.disk_reserve_bytes + needed:
            raise NormalizationError('reconciliation_disk_reserve')

    def _issue(self, key, code, path):
        self.db.execute('INSERT OR IGNORE INTO issues VALUES(?,?,?)', (key, code, path))

    def _node(self, kind, namespace, scope, value):
        node = _id('node', kind, namespace, scope, value)
        self.db.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?)', (node, kind, namespace, scope, value))
        return node

    def _member(self, key, node, path, role, state='source_asserted_candidate'):
        self.db.execute('INSERT OR IGNORE INTO memberships VALUES(?,?,?,?,?)', (key, node, path, role, state))

    def _alias(self, key, node, text, path, scope, language, role, unit='', state='source_asserted_candidate'):
        if not _text(text):
            return
        # Exact lexical tokens only; no casefold, trimming, transliteration,
        # translation or language inference. Unknown language is explicit und.
        term = _id('term', scope, language, text, unit, role)
        self.db.execute('INSERT OR IGNORE INTO terms VALUES(?,?,?,?,?,?)', (term, scope, language, text, unit, role))
        self.db.execute('INSERT OR IGNORE INTO aliases VALUES(?,?,?,?,?)', (key, path, term, node, state))
        if language == 'und':
            self._issue(key, 'term_language_unknown', path)

    def _quantity(self, key, quantity, path, basis=None):
        if not isinstance(quantity, dict): return
        if quantity.get('status') != 'normalized' or quantity.get('exact') is not True:
            self._issue(key, 'quantity_unresolved', path)
            return
        self.db.execute('INSERT OR IGNORE INTO measures VALUES(?,?,?,?,?,?,?,?)',
            (key, path, quantity['unit'], quantity['dimension'], quantity.get('value'), quantity.get('min'), quantity.get('max'), basis))

    def pending_keys(self, cache_keys):
        """Exact receipt lookup for event delivery/backfill; no source JSON replay."""
        if (not isinstance(cache_keys, (list, tuple)) or len(cache_keys) > BATCH_LIMIT
                or any(not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key) for key in cache_keys)):
            raise NormalizationError('invalid_reconciliation_cache_batch')
        return [key for key in cache_keys if self.db.execute(
            'SELECT 1 FROM artifacts WHERE cache_key=?', (key,)).fetchone() is None]

    def ingest_artifacts(self, artifacts, *, before_commit=None):
        """Verify source-bound rules artifacts and atomically persist compact facts.

        before_commit(db, result), when supplied, runs exactly once inside the
        transaction, including an empty batch. It may inspect page counts/budgets
        and write owner checkpoint/quarantine rows using execute/executemany.
        An exception rolls back facts and checkpoint together. The callback is
        trusted owner code, not source data, and must not change the authorizer,
        close the connection, or perform external side effects. Transaction-control
        SQL (including executescript's implicit commit) is denied during the hook.

        Original JSON is transient and never stored. Repeated identical cache keys
        are no-ops; changed content/rules retain separate evidence. All source
        versions coexist; there is deliberately no lexicographic latest winner.
        """
        if before_commit is not None and not callable(before_commit):
            raise NormalizationError('invalid_reconciliation_commit_hook')
        if not isinstance(artifacts, (list, tuple)) or len(artifacts) > BATCH_LIMIT:
            raise NormalizationError('reconciliation_batch_cap')
        # Validate before a transaction. This is an offline integrity check, not review.
        batch_bytes = 0
        for artifact in artifacts:
            if not isinstance(artifact, dict) or artifact.get('domain') not in PUBLIC_DOMAINS:
                raise NormalizationError('public_domain_required')
            batch_bytes += len(canonical_json(artifact).encode('utf-8'))
            if batch_bytes > MAX_BATCH_BYTES:
                raise NormalizationError('reconciliation_batch_bytes_cap')
            validate_artifact(artifact, verify_projection=True)
            if artifact['pass'] != 'rules':
                raise NormalizationError('rules_artifact_required')
        self._space(batch_bytes * 4 + 1024**2)
        new = reused = 0
        try:
            self.db.execute('BEGIN IMMEDIATE')
            for artifact in artifacts:
                key, sha = artifact['cache_key'], artifact_digest(artifact)
                existing = self.db.execute('SELECT artifact_sha256 FROM artifacts WHERE cache_key=?', (key,)).fetchone()
                if existing:
                    if existing != (sha,):
                        raise NormalizationError('immutable_reconciliation_artifact_conflict')
                    reused += 1
                    continue
                self._project(artifact, sha)
                new += 1
            result = {'new': new, 'reused': reused, 'gold_status': 'blocked', 'review_status': 'pendingreview'}
            if before_commit is not None:
                def transaction_guard(action, arg1, arg2, database, trigger):
                    return sqlite3.SQLITE_DENY if action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT) else sqlite3.SQLITE_OK
                self.db.set_authorizer(transaction_guard)
                try:
                    before_commit(self.db, dict(result))
                finally:
                    self.db.set_authorizer(None)
                if not self.db.in_transaction:
                    raise NormalizationError('reconciliation_commit_hook_ended_transaction')
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return result

    def _project(self, artifact, sha):
        source, key, kind = artifact['source'], artifact['cache_key'], artifact['record_type']
        slot = _id('slot', source['domain'], source['source_key'], source['source_version'], source['record_id'])
        occurrence = _id('occurrence', slot, source['content_sha256'])
        self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (key, sha, occurrence, slot, source['domain'], source['source_key'], source['source_version'],
             source['record_id'], source['content_sha256'], digest(artifact['versions']), digest(artifact['provenance'])))
        normalized = artifact['normalized']
        fields, language = normalized['fields'], normalized['language'] or 'und'
        term_scope = _id('scope', source['domain'], source['source_key'])
        claims = []
        for index, claim in enumerate(fields.get('identity_claims', [])):
            path = '/fields/identity_claims/' + str(index)
            if not isinstance(claim, dict) or not _text(claim.get('value')):
                self._issue(key, 'identifier_value_missing', path)
                continue
            namespace = claim.get('namespace')
            if not _text(namespace, 256):
                self._issue(key, 'identifier_namespace_missing', path)
                continue
            claims.append((namespace, claim['value'], path, 'source_asserted_candidate'))
        for index, barcode in enumerate(fields.get('barcodes', [])):
            path = '/fields/barcodes/' + str(index)
            value = barcode.get('gtin14')
            checked = normalize_gtin(value) if isinstance(value, str) else {}
            if isinstance(value, str) and checked.get('gtin14') == value:
                claims.append(('gs1:gtin14', value, path, 'syntax_only_identifier_candidate'))
            else:
                self._issue(key, 'barcode_identifier_unresolved', path)
        values = {}
        for namespace, value, _, _ in claims:
            values.setdefault(namespace, set()).add(value)
        if not claims:
            self._issue(key, 'global_identifier_unresolved', '/fields')
        primary = []
        for namespace, value, path, state in claims:
            rule = self.registry['namespaces'].get(namespace)
            if rule is None:
                # A provider string alone does not declare a worldwide ID system.
                scope, node_kind = _id('scope', source['domain'], source['source_key'], kind), 'source_scoped_identifier'
                self._issue(key, 'identifier_namespace_not_registered', path)
            else:
                scope, node_kind = '', rule['kind']
                if kind not in rule['record_types']:
                    state = 'held_namespace_record_type_conflict'
                    self._issue(key, state, path)
                if rule['exclusive'] and len(values[namespace]) > 1:
                    state = 'held_identifier_conflict'
                    self._issue(key, state, path)
            if namespace == 'gs1:gtin14' and normalize_gtin(value).get('gtin14') != value:
                state = 'held_identifier_lexeme_invalid'
                self._issue(key, state, path)
            node = self._node(node_kind, namespace, scope, value)
            self._member(key, node, path, 'asserts_identifier', state)
            if rule is not None and not state.startswith('held_'):
                primary.append(node)
        primary = sorted(set(primary))
        # No transitive equivalence between multiple IDs is inferred. Source
        # synonyms can label a single identifier key, otherwise their occurrence.
        alias_target = primary[0] if len(primary) == 1 else self._node('source_occurrence', 'offmenu:source-occurrence', '', occurrence)
        if len(primary) > 1:
            self._issue(key, 'multiple_identifier_systems_not_merged', '/fields/identity_claims')
        self._alias(key, alias_target, normalized['title'], '/title', term_scope, language, kind)
        for name in ('name_original', 'product_name', 'legal_name_original'):
            self._alias(key, alias_target, fields.get(name), '/fields/' + name, term_scope, language, kind)
        aliases = fields.get('aliases_original', [])
        if isinstance(aliases, str): aliases = [aliases]
        if isinstance(aliases, list):
            for index, text in enumerate(aliases):
                if isinstance(text, str):
                    self._alias(key, alias_target, text, '/fields/aliases_original/' + str(index), term_scope, language, kind)
                else:
                    self._issue(key, 'structured_alias_unresolved', '/fields/aliases_original/' + str(index))
        self._quantity(key, fields.get('quantity'), '/fields/quantity')
        for index, observation in enumerate(fields.get('nutrient_observations', [])):
            path = '/fields/nutrient_observations/' + str(index)
            nutrient = observation.get('nutrient_id')
            if isinstance(nutrient, int) and not isinstance(nutrient, bool): nutrient = str(nutrient)
            if _text(nutrient):
                node = self._node('source_nutrient_identifier', 'source:nutrient', source['source_key'], nutrient)
                self._member(key, node, path, 'observes_nutrient')
                quantity = observation.get('quantity', {})
                self._alias(key, node, observation.get('name'), path + '/name', term_scope, language,
                    'nutrient', quantity.get('unit', '') if quantity.get('status') == 'normalized' else '')
            else:
                self._issue(key, 'nutrient_identifier_missing', path)
            self._quantity(key, observation.get('quantity'), path + '/quantity', observation.get('basis'))
        for index, url in enumerate(fields.get('urls', [])):
            path = '/fields/urls/' + str(index)
            if _text(url.get('canonical')):
                node = self._node('url_locator', 'url:http', '', url['canonical'])
                self._member(key, node, path, 'asserts_' + url['source_field'], 'locator_only_not_document_equivalence')
        template = fields.get('recipe_menu_template', {})
        for index, ingredient in enumerate(template.get('ingredients', [])):
            path = '/fields/recipe_menu_template/ingredients/' + str(index)
            node = self._node('ingredient_mention', 'offmenu:recipe-mention', occurrence, str(index))
            self._member(key, node, path, 'contains_ingredient_mention', 'source_mention_not_food_identity')
            self._alias(key, node, ingredient.get('source_name'), path + '/source_name', term_scope, language, 'ingredient_mention', ingredient.get('source_unit') if isinstance(ingredient.get('source_unit'), str) else '')
            self._quantity(key, ingredient.get('quantity'), path + '/quantity')
            self._issue(key, 'ingredient_mention_identity_unresolved', path)
        for index, relation in enumerate(normalized['relations']):
            path = '/relations/' + str(index)
            self._relation(key, source, relation.get('source_assertion', relation), path)
        for index, relation in enumerate(template.get('menu_links', [])):
            self._relation(key, source, relation, '/fields/recipe_menu_template/menu_links/' + str(index))
        # Carry bounded codes/pointers, never source issue text or raw payload.
        for issue in artifact['issues']:
            self._issue(key, 'rules:' + issue['code'], issue['path'])

    def _relation(self, key, source, relation, path):
        if not isinstance(relation, dict):
            self._issue(key, 'relationship_shape_unresolved', path)
            return
        kind = relation.get('kind')
        target_domain, target_id = relation.get('target_domain'), relation.get('target_id')
        target_source = relation.get('target_source_key', source['source_key'])
        target_version = relation.get('target_source_version', source['source_version'])
        if (not _text(kind, 256) or target_domain not in PUBLIC_DOMAINS or not _text(target_id)
                or not _text(target_source) or not _text(target_version)):
            self._issue(key, 'relationship_exact_target_unresolved', path)
            return
        target = _id('slot', target_domain, target_source, target_version, target_id)
        edge = _id('edge', key, path, kind, target)
        self.db.execute('INSERT OR IGNORE INTO relations VALUES(?,?,?,?,?,?,?)',
            (edge, key, path, kind, target, None, 'source_asserted_candidate'))

    def resolve_term(self, text, *, scope, language, role, unit='', candidate_limit=32):
        """Bounded candidates within exact context; truncation can never resolve.

        Conflict existence is checked over the complete indexed term group, not
        merely the displayed prefix. The result retains at most candidate_limit
        nodes even for a common label with millions of unresolved occurrences.
        """
        if type(candidate_limit) is not int or not 1 <= candidate_limit <= BATCH_LIMIT:
            raise NormalizationError('invalid_terminology_candidate_limit')
        term = _id('term', scope, language, text, unit, role)
        rows = self.db.execute('SELECT DISTINCT node_id FROM aliases WHERE term_id=? ORDER BY node_id LIMIT ?',
                               (term, candidate_limit + 1)).fetchall()
        truncated = len(rows) > candidate_limit
        conflict = bool(rows) and bool(self.db.execute("""SELECT EXISTS(
            SELECT 1 FROM aliases x JOIN artifacts a USING(cache_key) WHERE x.term_id=?
            AND EXISTS(SELECT 1 FROM artifacts other WHERE other.slot_id=a.slot_id
                AND other.content_sha256<>a.content_sha256))""", (term,)).fetchone()[0])
        state = ('unresolved' if not rows else 'held_source_content_conflict' if conflict
                 else 'held_truncated_candidates' if truncated
                 else 'held_ambiguous_alias' if len(rows) != 1 else 'source_asserted_candidate')
        return {'status': state, 'candidate_node_ids': [row[0] for row in rows[:candidate_limit]],
                'candidate_truncated': truncated, 'source_conflict': conflict,
                'term_id': term, 'gold_status': 'blocked'}


    def report(self):
        """Count-only diagnostics; no names, IDs, URLs, source paths or payloads."""
        counts = {table: self.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                  for table in ('artifacts', 'nodes', 'memberships', 'terms', 'aliases', 'relations', 'measures')}
        reasons = dict(self.db.execute('SELECT code,COUNT(*) FROM issues GROUP BY code'))
        for state, count in self.db.execute("SELECT effective_state,COUNT(*) FROM effective_relations WHERE effective_state LIKE 'held_%' OR effective_state LIKE 'unresolved_%' GROUP BY effective_state"):
            reasons[state] = reasons.get(state, 0) + count
        for state, count in self.db.execute("SELECT effective_state,COUNT(*) FROM effective_memberships WHERE effective_state LIKE 'held_%' GROUP BY effective_state"):
            reasons[state] = max(reasons.get(state, 0), count)
        ambiguous = self.db.execute('SELECT COUNT(*) FROM (SELECT term_id FROM aliases GROUP BY term_id HAVING COUNT(DISTINCT node_id)>1)').fetchone()[0]
        if ambiguous:
            reasons['held_ambiguous_alias_terms'] = ambiguous
        conflicts = self.db.execute('SELECT COUNT(*) FROM source_slot_conflicts').fetchone()[0]
        return {'schema': VERSION, 'counts': counts, 'unresolved_reasons': reasons,
                'source_slot_conflicts': conflicts, 'policy_sha256': self.policy_sha256,
                'selection': 'all_retained_source_versions_no_current_truth_claim',
                'review_status': 'pendingreview', 'gold_status': 'blocked', 'entity_merges': 0}


_SOURCE_QUERY = '''SELECT r.source_key,r.source_version,r.record_id,r.content_sha256,
 CASE WHEN length(CAST(r.payload_json AS BLOB))<=? THEN r.payload_json ELSE NULL END,
 r.row_number,s.source_key,CASE WHEN length(s.license)<=4096 THEN s.license ELSE NULL END,
 CASE WHEN length(s.provider)<=4096 THEN s.provider ELSE NULL END,
 CASE WHEN length(CAST(s.custody_json AS BLOB))<=? THEN s.custody_json ELSE NULL END
 FROM records r LEFT JOIN sources s ON r.source_key=s.source_key AND r.source_version=s.version
 WHERE r.source_key=? AND r.source_version=? AND r.record_id=?'''


def ingest_cache_keys(state_dir, domain, cache_keys, output, *, before_commit=None):
    """Read a bounded committed-key batch; sources/cache are mode=ro/query_only.

    Suitable at a writer's completed normalization batch boundary. Source
    transaction lasts for at most one key batch, never the entire corpus. A
    stale/missing/tampered key rejects the whole batch without a partial receipt.
    No arbitrary source path from source metadata is opened.
    """
    if domain not in PUBLIC_DOMAINS:
        raise NormalizationError('public_domain_required')
    if (not isinstance(cache_keys, (list, tuple)) or len(cache_keys) > BATCH_LIMIT
            or any(not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key) for key in cache_keys)):
        raise NormalizationError('invalid_reconciliation_cache_batch')
    state = Path(os.path.abspath(state_dir))
    cache_path = state / 'normalization-private' / ('compact-' + domain + '.sqlite3')
    source_path = state / 'staging' / (domain + '.sqlite3')
    records = []
    batch_bytes = 0
    with closing(_readonly(cache_path, private=True)) as cache, closing(_readonly(source_path)) as source:
        if cache.execute("SELECT value FROM compact_meta WHERE key='binding'").fetchone() != (CompactNormalizationStore.BINDING,):
            raise NormalizationError('non_owned_compact_cache')
        meta = dict(source.execute("SELECT key,value FROM ingest_meta WHERE key IN ('binding','schema_version','domain')"))
        if meta != {'binding': 'additive_staging_not_app_bound', 'schema_version': '1', 'domain': domain}:
            raise NormalizationError('non_owned_source_database')
        reader = object.__new__(CompactNormalizationStore)
        reader.db = cache
        source.execute('BEGIN')
        cache.execute('BEGIN')
        for key in cache_keys:
            size = cache.execute('SELECT length(body_zlib) FROM rules_cache WHERE cache_key=?', (key,)).fetchone()
            if size and size[0] > MAX_JSON_BYTES:
                raise NormalizationError('compact_cache_size_cap')
            compact = reader.get_compact(key)
            if compact is None:
                raise NormalizationError('compact_cache_missing')
            body = compact[0]
            if body.get('domain') != domain or body['source'].get('domain') != domain:
                raise NormalizationError('cache_domain_mismatch')
            ref = body['source']
            row = source.execute(_SOURCE_QUERY, (MAX_JSON_BYTES, SOURCE_CUSTODY_BYTES, ref['source_key'], ref['source_version'], ref['record_id'])).fetchone()
            if row is None or row[4] is None:
                raise NormalizationError('source_missing_or_size_cap')
            provenance = {'license': row[7], 'provider': row[8], 'custody': json.loads(row[9]) if row[9] else None, 'rights_status': 'unverified'}
            if row[6] is None: provenance['source_metadata_status'] = 'missing'
            record = {'domain': domain, 'source_key': row[0], 'source_version': row[1], 'record_id': row[2],
                      'content_sha256': row[3], 'payload': json.loads(row[4]), 'row_number': row[5], 'provenance': provenance}
            artifact = reader.resolve(key, record)
            batch_bytes += len(canonical_json(artifact).encode('utf-8'))
            if batch_bytes > MAX_BATCH_BYTES:
                raise NormalizationError('reconciliation_batch_bytes_cap')
            records.append(artifact)
    # Source read snapshots are released before output transaction/verification.
    return output.ingest_artifacts(records, before_commit=before_commit)


def backfill_page(state_dir, domain, *, after=None, limit=BATCH_LIMIT):
    """Discover one deterministic cache-key page without copying compressed blobs.

    Pass returned keys to ingest_cache_keys and advance only after its successful
    commit. Restart at None after a normalization snapshot changes; receipts
    deduplicate unchanged keys. Exact newly committed-key events avoid that full
    discovery pass. Never rely on rowid surviving VACUUM/replacement.
    """
    if domain not in PUBLIC_DOMAINS:
        raise NormalizationError('public_domain_required')
    if type(limit) is not int or not 1 <= limit <= BATCH_LIMIT or (after is not None and (not isinstance(after, str) or not re.fullmatch(r'[0-9a-f]{64}', after))):
        raise NormalizationError('invalid_reconciliation_page')
    path = Path(state_dir) / 'normalization-private' / ('compact-' + domain + '.sqlite3')
    with closing(_readonly(path, private=True)) as cache:
        if cache.execute("SELECT value FROM compact_meta WHERE key='binding'").fetchone() != (CompactNormalizationStore.BINDING,):
            raise NormalizationError('non_owned_compact_cache')
        return [row[0] for row in cache.execute('SELECT cache_key FROM rules_cache WHERE cache_key>? ORDER BY cache_key LIMIT ?', (after or '', limit))]
