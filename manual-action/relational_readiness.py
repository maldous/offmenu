"""Offline, read-only retained-staging evidence, never an application/FETCH gate.

No ingestion, network, raw-store discovery, normalization writes, or orchestration.
The callable build_report(state_dir) is suitable for an existing one-command
runner after its terminal receipt is durable. Only the CLI writes report files.
"""
from __future__ import annotations
from runner_paths import resolve_layout

import argparse
import contextlib
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import time

from ingest_api import DOMAINS, source_key

SCHEMA = 'offmenu.retained-relational-readiness/1'
RULE_VERSION = 'offmenu.exact-staging-crosswalks/1'
BINDING = 'additive_staging_not_app_bound'
PRIVATE = frozenset(('user_profiles', 'inventory'))
DISPOSITIONS = ('resolved', 'missing', 'ambiguous', 'unsupported')
CONTRACTS = {
    'recipe_mentions': ('recipes', 'has_ingredient_mention', 'ingredients', 'ingredient_of'),
    'mention_recipe': ('ingredients', 'ingredient_of', 'recipes', 'has_ingredient_mention'),
    'menu_entries': ('recipes', 'contains_menu_entry', 'recipes', None),
    'supplier_entities': ('suppliers', None, 'suppliers', None),
}
SUPPLIER_KINDS = frozenset(('owned_by', 'parent_organization', 'subsidiary'))
SUPPLIER_ENTITY_TYPES = frozenset(('organization', 'supplier_entity'))
TABLES = ('sources', 'records', 'record_fields', 'relations', 'source_errors')
GAPS = {
    'barcodes': 'native_product_tables_and_typed_identifier_bridge_unavailable',
    'ingredients': 'ingredient_entity_and_product_identifier_bridge_unavailable',
    'recipes': 'cross_source_menu_recipe_and_venue_contract_unavailable',
    'dietary': 'typed_provider_food_identifier_and_nutrient_basis_contract_unavailable',
    'user_profiles': 'private_identity_adapter_and_access_isolation_unverified',
    'inventory': 'private_item_and_product_identifier_contract_unavailable',
    'suppliers': 'cross_source_entity_mapping_and_canonical_registry_unavailable',
    'citations': 'complete_record_to_citation_and_rights_contract_unavailable',
}
NORM_COUNTS = ('no_artifact', 'rules_only', 'review_pending', 'review_rejected',
               'validated_interpreted', 'unresolved_error', 'ambiguous_versions',
               'translation_pending', 'gold_blocked', 'gold_unknown')


class ReadinessError(ValueError):
    """A fixed diagnostic code, never source contents or exception text."""


@dataclass(frozen=True)
class Limits:
    max_seconds: float = 120
    max_records: int = 200000
    max_relations: int = 1000000
    max_json_bytes: int = 8 * 1024 * 1024
    max_total_json_bytes: int = 512 * 1024 * 1024
    max_sql_steps: int = 100000000
    max_metadata_rows: int = 100000
    max_json_depth: int = 40
    max_json_nodes: int = 200000

    def __post_init__(self):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
               for v in asdict(self).values()):
            raise ReadinessError('invalid_resource_budget')
        if any(not isinstance(v, int) for k, v in asdict(self).items() if k != 'max_seconds'):
            raise ReadinessError('invalid_resource_budget')


class Budget:
    def __init__(self, limits):
        self.limits = limits
        self.started = time.monotonic()
        self.records = self.relations = self.json_bytes = self.sql_steps = 0

    def check(self):
        if time.monotonic() - self.started > self.limits.max_seconds:
            raise ReadinessError('resource_budget_exhausted')

    def progress(self):
        self.sql_steps += 1000
        return int(time.monotonic() - self.started > self.limits.max_seconds
                   or self.sql_steps > self.limits.max_sql_steps)

    def take(self, name):
        self.check()
        value = getattr(self, name) + 1
        if value > getattr(self.limits, 'max_' + name):
            raise ReadinessError('resource_budget_exhausted')
        setattr(self, name, value)

    def parse(self, raw):
        self.check()
        size = len(raw.encode('utf-8')) if isinstance(raw, str) else len(raw)
        self.json_bytes += size
        if size > self.limits.max_json_bytes or self.json_bytes > self.limits.max_total_json_bytes:
            raise ReadinessError('resource_budget_exhausted')
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out:
                    raise ReadinessError('duplicate_json_key')
                out[key] = value
            return out
        def bad_constant(_):
            raise ReadinessError('invalid_json_number')
        try:
            result = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
        except (ValueError, TypeError, RecursionError, UnicodeError):
            raise ReadinessError('invalid_bounded_json') from None
        stack, count = [(result, 0)], 0
        while stack:
            value, depth = stack.pop()
            count += 1
            if depth > self.limits.max_json_depth or count > self.limits.max_json_nodes:
                raise ReadinessError('resource_budget_exhausted')
            if isinstance(value, dict):
                stack.extend((v, depth + 1) for v in value.values())
            elif isinstance(value, list):
                stack.extend((v, depth + 1) for v in value)
        return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ReadinessError('symlink_path_refused')
    return path


def file_identity(path):
    path = safe_path(path)
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(st.st_mode):
        raise ReadinessError('nonregular_file_refused')
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]


def database_identity(path):
    return {'main': file_identity(path), 'wal': file_identity(str(path) + '-wal')}


def store_path(state, domain):
    return resolve_layout(state).domain_path(domain)


def read_json_file(path, budget):
    path = safe_path(path)
    if file_identity(path) is None:
        raise ReadinessError('metadata_file_missing')
    with path.open('rb') as stream:
        raw = stream.read(budget.limits.max_json_bytes + 1)
    value = budget.parse(raw)
    if not isinstance(value, dict):
        raise ReadinessError('metadata_object_required')
    return value, hashlib.sha256(raw).hexdigest()


def open_readonly(path, budget, *, quiescent=False):
    """Immutable reads ONLY after caller-bound terminal/no-writer/no-WAL checks.

    A normal mode=ro connection can create source WAL/SHM files or delay writers.
    No immutable read is allowed when any WAL is present, even an empty WAL.
    Before/after identities remain mandatory; immutable does not prove atomicity.
    """
    path = safe_path(path)
    if file_identity(path) is None:
        raise ReadinessError('database_missing')
    if not quiescent:
        raise ReadinessError('quiescent_terminal_snapshot_not_established')
    if file_identity(str(path) + '-wal') is not None:
        raise ReadinessError('wal_present_read_deferred_without_copy_or_source_mutation')
    if file_identity(str(path) + '-journal') is not None:
        raise ReadinessError('rollback_journal_present_read_deferred')
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True, timeout=.1)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('PRAGMA temp_store=MEMORY')
        db.set_progress_handler(budget.progress, 1000)
        db.execute('BEGIN')
        return db
    except BaseException:
        db.close()
        raise


def observe_writer_lock(path):
    """Observe Linux lock metadata; never acquire a lock even momentarily.

    Acquiring a shared lock could reject DomainStore's nonblocking writer, so
    lack of a portable read-only lock query is reported as unknown instead.
    This observation does not exclude future/uncooperative external writers.
    """
    lock = safe_path(path.with_suffix('.writer.lock'))
    ident = file_identity(lock)
    if ident is None:
        return 'unknown_missing_writer_lock'
    expected = (os.major(ident[0]), os.minor(ident[0]), ident[1])
    try:
        with open('/proc/locks', 'rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return 'unknown_lock_metadata_unavailable'
        for line in raw.decode('ascii').splitlines():
            fields = line.split()
            if 'WRITE' not in fields:
                continue
            for field in fields:
                parts = field.split(':')
                if len(parts) == 3:
                    try:
                        match = (int(parts[0], 16), int(parts[1], 16), int(parts[2]))
                    except ValueError:
                        continue
                    if match == expected:
                        return 'writer_active'
        return 'no_writer_observed'
    except (OSError, UnicodeError):
        return 'unknown_lock_metadata_unavailable'



def limited_rows(cursor, budget):
    rows = []
    for row in cursor:
        budget.check()
        if len(rows) >= budget.limits.max_metadata_rows:
            raise ReadinessError('metadata_row_budget_exhausted')
        rows.append(row)
    return rows


def identity(domain, row):
    return dict(zip(('domain', 'source_key', 'source_version', 'record_id', 'content_sha256'),
                    (domain, *row[:4])))


def key_of(record):
    return tuple(record[k] for k in ('domain', 'source_key', 'source_version', 'record_id'))


def identifier(value):
    # Native string/integer identifiers only; never floats, bools, stripping,
    # case folding, name fallback, or conversion of a generated hash into an ID.
    if isinstance(value, str) and value and len(value) <= 4096:
        return value, 'string'
    if type(value) is int:
        return str(value), 'integer'
    return None


def initial_domain():
    return {'status': 'unknown', 'coverage': 'incomplete', 'integrity': 'unknown',
            'foreign_keys': 'unknown', 'source_selection': 'unknown',
            'scope': 'unknown', 'diagnostics': [], 'table_counts': {},
            'selected_sources': [], 'historical_records': None,
            'selected_records': None, 'scanned_records': 0, 'payload_hash_mismatches': 0,
            'reference_records': 0, 'relations': None, 'scanned_relations': 0,
            'missing_scope_fields': 0, 'duplicate_scoped_keys': 0,
            'cross_scope_attempts': 0, 'native_external_rows': None,
            'normalization': {'status': 'unknown', **dict.fromkeys(NORM_COUNTS, 0)},
            'adapter_gap': 'unknown'}


def receipt_inputs(state, budget):
    details, hashes, before = {}, {}, {}
    for name in ('catalog.private.json', 'last-run.private.json', 'last-report.json'):
        before[name] = file_identity(state / name)
        details[name], hashes[name] = read_json_file(state / name, budget)
    catalog, receipt, public = (details[n] for n in ('catalog.private.json', 'last-run.private.json', 'last-report.json'))
    report = receipt.get('report', {})
    if not isinstance(report, dict) or not isinstance(receipt.get('domains'), dict):
        raise ReadinessError('terminal_receipt_invalid')
    sources = catalog.get('sources')
    if not isinstance(sources, list) or any(not isinstance(s, dict) for s in sources):
        raise ReadinessError('catalog_invalid')
    # Same catalog-descriptor hash as prepare_default; NOT a raw-source checksum.
    catalog_digest = hashlib.sha256(json.dumps(sources, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
    valid = (report.get('schema') == 'offmenu-ingest-report/1'
             and report.get('status') in ('complete', 'partial', 'failed')
             and bool(report.get('run_id'))
             and all(public.get(k) == report.get(k) for k in ('run_id', 'catalog_sha256', 'status'))
             and report.get('catalog_sha256') == catalog_digest
             and not catalog.get('truncated') and catalog.get('complete') is not False
             and report.get('catalog_truncated') is False)
    return receipt, catalog, {'status': 'bound' if valid else 'unknown', 'run_id': report.get('run_id'),
        'metadata_sha256': hashes, 'catalog_descriptor_sha256': catalog_digest,
        'raw_source_custody': 'not_established_by_metadata_fingerprints',
        'before': before}


def select_sources(domain, receipt, catalog):
    expected = receipt.get('domains', {}).get(domain)
    if not isinstance(expected, dict) or not isinstance(expected.get('sources'), list):
        raise ReadinessError('domain_receipt_missing')
    selected, issues = {}, []
    for item in expected['sources']:
        if not isinstance(item, dict):
            issues.append('invalid_source_receipt')
            continue
        sk, version = item.get('source_key'), item.get('source_version')
        if not isinstance(sk, str) or not isinstance(version, str) or not sk or not version:
            issues.append('source_version_receipt_missing')
            continue
        if sk in selected and selected[sk] != version:
            issues.append('multiple_selected_source_versions')
        selected[sk] = version
        if item.get('status') not in ('complete', 'imported', 'reused') or item.get('errors', 0):
            issues.append('source_receipt_not_complete')
    assigned = set()
    for source in catalog['sources']:
        domains = source.get('domains', source.get('domain', []))
        domains = [domains] if isinstance(domains, str) else domains
        if isinstance(domains, list) and domain in domains:
            assigned.add(source_key(source))
    if assigned != set(selected):
        issues.append('catalog_assignments_not_exactly_reconciled')
    return expected, selected, sorted(set(issues))


def scan_domain(domain, db, receipt, catalog, budget, result, records, edges):
    # No arbitrary table/SQL from payloads, catalogs or manifest inputs.
    objects = limited_rows(db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"), budget)
    result['schema_objects'] = [dict(zip(('type', 'name', 'table', 'sql'), row)) for row in objects]
    object_types = {r[1]: r[0] for r in objects}
    if any(object_types.get(t) != 'table' for t in (*TABLES, 'ingest_meta')):
        raise ReadinessError('unsupported_staging_schema')
    meta = dict(limited_rows(db.execute('SELECT key,value FROM ingest_meta'), budget))
    result['metadata'] = meta
    if meta.get('domain') != domain or meta.get('binding') != BINDING or meta.get('schema_version') != '1' or not meta.get('database_id'):
        raise ReadinessError('unowned_or_incompatible_staging')
    result['status'] = 'observed'
    result['schema_metadata'] = {}
    for table in TABLES:
        result['schema_metadata'][table] = {
            'columns': limited_rows(db.execute('PRAGMA table_info(' + table + ')'), budget),
            'indexes': limited_rows(db.execute('PRAGMA index_list(' + table + ')'), budget),
            'foreign_keys': limited_rows(db.execute('PRAGMA foreign_key_list(' + table + ')'), budget)}
        result['table_counts'][table] = db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
    check = limited_rows(db.execute('PRAGMA integrity_check'), budget)
    result['integrity'] = 'ok' if check == [('ok',)] else 'failed'
    result['integrity_diagnostics'] = check
    violations = limited_rows(db.execute('PRAGMA foreign_key_check'), budget)
    result['foreign_keys'] = 'ok' if not violations else 'failed'
    result['foreign_key_violations'] = violations
    expected, selected, selection_issues = select_sources(domain, receipt, catalog)
    result['selected_records'] = result['relations'] = 0
    result['diagnostics'].extend(selection_issues)
    if expected.get('database_id') != meta['database_id'] or expected.get('stored_records') != result['table_counts']['records']:
        result['diagnostics'].append('terminal_output_identity_or_count_mismatch')
    try:
        if int(meta.get('record_count', '-1')) != result['table_counts']['records']:
            result['diagnostics'].append('cached_record_count_mismatch')
    except (ValueError, TypeError):
        result['diagnostics'].append('cached_record_count_invalid')
    source_rows = limited_rows(db.execute('SELECT source_key,version,provider,status,errors FROM sources ORDER BY source_key,version'), budget)
    source_index = {(r[0], r[1]): r for r in source_rows}
    result['source_states'] = [dict(zip(('source_key', 'source_version', 'provider', 'status', 'errors'), row)) for row in source_rows]
    for sk, version in sorted(selected.items()):
        row = source_index.get((sk, version))
        if row is None:
            result['diagnostics'].append('selected_source_version_missing')
            continue
        if row[3] != 'complete' or row[4]:
            result['diagnostics'].append('selected_source_not_complete')
        count = db.execute('SELECT count(*) FROM records WHERE source_key=? AND source_version=?', (sk, version)).fetchone()[0]
        result['selected_sources'].append({'source_key': sk, 'source_version': version, 'records': count})
        result['selected_records'] += count
        result['relations'] += db.execute('SELECT count(*) FROM relations WHERE source_key=? AND source_version=?', (sk, version)).fetchone()[0]
        for record_row in db.execute('SELECT source_key,source_version,record_id,content_sha256,payload_json FROM records WHERE source_key=? AND source_version=? ORDER BY record_id', (sk, version)):
            budget.take('records')
            payload = budget.parse(record_row[4])
            if not isinstance(payload, dict):
                raise ReadinessError('staged_payload_not_object')
            valid_hash = digest(payload) == record_row[3]
            result['payload_hash_mismatches'] += not valid_hash
            ident = identity(domain, record_row)
            records[key_of(ident)] = {'identity': ident, 'payload': payload, 'provider': row[2], 'hash_valid': valid_hash}
            result['reference_records'] += payload.get('type') == 'readonly_source_reference' or payload.get('kind') == 'readonly_source_reference'
            result['scanned_records'] += 1
        for edge in db.execute('SELECT source_key,source_version,record_id,ordinal,kind,target_domain,target_id,detail_json FROM relations WHERE source_key=? AND source_version=? ORDER BY record_id,ordinal', (sk, version)):
            budget.take('relations')
            detail = budget.parse(edge[7])
            if not isinstance(detail, dict):
                raise ReadinessError('relation_detail_not_object')
            edges.append({'domain': domain, 'source_key': edge[0], 'source_version': edge[1], 'record_id': edge[2],
                          'ordinal': edge[3], 'kind': edge[4], 'target_domain': edge[5], 'target_id': edge[6], 'detail': detail})
            result['scanned_relations'] += 1
    result['historical_records'] = result['table_counts']['records'] - result['selected_records']
    result['source_selection'] = 'exact' if not result['diagnostics'] else 'unknown'
    result['coverage'] = 'complete' if (result['source_selection'] == 'exact' and result['integrity'] == 'ok'
                                      and result['foreign_keys'] == 'ok' and not result['payload_hash_mismatches']) else 'incomplete'
    if domain in PRIVATE and not selected and not result['table_counts']['records'] and expected.get('status') in ('schema_only', 'awaiting_user_input'):
        result['status'] = 'schema_only_app_managed'  # Staging observation, not app migration readiness.
        result['scope'] = 'not_exercised_no_input'
    result['adapter_gap'] = GAPS[domain]


def lookup_key(domain, namespace, provider, sk, version, native):
    return {'target_domain': domain, 'identifier_namespace': namespace, 'provider': provider,
            'source_key': sk, 'source_version': version, 'source_native_id_lexical': native}


def exact_resolution(key, candidates, *, snapshot_id, contract, reason=None, value_type='string', evidence=None):
    # Separate identifier claim from selected record identity. Equal native IDs
    # in two provenance rows remain ambiguous, not implicitly one organization.
    unique = {tuple(t[k] for k in ('domain', 'source_key', 'source_version', 'record_id', 'content_sha256')): t for t in candidates}
    targets = list(unique.values())
    disposition = 'unsupported' if reason else ('missing' if not targets else 'resolved' if len(targets) == 1 else 'ambiguous')
    return {'lookup_key': key, 'selected_snapshot_id': snapshot_id,
            'join_contract_id': contract, 'mapping_rule_version': RULE_VERSION,
            'disposition': disposition, 'reason_code': reason or {'missing': 'no_exact_scoped_target', 'resolved': 'unique_exact_scoped_target', 'ambiguous': 'multiple_provenance_targets'}[disposition],
            'source_value_type': value_type, 'targets': targets,
            'evidence': evidence or [], 'canonical_entity_id': None}


def check_private_scopes(records, domains):
    seen = {}
    for item in records.values():
        identity_, payload = item['identity'], item['payload']
        domain = identity_['domain']
        if domain not in PRIVATE:
            continue
        result = domains[domain]
        values = []
        for aliases in (('household_namespace', 'scope_namespace', 'namespace'), ('household_id', 'householdId'), ('user_id', 'userId')):
            claims = [payload[k] for k in aliases if k in payload and payload[k] is not None]
            value = claims[0] if claims and all(type(v) is type(claims[0]) and v == claims[0] for v in claims) else None
            values.append(identifier(value))
        item['scope'] = tuple(values) if all(values) else None
        if not item['scope']:
            result['missing_scope_fields'] += sum(v is None for v in values)
            continue
        native = identifier(payload.get('id', payload.get('source_id')))
        if native is None or identity_['record_id'].startswith('row:'):
            result['missing_scope_fields'] += 1
            continue
        scoped = (domain, *item['scope'], native)
        seen.setdefault(scoped, []).append(identity_)
    for keys in seen.values():
        if len(keys) > 1:
            domains[keys[0]['domain']]['duplicate_scoped_keys'] += len(keys)
    for domain in PRIVATE:
        row = domains[domain]
        if row['scanned_records']:
            row['scope'] = 'blocked' if row['missing_scope_fields'] or row['duplicate_scoped_keys'] else 'explicit_claims_only_access_isolation_unknown'


def resolve_edges(records, edges, domains, snapshot_id):
    supplier_index = {}
    for record in records.values():
        ident, payload = record['identity'], record['payload']
        native = identifier(payload.get('entity_id'))
        provider = payload.get('provider')
        if (ident['domain'] == 'suppliers' and native and isinstance(provider, str)
                and provider not in ('', 'unknown', 'retained') and provider == record['provider']
                and payload.get('type') in SUPPLIER_ENTITY_TYPES and record['hash_valid']):
            k = (provider, ident['source_key'], ident['source_version'], *native)
            supplier_index.setdefault(k, []).append(ident)
    output = []
    for edge in edges:
        owner = records.get(key_of(edge))
        contract = next((name for name, (d, kind, _, _) in CONTRACTS.items() if d == edge['domain'] and kind == edge['kind']), 'unsupported_relation')
        if edge['domain'] == 'suppliers' and edge['kind'] in SUPPLIER_KINDS:
            contract = 'supplier_entities'
        result = {'owner': owner['identity'] if owner else {k: edge[k] for k in ('domain', 'source_key', 'source_version', 'record_id')},
                  'relation_ordinal': edge['ordinal'], 'relation_kind': edge['kind'], 'reciprocal': 'not_applicable'}
        reason, candidates, key, native, reciprocal = None, [], None, identifier(edge['target_id']), None
        evidence = [{'source_record_identity': result['owner'], 'json_pointer': '/relations/' + str(edge['ordinal']) + '/target_id',
                     'asserted_value': edge['target_id'], 'mapping_rule_id': contract}]
        if not owner or not owner['hash_valid']:
            reason = 'owning_record_missing_or_hash_invalid'
        elif contract == 'unsupported_relation':
            reason = 'join_contract_unavailable'
        else:
            expected_domain = CONTRACTS[contract][2]
            reciprocal = CONTRACTS[contract][3]
            payload_links = owner['payload'].get('relations')
            if (not isinstance(payload_links, list) or not 0 <= edge['ordinal'] < len(payload_links)
                    or payload_links[edge['ordinal']] != edge['detail']
                    or edge['detail'].get('kind', 'related') != edge['kind']
                    or edge['detail'].get('target_domain') != edge['target_domain']
                    or (str(edge['detail']['target_id']) if edge['detail'].get('target_id') is not None else None) != edge['target_id']):
                reason = 'relation_payload_disagrees'
            elif edge['target_domain'] != expected_domain:
                reason = 'target_domain_contract_mismatch'
            elif native is None:
                reason = 'target_identifier_missing_or_unsupported_type'
            elif domains[expected_domain]['coverage'] != 'complete':
                reason = 'target_snapshot_coverage_incomplete'
            elif contract == 'supplier_entities':
                provider = owner['payload'].get('provider')
                subject = edge['detail'].get('subject_id')
                raw_native = identifier(edge['detail'].get('target_id'))
                if not isinstance(provider, str) or provider in ('', 'unknown', 'retained') or provider != owner['provider']:
                    reason = 'supplier_provider_namespace_unverified'
                elif subject is None or subject != owner['payload'].get('entity_id'):
                    reason = 'supplier_subject_claim_missing_or_conflicting'
                elif raw_native is None:
                    reason = 'target_identifier_missing_or_unsupported_type'
                else:
                    native = raw_native
                    key = lookup_key('suppliers', 'provider-native-supplier-entity-id/1', provider, edge['source_key'], edge['source_version'], native[0])
                    candidates = supplier_index.get((provider, edge['source_key'], edge['source_version'], *native), [])
            else:
                # This namespace identifies adapter occurrences, not native IDs.
                key = lookup_key(expected_domain, 'offmenu-staging-record-id/1', 'offmenu.recipe-adapter/1', edge['source_key'], edge['source_version'], native[0])
                target = records.get((expected_domain, edge['source_key'], edge['source_version'], native[0]))
                expected_kinds = {'recipe_mentions': ('ingredient_mention',), 'mention_recipe': ('recipe',), 'menu_entries': ('menu', 'menu_item')}
                owner_kinds = {'recipe_mentions': ('recipe',), 'mention_recipe': ('ingredient_mention',), 'menu_entries': ('menu', 'menu_item')}
                if owner['payload'].get('kind') not in owner_kinds[contract] or str(owner['payload'].get('id')) != edge['record_id']:
                    reason = 'owning_adapter_shape_unverified'
                elif target and (target['payload'].get('kind') not in expected_kinds[contract] or str(target['payload'].get('id')) != native[0]):
                    reason = 'target_adapter_shape_unverified'
                elif target and target['hash_valid']:
                    if contract == 'recipe_mentions' and target['payload'].get('recipe_id') != edge['record_id']:
                        reason = 'mention_recipe_claim_conflicting'
                    elif contract == 'mention_recipe' and owner['payload'].get('recipe_id') != native[0]:
                        reason = 'mention_recipe_claim_conflicting'
                    else:
                        candidates = [target['identity']]
        evidence[0]['asserted_namespace'] = key['identifier_namespace'] if key else None
        result.update(exact_resolution(key, candidates, snapshot_id=snapshot_id, contract=contract, reason=reason,
                                       value_type=native[1] if native else 'unsupported', evidence=evidence))
        result['identifier_role'] = 'source_native_identifier' if contract == 'supplier_entities' else 'staging_occurrence_identifier' if contract != 'unsupported_relation' else 'unknown'
        if result['disposition'] == 'missing' and key:
            versions = {s['source_version'] for s in domains[key['target_domain']]['selected_sources'] if s['source_key'] == key['source_key']}
            if versions and key['source_version'] not in versions:
                result['reason_code'] = 'target_source_version_mismatch'
            elif not versions:
                result['reason_code'] = 'target_source_namespace_not_selected'
        if edge['domain'] in PRIVATE:
            # No private link is accepted by v1. Still detect explicit attempted
            # joins to a known staging occurrence in a different scope.
            target = records.get((edge['target_domain'], edge['source_key'], edge['source_version'], edge['target_id']))
            claimed_scope = tuple(identifier(edge['detail'].get(k)) for k in ('household_namespace', 'household_id', 'user_id'))
            cross = (owner and target and owner.get('scope') and target.get('scope') and owner['scope'] != target['scope'])
            cross = cross or (owner and owner.get('scope') and all(claimed_scope) and claimed_scope != owner['scope'])
            if cross:
                domains[edge['domain']]['cross_scope_attempts'] += 1
                result['reason_code'] = 'cross_household_or_user_scope_attempt'
        output.append(result)
    # Raw reciprocal rows are insufficient: the reverse edge must itself have
    # passed payload/hash/shape/namespace checks and uniquely resolve to owner.
    validated = {(key_of(r['owner']), r['relation_kind'], key_of(r['targets'][0]))
                 for r in output if r['disposition'] == 'resolved'}
    for result in output:
        contract = result['join_contract_id']
        reverse_kind = CONTRACTS.get(contract, (None, None, None, None))[3]
        if reverse_kind and result['disposition'] == 'resolved':
            reverse = (key_of(result['targets'][0]), reverse_kind, key_of(result['owner']))
            result['reciprocal'] = 'matched' if reverse in validated else 'missing'
    return output


class ReadonlyNormalizationView:
    """Adapter only for validators' SELECTs, never NormalizationStore creation."""
    def __init__(self, db, budget):
        self.db, self.budget = db, budget

    def get(self, key):
        row = self.db.execute('SELECT body_json FROM artifacts WHERE cache_key=?', (key,)).fetchone()
        return self.budget.parse(row[0]) if row else None


def normalization_coverage(state, records, domains, budget, target_language):
    path = resolve_layout(state).normalization / 'normalized-sidecars.sqlite3'
    report = {'status': 'unknown', 'snapshot': None, 'orphan_or_stale_artifacts': 0,
              'invalid_artifacts': 0, 'matching_artifacts': 0,
              'target_language_status': 'specified' if target_language else 'unspecified',
              'diagnostics': []}
    before = database_identity(path)
    if before['main'] is None:
        report['status'] = 'absent'
        for domain in DOMAINS:
            domains[domain]['normalization'].update(status='absent', no_artifact=domains[domain]['scanned_records'],
                                                    gold_unknown=domains[domain]['scanned_records'])
        return report
    report['snapshot'] = {'before': before}
    db = None
    try:
        db = open_readonly(path, budget, quiescent=True)
        if db.execute("SELECT value FROM normalization_meta WHERE key='binding'").fetchone() != ('normalization_sidecar_only/1',):
            raise ReadinessError('unsupported_normalization_sidecar')
        from normalization_core import validate_artifact, validate_and_cache_actual_review, gold_readiness
        view = ReadonlyNormalizationView(db, budget)
        matches = {}
        scanned = 0
        for cache_key, raw in db.execute('SELECT cache_key,body_json FROM artifacts ORDER BY cache_key'):
            scanned += 1
            if scanned > budget.limits.max_records:
                raise ReadinessError('resource_budget_exhausted')
            artifact = budget.parse(raw)
            try:
                source = artifact['source']
                rec_key = key_of(source)
                current = records.get(rec_key)
                if not current or source != current['identity']:
                    report['orphan_or_stale_artifacts'] += 1
                    continue
                validate_artifact(artifact)
                if artifact['cache_key'] != cache_key:
                    raise ValueError('cache_key_mismatch')
                matches.setdefault(rec_key, []).append(artifact)
                report['matching_artifacts'] += 1
            except (ValueError, TypeError, KeyError, RecursionError):
                report['invalid_artifacts'] += 1
        for rec_key, record in records.items():
            budget.check()
            counters = domains[record['identity']['domain']]['normalization']
            artifacts = matches.get(rec_key, [])
            versions = {canonical(a['versions']) for a in artifacts}
            if not artifacts:
                counters['no_artifact'] += 1
                counters['gold_unknown'] += 1
                continue
            if len(versions) != 1:
                counters['ambiguous_versions'] += 1
                counters['gold_unknown'] += 1
                continue
            interpreted = [a for a in artifacts if a['pass'] == 'interpreted']
            if len(interpreted) > 1:
                counters['ambiguous_versions'] += 1
                counters['gold_unknown'] += 1
                continue
            if not interpreted:
                counters['rules_only'] += 1
                counters['review_pending'] += 1
                counters['gold_blocked'] += 1
                continue
            artifact = interpreted[0]
            try:
                parent_id = artifact['lineage']['parent_artifact_id']
                parent = view.get(parent_id.split(':', 1)[1])
                replay = validate_and_cache_actual_review(parent, artifact['review']['receipt'], store=view, cache_result=False)
                if replay != artifact:
                    raise ValueError('review_output_mismatch')
                if artifact['review']['status'] == 'rejected':
                    counters['review_rejected'] += 1
                elif artifact['normalization_status'] != 'validated':
                    counters['review_pending'] += 1
                else:
                    counters['validated_interpreted'] += 1
                if artifact['uncertainty'] or any(i['severity'] == 'error' for i in artifact['issues']):
                    counters['unresolved_error'] += 1
                if target_language:
                    gold = gold_readiness(artifact, target_language, store=view)
                    blockers = gold.get('blockers', [])
                    counters['gold_blocked'] += bool(blockers)
                    counters['translation_pending'] += any('translation' in x for x in blockers)
                else:
                    counters['gold_unknown'] += 1
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                counters['unresolved_error'] += 1
                counters['gold_unknown'] += 1
        report['status'] = 'observed' if not report['invalid_artifacts'] else 'incomplete'
        for domain in DOMAINS:
            domains[domain]['normalization']['status'] = report['status']
    except (OSError, sqlite3.Error, ReadinessError, ImportError) as exc:
        report['diagnostics'].append(str(exc) if isinstance(exc, ReadinessError) else 'normalization_read_or_validation_unavailable')
        report['status'] = 'incomplete'
        for domain in DOMAINS:
            domains[domain]['normalization']['status'] = 'incomplete'
    finally:
        if db:
            db.close()
        report['snapshot']['after'] = database_identity(path)
        if report['snapshot']['after'] != before:
            report['status'] = 'unstable'
            for domain in DOMAINS:
                domains[domain]['normalization']['status'] = 'unstable'
    return report


def build_report(state_dir, *, limits=None, target_language=None):
    """Inspect exactly eight existing stores and retained terminal metadata once.

    Returns private detail (do not publish). Invalid/unavailable inputs produce
    unknown/incomplete evidence, not invented zeros or a readiness approval.
    This does not write reports, staging, private inputs, or execution settings.
    """
    state = safe_path(resolve_layout(state_dir).ingest)
    limits = limits or Limits()
    budget = Budget(limits)
    if target_language is not None and (not isinstance(target_language, str) or not target_language or len(target_language) > 64):
        raise ReadinessError('invalid_target_language')
    report = {'schema': SCHEMA, 'mapping_rule_version': RULE_VERSION,
              'status': 'blocked', 'evidence_status': 'incomplete',
              'binding': BINDING, 'app_binding_status': 'app_binding_unknown',
              'fetch_status': 'disabled', 'canonical_entity_registry': 'unavailable',
              'fetch_status_scope': 'this_reporter_has_no_acquisition_capability_or_authorization_gate',
              'resource_budget': asdict(limits), 'snapshot': {'status': 'unknown'},
              'domains': {d: initial_domain() for d in DOMAINS},
              'relation_resolutions': [], 'diagnostics': [],
              'observation_boundary': 'retained_staging_only_no_Foo_execution_no_raw_source_custody_or_application_provisioning_claim'}
    # Bind rule implementation and any pure validation implementation used here.
    code_files = ('relational_readiness.py', 'ingest_api.py', 'ingest_store.py',
                  'ingest_recipes.py', 'ingest_suppliers.py', 'normalization_api.py',
                  'normalization_core.py', 'normalization_domains.py', 'normalize_recipes.py', 'normalization-rules.json')
    code_hashes = {}
    for name in code_files:
        path = safe_path(Path(__file__).parent / name)
        if file_identity(path):
            code_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report['code_sha256'] = code_hashes
    try:
        receipt, catalog, metadata = receipt_inputs(state, budget)
        report['terminal_metadata'] = metadata
    except (OSError, ReadinessError) as exc:
        receipt, catalog = {}, {'sources': []}
        report['terminal_metadata'] = {'status': 'unknown'}
        report['diagnostics'].append(str(exc) if isinstance(exc, ReadinessError) else 'terminal_metadata_unreadable')
    records, edges, connections = {}, [], {}
    before, lock_states = {}, {}
    try:
        # Observe locks only. Even a momentary shared lock could reject an
        # ingestion writer's nonblocking exclusive flock; never acquire one.
        for domain in DOMAINS:
            try:
                lock_states[domain] = observe_writer_lock(store_path(state, domain))
            except (OSError, ReadinessError):
                lock_states[domain] = 'unknown_unreadable_writer_lock'
        for domain in DOMAINS:
            result = report['domains'][domain]
            path = store_path(state, domain)
            try:
                before[domain] = database_identity(path)
                result['snapshot_before'] = before[domain]
                result['writer_lock'] = lock_states[domain]
                if lock_states[domain] == 'writer_active':
                    raise ReadinessError('writer_active_snapshot_not_inspected')
                if before[domain]['wal'] is not None:
                    raise ReadinessError('wal_present_read_deferred_without_copy_or_source_mutation')
                if (report['terminal_metadata']['status'] != 'bound'
                        or receipt.get('output_identities', {}).get(domain) != before[domain]
                        or lock_states[domain] != 'no_writer_observed'):
                    raise ReadinessError('quiescent_terminal_snapshot_not_established')
                db = open_readonly(path, budget, quiescent=True)
                result['sqlite_data_version_before'] = db.execute('PRAGMA data_version').fetchone()[0]
                connections[domain] = db
                scan_domain(domain, db, receipt, catalog, budget, result, records, edges)
                if receipt.get('output_identities', {}).get(domain) != before[domain]:
                    result['diagnostics'].append('terminal_file_identity_mismatch')
                    result['coverage'] = 'incomplete'
            except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError) as exc:
                result['coverage'] = 'incomplete'
                result['diagnostics'].append(str(exc) if isinstance(exc, ReadinessError) else 'staging_read_failed_or_budget_exhausted')
        check_private_scopes(records, report['domains'])
        try:
            report['normalization'] = normalization_coverage(state, records, report['domains'], budget, target_language)
        except (OSError, ReadinessError):
            report['normalization'] = {'status': 'incomplete', 'diagnostics': ['normalization_input_unreadable']}

        after = {}
        for domain in DOMAINS:
            try:
                after[domain] = database_identity(store_path(state, domain))
            except (OSError, ReadinessError):
                after[domain] = None
            try:
                report['domains'][domain]['writer_lock_after'] = observe_writer_lock(store_path(state, domain))
            except (OSError, ReadinessError):
                report['domains'][domain]['writer_lock_after'] = 'unknown_unreadable_writer_lock'
            if domain in connections:
                connections[domain].set_progress_handler(None, 0)
                report['domains'][domain]['sqlite_data_version_after'] = connections[domain].execute('PRAGMA data_version').fetchone()[0]
            report['domains'][domain]['snapshot_after'] = after[domain]
            if after[domain] != before.get(domain):
                report['domains'][domain]['coverage'] = 'incomplete'
                report['domains'][domain]['diagnostics'].append('staging_identity_changed_during_report')
        metadata_after = {}
        for name in report['terminal_metadata'].get('before', {}):
            try:
                metadata_after[name] = file_identity(state / name)
            except (OSError, ReadinessError):
                metadata_after[name] = None
        report['terminal_metadata']['after'] = metadata_after
        after_code_hashes = {}
        for name in code_hashes:
            try:
                after_code_hashes[name] = hashlib.sha256(safe_path(Path(__file__).parent / name).read_bytes()).hexdigest()
            except (OSError, ReadinessError):
                after_code_hashes[name] = None
        report['code_unchanged_during_report'] = after_code_hashes == code_hashes
        stable_files = (before == after and metadata_after == report['terminal_metadata'].get('before')
                        and report['code_unchanged_during_report'])
        stable = (stable_files and report['terminal_metadata']['status'] == 'bound'
                  and all(v == 'no_writer_observed' for v in lock_states.values())
                  and all(r.get('writer_lock_after') == 'no_writer_observed' for r in report['domains'].values())
                  and all(before.get(d) == receipt.get('output_identities', {}).get(d) for d in DOMAINS)
                  and all(v.get('wal') is None for v in before.values()))
        snapshot_material = {'databases': before, 'terminal_metadata': report['terminal_metadata'].get('metadata_sha256'),
                             'selected_sources': {d: r['selected_sources'] for d, r in report['domains'].items()},
                             'code_sha256': code_hashes, 'mapping_rule_version': RULE_VERSION}
        snapshot_id = digest(snapshot_material)
        report['snapshot'] = {'status': 'stable_terminal_observation' if stable else 'unstable_or_unknown',
                              'snapshot_id': snapshot_id, 'material': snapshot_material,
                              'coordination': 'terminal_receipt_output_identities_and_before_after_observation',
                              'atomic_cross_database_snapshot': 'not_established',
                              'sqlite_data_version_scope': 'immutable_read_only_not_a_live_writer_detector',
                              'uncooperative_external_writer_exclusion': 'not_proven'}
        if not stable:
            for result in report['domains'].values():
                result['coverage'] = 'incomplete'
        report['relation_resolutions'] = resolve_edges(records, edges, report['domains'], snapshot_id)
        report['evidence_status'] = 'complete_for_supported_staging_contracts' if stable and all(r['coverage'] == 'complete' for r in report['domains'].values()) else 'incomplete'
    finally:
        for db in connections.values():
            db.close()
    # Hash raw-record identity, never preserve payloads in the output report.
    report['observed_record_identity_sha256'] = digest(sorted((tuple(r['identity'][k] for k in ('domain', 'source_key', 'source_version', 'record_id', 'content_sha256')) for r in records.values())))
    report['counts'] = {'scanned_records': len(records), 'scanned_relations': len(edges),
                        **{s: sum(r['disposition'] == s for r in report['relation_resolutions']) for s in DISPOSITIONS},
                        'reciprocal_mismatches': sum(r['reciprocal'] == 'missing' for r in report['relation_resolutions'])}
    report['contract_counts'] = {c: {'edges': sum(r['join_contract_id'] == c for r in report['relation_resolutions']),
        **{s: sum(r['join_contract_id'] == c and r['disposition'] == s for r in report['relation_resolutions']) for s in DISPOSITIONS}}
        for c in (*CONTRACTS, 'unsupported_relation')}
    report['remaining_app_prerequisites'] = ['configured_database_identity_and_schema_evidence',
        'application_join_adapters_or_views', 'read_only_application_query_results_and_expected_cardinalities',
        'source_evidence_and_rights_coverage', 'private_access_isolation_evidence']
    return report


def sanitized_summary(report):
    """Positive whitelist: no identifiers, paths, relation labels or source data.

    Source-supplied statuses cannot become arbitrary strings in the shareable
    return. Counts are observations; coverage states determine their completeness.
    """
    def count(value):
        return value if type(value) is int and value >= 0 else None
    def status(value, allowed):
        return value if isinstance(value, str) and value in allowed else 'unknown'
    result = {'schema': 'offmenu.retained-relational-summary/1', 'status': 'blocked',
              'binding_status': 'staging_not_application_bound', 'app_binding_status': 'app_binding_unknown',
              'fetch_status': 'disabled', 'snapshot_status': status(report.get('snapshot', {}).get('status'), ('stable_terminal_observation', 'unstable_or_unknown')),
              'evidence_status': status(report.get('evidence_status'), ('complete_for_supported_staging_contracts', 'incomplete')),
              'counts': {}, 'contract_counts': {}, 'domains': {}}
    for key in ('scanned_records', 'scanned_relations', *DISPOSITIONS, 'reciprocal_mismatches'):
        result['counts'][key] = count(report.get('counts', {}).get(key))
    for contract in (*CONTRACTS, 'unsupported_relation'):
        result['contract_counts'][contract] = {k: count(report.get('contract_counts', {}).get(contract, {}).get(k)) for k in ('edges', *DISPOSITIONS)}
    for domain in DOMAINS:
        src = report.get('domains', {}).get(domain, {})
        dest = {'status': status(src.get('status'), ('observed', 'schema_only_awaiting_user_input', 'schema_only_app_managed')),
                'coverage_status': status(src.get('coverage'), ('complete', 'incomplete')),
                'integrity_status': status(src.get('integrity'), ('ok', 'failed')),
                'foreign_key_status': status(src.get('foreign_keys'), ('ok', 'failed')),
                'source_selection_status': status(src.get('source_selection'), ('exact',)),
                'scope_status': status(src.get('scope'), ('not_exercised_no_input', 'blocked', 'explicit_claims_only_access_isolation_unknown')),
                'adapter_status': 'unknown'}
        for key in ('selected_records', 'scanned_records', 'historical_records', 'reference_records', 'relations', 'scanned_relations',
                    'payload_hash_mismatches', 'missing_scope_fields', 'duplicate_scoped_keys', 'cross_scope_attempts'):
            dest[key] = count(src.get(key))
        dest['stored_records'] = count(src.get('table_counts', {}).get('records'))
        dest['normalization'] = {'status': status(src.get('normalization', {}).get('status'), ('absent', 'observed', 'incomplete', 'unstable')),
                                 **{k: count(src.get('normalization', {}).get(k)) for k in NORM_COUNTS}}
        result['domains'][domain] = dest
    return result


def write_reports(output_dir, report):
    """Write only new, mode-0600 report artifacts into a private directory.

    O_EXCL prevents overwriting source files or previous evidence. A caller may
    reuse an unchanged report; changed observations require a different directory.
    """
    directory = safe_path(output_dir)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise ReadinessError('report_directory_must_be_private')
    paths = []
    for name, value in (('retained-relational-readiness.private.json', report),
                        ('retained-relational-readiness.summary.json', sanitized_summary(report))):
        path = safe_path(directory / name)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(canonical(value) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        paths.append(path)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--target-language', default=None)
    parser.add_argument('--max-seconds', type=float, default=120)
    parser.add_argument('--max-records', type=int, default=200000)
    parser.add_argument('--max-relations', type=int, default=1000000)
    args = parser.parse_args(argv)
    try:
        report = build_report(args.state_dir, limits=Limits(max_seconds=args.max_seconds, max_records=args.max_records, max_relations=args.max_relations), target_language=args.target_language)
        write_reports(args.output_dir, report)
        print(canonical(sanitized_summary(report)))
        # This exit code is evidence completeness only, never FETCH permission.
        return 0 if report['evidence_status'] == 'complete_for_supported_staging_contracts' else 2
    except (OSError, ReadinessError, sqlite3.Error):
        print(canonical({'status': 'report_unavailable', 'app_binding_status': 'app_binding_unknown', 'fetch_status': 'disabled'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
