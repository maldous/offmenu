"""Offline, additive relational targets over an explicitly selected ingest snapshot.

No app database, original file, native product store, network, name matcher or
review service is opened for writing. Materialization is local/private, bounded,
resumable and source-identity preserving. Exact record joins are not food identity
equivalence, semantic review, rights clearance, translation or gold acceptance.
"""
from __future__ import annotations
from runner_paths import resolve_layout
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import re
import sqlite3
import stat
import time
import uuid

from ingest_api import DOMAINS

SCHEMA = 'offmenu-relational-targets/1'
BINDING = 'versioned_derived_not_app_bound'
PRIVATE = ('user_profiles', 'inventory')
DOMAIN_STATES = ('materialized', 'partial', 'empty', 'schema_only', 'unavailable')
BLOCKERS = frozenset(('source_writer_active', 'source_lock_missing', 'source_wal_present',
    'source_journal_present', 'source_changed', 'source_selection_missing',
    'source_database_unavailable', 'source_not_owned', 'resource_budget',
    'catalog_incomplete', 'source_partial', 'untyped_records', 'unresolved_relations',
    'app_binding_deferred', 'payload_hash_mismatch', 'unsafe_path',
    'derived_writer_active', 'derived_target_invalid', 'relational_target_error', 'disk_reserve'))
SAME_SOURCE_KINDS = {
    'has_ingredient_mention': ('recipes', 'ingredients'),
    'ingredient_of': ('ingredients', 'recipes'),
    'contains_menu_entry': ('recipes', 'recipes'),
    'item_of': ('recipes', 'recipes'), 'section_of': ('recipes', 'recipes'),
    'has_source_composition': ('recipes', 'recipes'),
    'ingredient_of_dish': ('ingredients', 'recipes'),
    'ingredient_of_menu_item': ('ingredients', 'recipes'),
    'observation_of': (None, None),
    'cites': (None, 'citations'), 'cites_record': ('citations', None),
}
MENU_KINDS = frozenset(('menu', 'menu_item', 'menu_section', 'dish_composition',
    'composition_reference', 'menu_observation', 'dish_observation', 'menu_entry',
    'restaurant_menu', 'technical_sheet', 'dish_composition_observation'))
OFF_PROVIDERS = ('off', 'openfoodfacts', 'open_food_facts', 'open-food-facts')
FDC_PROVIDERS = ('usda', 'fdc', 'usda_fdc', 'usda-files')
ENTITY_NAMESPACES = {
    'off.product_code': ('barcodes','barcode_products',OFF_PROVIDERS),
    'usda.fdc_id': ('ingredients','ingredient_entities',FDC_PROVIDERS),
    'supplier.entity_id': ('suppliers','supplier_entities',None),
}
SCOPED_TARGET_TABLES = {
    'has_ingredient_mention':'ingredient_mentions', 'ingredient_of':'recipe_headers',
    'contains_menu_entry':'menu_entries', 'item_of':'menu_entries',
    'section_of':'menu_entries', 'has_source_composition':'menu_entries',
    'ingredient_of_dish':'menu_entries', 'ingredient_of_menu_item':'menu_entries',
}
DIETARY_KINDS = frozenset(('nutrientprofile','foodcompositionobservation','dietflagassertion',
    'dietarytype','allergenmapping','dietaryreference','nutrientdefinition','metricbasisdefinition','dietaryguideline',
    'source_assertion','common_dietary_packet','guideline_reference_packet',
    'nutrition_reference','source_diet_flag','usda_nutrient_observation',
    'nutrient_observation','nutrient_definition','source_allergen_mapping',
    'diet_flag_definition','provider_composition_table'))


class TargetError(ValueError):
    pass


class _Limit(Exception):
    def __init__(self, reason='resource_budget'):
        self.reason = reason
        super().__init__(reason)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _write_manifest(path, value):
    temporary = path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    fd = os.open(temporary, os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(_json(value)+'\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def _safe(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise TargetError('unsafe_path')
    return path


def _identity(path):
    path = _safe(path)
    try:
        s = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(s.st_mode):
        raise TargetError('unsafe_path')
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def _store(state, domain):
    return resolve_layout(state).domain_path(domain)


def _lexical(value):
    # Booleans/floats cannot become native identifiers. Type is part of equality.
    if isinstance(value, str) and value:
        return 'string', value
    if type(value) is int:
        return 'integer', str(value)
    return None


def _scope(payload):
    values = [payload.get('household_namespace', payload.get('scope_namespace', payload.get('namespace'))),
              payload.get('household_id'), payload.get('user_id')]
    return values if all(isinstance(x, str) and x for x in values) else None


def _claim(db, uid, row, namespace, value, pointer, contract):
    admission = ENTITY_NAMESPACES.get(namespace)
    if not admission:
        return
    domain, table, providers = admission
    # Identifier eligibility and typed-entity admission are one invariant, not
    # independent field heuristics. Assertion/metadata rows cannot supply keys.
    if row['domain'] != domain or (providers is not None and row['provider'] not in providers) or not db.execute('SELECT 1 FROM '+table+' WHERE record_uid=?',(uid,)).fetchone():
        return
    lexical = _lexical(value)
    if lexical and row['provider'] not in (None, '', 'unknown', 'retained'):
        db.execute('INSERT OR IGNORE INTO identifier_claims VALUES(?,?,?,?,?,?,?,?,?)',
            (uid, namespace, row['provider'], row['source_key'], row['source_version'],
             *lexical, pointer, contract))


def _edge(db, uid, ordinal, edge):
    db.execute('INSERT INTO relation_claims VALUES(?,?,?,?,?,?)',
        (uid, ordinal, str(edge.get('kind', 'related')), edge.get('target_domain'),
         _json(edge.get('target_id')), _json(edge)))
    db.execute('INSERT INTO relation_resolutions VALUES(?,?,?,?,?,?,?)',
        (uid, ordinal, 'unassigned', 'deferred', 'snapshot_coverage_incomplete', 0, '{}'))


def _project(db, uid, row, p):
    """Typed tables carry observed values; a source record may remain untyped."""
    domain, kind = row['domain'], p.get('kind', p.get('record_type', p.get('type')))
    value = lambda key: _json(p.get(key))
    typed, synthetic = False, []
    if domain == 'recipes' and kind == 'recipe':
        db.execute('INSERT INTO recipe_headers VALUES(?,?,?,?,?)',
            (uid, value('title'), value('language'), value('yield'), value('steps')))
        typed = True
    elif domain == 'recipes' and kind in MENU_KINDS:
        db.execute('INSERT INTO menu_entries VALUES(?,?,?,?,?)',
            (uid, kind, _json(p.get('title', p.get('name'))), value('source_scope'), value('source_native_id')))
        typed = True
    elif domain == 'ingredients':
        if kind in ('ingredient_mention', 'ingredient_label_mention', 'ingredient_source_assertion', 'ingredient_observation', 'ingredient_source_observation'):
            db.execute('INSERT INTO ingredient_mentions VALUES(?,?,?,?,?,?,?)',
                (uid, p.get('recipe_id'), p.get('ordinal') if type(p.get('ordinal')) is int else None,
                 value('raw_text'), value('quantity'), value('unit'), 'source_mention_not_canonical_entity'))
            typed = True
        elif kind in ('ingredient_source_entity', 'composition_reference'):
            db.execute('INSERT INTO ingredient_entities VALUES(?,?,?,?)',
                (uid, value('source_native_id'), value('name'), 'source_entity_not_canonical'))
            typed = True
        raw = p.get('raw_source')
        if kind == 'ingredient_source_entity' and typed and row['provider'] in FDC_PROVIDERS and isinstance(raw, dict):
            for field in ('fdcId', 'fdc_id'):
                if field in raw and _lexical(raw[field]) == _lexical(p.get('source_native_id')):
                    _claim(db, uid, row, 'usda.fdc_id', raw[field], '/raw_source/' + field, 'fdc-field/1')
    elif domain == 'barcodes':
        if kind == 'readonly_source_reference':
            db.execute('INSERT INTO external_store_references VALUES(?,?,?)',
                (uid, _json(p), 'native_product_lookup_deferred'))
            typed = True
        elif kind in (None,'','product','food_product','FoodProduct') and row['provider'] in OFF_PROVIDERS and isinstance(p.get('code'), str) and p['code'] and p['code'].isascii() and p['code'].isdigit():
            db.execute('INSERT INTO barcode_products VALUES(?,?,?)',
                (uid, value('code'), 'provider_code_claim_not_issuer_verified'))
            _claim(db, uid, row, 'off.product_code', p['code'], '/code', 'off-code-field/1')
            typed = True
    elif domain == 'dietary':
        if p.get('record_type') in DIETARY_KINDS and isinstance(p.get('source_fields'), dict):
            facts = p['source_fields']
            db.execute('INSERT INTO dietary_assertions VALUES(?,?,?,?,?)',
                (uid, kind, value('source_record_id'), _json(facts), value('source_numeric_lexemes')))
            typed = True
            raw = facts.get('data') if isinstance(facts.get('data'), dict) else facts
            native = next((raw[k] for k in ('fdcId', 'fdc_id') if k in raw), None)
            synthetic.append({'kind': 'dietary_subject', 'target_domain': 'ingredients',
                              'source_native_food_id': native})
    elif domain == 'suppliers' and kind in ('organization','supplier_entity','place','food_place') and _lexical(p.get('entity_id')):
        db.execute('INSERT INTO supplier_entities VALUES(?,?,?,?)',
            (uid, value('entity_id'), kind, value('name')))
        _claim(db, uid, row, 'supplier.entity_id', p['entity_id'], '/entity_id', 'supplier-native-scoped/1')
        typed = True
    elif domain == 'suppliers' and kind in ('company_ownership','price_observation'):
        db.execute('INSERT INTO supplier_assertions VALUES(?,?,?,?)', (uid,value('entity_id'),kind,_json(p)))
        if kind == 'company_ownership':
            synthetic.append({'kind':'assertion_subject','target_domain':'suppliers','target_id':p.get('entity_id')})
        typed = True
    elif domain == 'citations':
        db.execute('INSERT INTO evidence_citations VALUES(?,?,?)',
            (uid, _json(p), 'explicit_edges_only'))
        if not any(e.get('kind') == 'cites_record' for e in p.get('relations', []) if isinstance(e, dict)):
            synthetic.append({'kind': 'citation_attachment', 'target_domain': None})
        typed = True
    elif domain in PRIVATE:
        scope = _scope(p)
        status = 'explicit_scope' if scope else 'scope_missing'
        if domain == 'user_profiles':
            db.execute('INSERT INTO household_profiles VALUES(?,?,?,?)', (uid, _json(scope), _json(p), status))
        else:
            db.execute('INSERT INTO inventory_lots VALUES(?,?,?,?,?,?)',
                (uid, _json(scope), value('id'), value('quantity'), value('unit'), status))
            synthetic.append({'kind': 'inventory_profile', 'target_domain': 'user_profiles', 'scope': scope})
            if p.get('barcode') is not None or p.get('product_id') is not None:
                synthetic.append({'kind': 'inventory_product', 'target_domain': 'barcodes',
                                  'target_id': p.get('barcode', p.get('product_id'))})
        typed = True
    edges = p.get('relations', [])
    if not isinstance(edges, list) or len(edges) > 100000 or any(not isinstance(e, dict) for e in edges):
        raise TargetError('derived_target_invalid')
    for ordinal, edge in enumerate(edges + synthetic):
        _edge(db, uid, ordinal, edge)
    return typed


def _resolve(db, owner, edge):
    kind, domain, target = edge.get('kind'), edge.get('target_domain'), edge.get('target_id')
    lookup = {'target_domain': domain, 'target_id': target}
    if kind in SAME_SOURCE_KINDS:
        source_domain, target_domain = SAME_SOURCE_KINDS[kind]
        if (source_domain is not None and owner['domain'] != source_domain) or (target_domain is not None and domain != target_domain) or domain not in DOMAINS:
            return 'scoped-record-id/1', 'relation_domain_mismatch', [], lookup
        if kind == 'observation_of' and (owner['domain'] not in ('recipes','ingredients') or domain != owner['domain']):
            return 'scoped-record-id/1', 'relation_domain_mismatch', [], lookup
        lookup.update(source_key=owner['source_key'], source_version=owner['source_version'])
        table = SCOPED_TARGET_TABLES.get(kind)
        if kind == 'observation_of':
            table = 'ingredient_entities' if domain == 'ingredients' else 'menu_entries'
        typed_clause = ' AND uid IN (SELECT record_uid FROM '+table+')' if table else ''
        candidates = list(db.execute('SELECT uid FROM source_records WHERE domain=? AND source_key=? AND source_version=? AND record_id=?'+typed_clause,
            (domain, owner['source_key'], owner['source_version'], str(target)))) if target is not None else []
        # A private record can never bypass household scope via a generic edge.
        if owner['domain'] in PRIVATE or domain in PRIVATE:
            candidates = [r for r in candidates if db.execute('SELECT household_scope_json FROM source_records WHERE uid=?', r).fetchone()[0] == owner['household_scope_json'] and owner['household_scope_json'] != 'null']
        return 'scoped-record-id/1', None, candidates, lookup
    if edge.get('target_identity_kind') == 'acquired_scoped_id':
        family, scope = edge.get('target_adapter'), edge.get('target_scope')
        lookup.update(family=family, scope=scope, native_id=edge.get('target_native_id'))
        if (edge.get('target_source_policy') != 'selected_family' or
                family not in ('fr_cnous_menus','fr_begles_menus','fr_toulouse_menus') or
                family != owner['source_family'] or (scope is None and family != 'fr_toulouse_menus') or
                domain not in ('recipes', 'ingredients') or edge.get('target_native_id') is None):
            return 'acquired-scoped-id/1', 'acquired_scope_unverified', [], lookup
        table = 'ingredient_entities' if domain == 'ingredients' else 'menu_entries'
        candidates = list(db.execute('SELECT uid FROM source_records WHERE domain=? AND source_family=? AND source_scope_json=? AND source_native_id_json=? AND record_id=? AND uid IN (SELECT record_uid FROM '+table+')',
            (domain, family, _json(scope), _json(edge['target_native_id']), str(target))))
        return 'acquired-scoped-id/1', None, candidates, lookup
    if owner['domain'] == 'suppliers' and domain == 'suppliers':
        lexical = _lexical(target)
        lookup.update(namespace='supplier.entity_id', provider=owner['provider'], source_key=owner['source_key'], source_version=owner['source_version'], value=lexical)
        candidates = list(db.execute('SELECT record_uid FROM identifier_claims WHERE namespace=? AND provider=? AND source_key=? AND source_version=? AND value_type=? AND lexical_value=?',
            ('supplier.entity_id', owner['provider'], owner['source_key'], owner['source_version'], *lexical))) if lexical else []
        return 'supplier-native-scoped/1', None, candidates, lookup
    if kind in ('ingredient_of_product', 'dietary_subject'):
        product = kind == 'ingredient_of_product'
        native = edge.get('source_native_product_id' if product else 'source_native_food_id')
        lexical = _lexical(native)
        namespace = 'off.product_code' if product else 'usda.fdc_id'
        providers = OFF_PROVIDERS if product else FDC_PROVIDERS
        lookup.update(namespace=namespace, provider=owner['provider'], physical_origin=owner['physical_origin'], value=lexical)
        if owner['provider'] not in providers or not lexical or not owner['physical_origin']:
            return 'same-asset-native-id/1', 'native_namespace_unverified', [], lookup
        candidates = list(db.execute('SELECT DISTINCT c.record_uid FROM identifier_claims c JOIN source_records r ON r.uid=c.record_uid WHERE r.domain=? AND c.namespace=? AND c.provider=? AND c.value_type=? AND c.lexical_value=? AND r.physical_origin=?',
            (domain, namespace, owner['provider'], *lexical, owner['physical_origin'])))
        if product and not candidates and db.execute('SELECT 1 FROM external_store_references x JOIN source_records r ON r.uid=x.record_uid WHERE r.provider=? AND r.physical_origin=? LIMIT 1', (owner['provider'],owner['physical_origin'])).fetchone():
            return 'same-asset-native-id/1', 'retained_store_lookup_adapter_required', [], lookup
        return 'same-asset-native-id/1', None, candidates, lookup
    if kind == 'inventory_profile':
        scope = edge.get('scope')
        lookup['household_scope'] = scope
        if not scope:
            return 'private-profile-scope/1', 'private_scope_missing', [], lookup
        candidates = list(db.execute("SELECT uid FROM source_records WHERE domain='user_profiles' AND household_scope_json=?", (_json(scope),)))
        return 'private-profile-scope/1', None, candidates, lookup
    return 'unassigned', 'explicit_mapping_required', [], lookup


def sanitize_relational_summary(value):
    value = value if isinstance(value, dict) else {}
    integer = lambda x: x if type(x) is int and 0 <= x <= 2**63-1 else 0
    mapping = lambda x: x if isinstance(x, dict) else {}
    blockers = value.get('blockers', [])
    blockers = blockers if isinstance(blockers, list) else []
    result = {'schema': SCHEMA, 'binding': BINDING, 'app_binding': 'deferred',
        'status': value.get('status') if value.get('status') in ('complete', 'partial', 'blocked', 'reused') else 'blocked',
        'domains': {}, 'relations': {},
        'schema_only_private_domains': min(2, integer(value.get('schema_only_private_domains'))),
        'blockers': sorted(set(x for x in blockers if isinstance(x, str)) & BLOCKERS)}
    for domain in DOMAINS:
        row = mapping(mapping(value.get('domains')).get(domain))
        result['domains'][domain] = {'status': row.get('status') if row.get('status') in DOMAIN_STATES else 'unavailable',
            **{k: integer(row.get(k)) for k in ('records', 'typed_records', 'untyped_records')}}
    for key in ('total', 'resolved', 'missing', 'ambiguous', 'deferred', 'reciprocal_mismatches'):
        result['relations'][key] = integer(mapping(value.get('relations')).get(key))
    return result


def relational_outputs_available(state_dir):
    """Metadata-only completion-cache guard; missing derived targets require work.

    The coordinator owns the top-level private receipt. Identity checks do not
    reread source records and are not a replacement for semantic/integrity review.
    Empty WAL inode churn is immaterial; nonempty WAL or active writers defer.
    """
    try:
        state = _safe(resolve_layout(state_dir).ingest)
        def read(path):
            path = _safe(path)
            if _identity(path) is None: raise TargetError('derived_target_invalid')
            with path.open('rb') as stream: raw = stream.read(16*1024*1024+1)
            if len(raw) > 16*1024*1024: raise TargetError('derived_target_invalid')
            result = json.loads(raw)
            if not isinstance(result,dict): raise TargetError('derived_target_invalid')
            return result
        receipt = read(state/'relational-targets.private.json')
        snapshot = receipt.get('snapshot')
        if not isinstance(snapshot,str) or not re.fullmatch('[a-f0-9]{64}',snapshot): return False
        root = _safe(resolve_layout(state).household/'relational-targets'/'v1')
        target = _safe(root/(snapshot+'.sqlite3'))
        persisted = read(root/(snapshot+'.manifest.json'))
        for value in (receipt,persisted):
            if (value.get('schema') != SCHEMA or value.get('binding') != BINDING or
                    value.get('snapshot') != snapshot or value.get('path') != str(target) or
                    value.get('status') not in ('complete','reused') or value.get('write_in_progress') is not False or
                    value.get('copy_complete') is not True or value.get('resolve_complete') is not True or
                    value.get('output_identity') != _identity(target)):
                return False
        for key in ('input_identities','selected_sources','code_sha256','mapping_sha256'):
            if receipt.get(key) != persisted.get(key): return False
        mapping = Path(__file__).with_name('relational-target-mapping.json').read_bytes()
        code_hash = hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('relational-targets.schema.sql').read_bytes()+mapping).hexdigest()
        if receipt.get('code_sha256') != code_hash or receipt.get('mapping_sha256') != hashlib.sha256(mapping).hexdigest(): return False
        expected = receipt.get('input_identities')
        if not isinstance(expected,dict) or set(expected) != set(DOMAINS): return False
        with contextlib.ExitStack() as stack:
            for domain in DOMAINS:
                path = _safe(_store(state,domain))
                if _identity(path) != expected[domain]: return False
                if expected[domain] is None: continue
                lock = path.with_suffix('.writer.lock')
                if _identity(lock) is None: return False
                fd = os.open(lock,os.O_RDONLY|os.O_NOFOLLOW); stack.callback(os.close,fd)
                fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
                wal = _identity(str(path)+'-wal')
                if wal is not None and wal[2] != 0: return False
                if _identity(str(path)+'-journal') is not None: return False
            return all(_identity(_store(state,d)) == expected[d] for d in DOMAINS)
    except (OSError,ValueError,TypeError,sqlite3.Error):
        return False


def _summary(db, complete, blockers):
    blockers = set(blockers)
    domains = {}
    for row in db.execute('SELECT * FROM domains'):
        count = row['records']
        domains[row['domain']] = dict(status=row['status'], records=count, typed_records=row['typed_records'], untyped_records=count-row['typed_records'])
    relations = dict(total=db.execute('SELECT COUNT(*) FROM relation_claims').fetchone()[0])
    relations.update(dict(db.execute('SELECT disposition,COUNT(*) FROM relation_resolutions GROUP BY disposition')))
    relations['reciprocal_mismatches'] = db.execute("SELECT COUNT(*) FROM resolved_links l WHERE ((l.kind='has_ingredient_mention' AND EXISTS(SELECT 1 FROM recipe_headers h WHERE h.record_uid=l.owner_uid)) OR (l.kind='ingredient_of' AND EXISTS(SELECT 1 FROM recipe_headers h WHERE h.record_uid=l.target_uid))) AND NOT EXISTS (SELECT 1 FROM resolved_links b WHERE b.owner_uid=l.target_uid AND b.target_uid=l.owner_uid AND b.kind=CASE l.kind WHEN 'has_ingredient_mention' THEN 'ingredient_of' ELSE 'has_ingredient_mention' END)").fetchone()[0]
    if any(d['untyped_records'] for d in domains.values()): blockers.add('untyped_records')
    if any(relations.get(k, 0) for k in ('missing', 'ambiguous', 'deferred', 'reciprocal_mismatches')): blockers.add('unresolved_relations')
    return sanitize_relational_summary({'status': 'complete' if complete else 'partial', 'domains': domains,
        'relations': relations, 'blockers': sorted(blockers | {'app_binding_deferred'}),
        'schema_only_private_domains': sum(domains[d]['status'] == 'schema_only' for d in PRIVATE)})


def materialize_relational_targets(state_dir, selections, *, catalog_complete=True,
                                  max_records=2000000, max_seconds=120, max_record_bytes=16777216,
                                  reserve_bytes=2*1024**3, progress_callback=None,
                                  progress_interval=60):
    """Return {summary, manifest}; selections must name exact stored source versions.

    Run only after the coordinating ingest has closed every DomainStore. All
    existing writer locks are held shared, all source DBs must be no-WAL/no-journal,
    (or only a pinned zero-byte WAL), and identities are verified unchanged
    before publishing. Selected incomplete
    sources remain incomplete even if every currently retained row is indexed.
    Repeated identical snapshots reuse completed targets; bounded partial targets
    resume after the last exact primary key, without rereading completed records.
    """
    blockers = set()
    try:
        return _materialize(state_dir, selections, catalog_complete, max_records, max_seconds, max_record_bytes,
                            reserve_bytes, progress_callback, progress_interval, blockers)
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        code = str(exc) if isinstance(exc, TargetError) and str(exc) in BLOCKERS else 'relational_target_error'
        status = 'partial' if code == 'disk_reserve' else 'blocked'
        if code == 'disk_reserve': blockers.add('resource_budget')
        return {'summary': sanitize_relational_summary({'status': status, 'blockers': sorted(blockers | {code, 'app_binding_deferred'})}),
                'manifest': {'schema': SCHEMA, 'status': status, 'reason': code}}


def _materialize(state_dir, selections, catalog_complete, max_records, max_seconds, max_record_bytes,
                 reserve_bytes, progress_callback, progress_interval, blockers):
    state = _safe(resolve_layout(state_dir).ingest)
    if not isinstance(selections, list) or len(selections) > 100000:
        raise TargetError('derived_target_invalid')
    selected = sorted(set((r.get('domain'), r.get('stored_source_key', r.get('source_key')),
        r.get('stored_source_version', r.get('source_version'))) for r in selections
        if isinstance(r, dict) and r.get('domain') in DOMAINS and
        isinstance(r.get('stored_source_key', r.get('source_key')), str) and
        isinstance(r.get('stored_source_version', r.get('source_version')), str)))
    if not catalog_complete: blockers.add('catalog_incomplete')
    reserve_bytes = max(0, int(reserve_bytes))
    def disk_check(extra=1024*1024):
        if shutil.disk_usage(state).free < reserve_bytes + extra:
            raise _Limit('disk_reserve')
    start, copied = time.monotonic(), 0
    def check():
        if copied >= max(1, int(max_records)) or time.monotonic()-start >= max(.01, float(max_seconds)):
            raise _Limit()
        disk_check()
    with contextlib.ExitStack() as stack:
        inputs, identities, wal_identities = {}, {}, {}
        for domain in DOMAINS:
            path = _safe(_store(state, domain))
            identity = _identity(path)
            identities[domain] = identity
            wal_identities[domain] = _identity(str(path)+'-wal')
            if identity is None:
                if any(d == domain for d, _, _ in selected): blockers.add('source_database_unavailable')
                continue
            lock = path.with_suffix('.writer.lock')
            if _identity(lock) is None: raise TargetError('source_lock_missing')
            fd = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
            stack.callback(os.close, fd)
            try: fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError: raise TargetError('source_writer_active') from None
            wal = _identity(str(path)+'-wal')
            # A zero-byte retained WAL contains no header, frames or committed
            # data. Under the shared writer lock it may be ignored by immutable
            # reads, but is never deleted/checkpointed. Pin its identity too.
            if wal is not None and wal[2] != 0: raise TargetError('source_wal_present')
            if wal != wal_identities[domain]: raise TargetError('source_changed')
            if _identity(str(path)+'-journal') is not None: raise TargetError('source_journal_present')
            src = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)
            stack.callback(src.close)
            src.row_factory = sqlite3.Row
            src.execute('PRAGMA query_only=ON'); src.execute('PRAGMA trusted_schema=OFF')
            meta = dict(src.execute('SELECT key,value FROM ingest_meta'))
            if meta.get('domain') != domain or meta.get('binding') != 'additive_staging_not_app_bound' or meta.get('schema_version') != '1':
                raise TargetError('source_not_owned')
            inputs[domain] = src
        mapping_path = Path(__file__).with_name('relational-target-mapping.json')
        mapping_hash = hashlib.sha256(mapping_path.read_bytes()).hexdigest()
        code_hash = hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('relational-targets.schema.sql').read_bytes()+mapping_path.read_bytes()).hexdigest()
        # Empty/absent WALs hold no committed data. Their current identities are
        # run-time race guards, not logical content identity or cache invalidators.
        snapshot = _hash([SCHEMA, code_hash, identities, selected, bool(catalog_complete)])
        try: disk_check()
        except _Limit: raise TargetError('disk_reserve') from None
        directory = _safe(resolve_layout(state).household / 'relational-targets' / 'v1')
        for path in (resolve_layout(state).household, directory.parent, directory):
            _safe(path).mkdir(exist_ok=True, mode=0o700)
        lock = _safe(directory / 'materializer.lock')
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        stack.callback(os.close, fd)
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise TargetError('derived_writer_active') from None
        target = _safe(directory / (snapshot+'.sqlite3'))
        manifest_path = _safe(directory / (snapshot+'.manifest.json'))
        exists = _identity(target) is not None
        if exists:
            prior_manifest = None
            if _identity(manifest_path) is not None:
                with manifest_path.open('rb') as stream:
                    raw = stream.read(16*1024*1024+1)
                if len(raw) > 16*1024*1024: raise TargetError('derived_target_invalid')
                prior_manifest = json.loads(raw)
                if prior_manifest.get('snapshot') != snapshot or (prior_manifest.get('write_in_progress') is not True and prior_manifest.get('output_identity') != _identity(target)):
                    raise TargetError('derived_target_invalid')
            recovering = prior_manifest is not None and prior_manifest.get('write_in_progress') is True
            # Only a marked, owned derived target may recover its own SQLite
            # journal. This never applies to input/staging/native databases.
            pre = sqlite3.connect(str(target)) if recovering else sqlite3.connect(target.as_uri()+'?mode=ro', uri=True)
            try:
                meta = dict(pre.execute('SELECT key,value FROM target_meta'))
                if meta.get('snapshot') != snapshot or meta.get('binding') != BINDING:
                    raise TargetError('derived_target_invalid')
                if recovering and (pre.execute('PRAGMA quick_check').fetchall() != [('ok',)] or pre.execute('PRAGMA foreign_key_check').fetchone() is not None):
                    raise TargetError('derived_target_invalid')
                if meta.get('copy_complete') == 'true' and meta.get('resolve_complete') == 'true':
                    if prior_manifest is None: raise TargetError('derived_target_invalid')
                    for domain, identity in identities.items():
                        if _identity(_store(state, domain)) != identity: raise TargetError('source_changed')
                        if _identity(str(_store(state, domain))+'-wal') != wal_identities[domain]: raise TargetError('source_changed')
                        if _identity(str(_store(state, domain))+'-journal') is not None: raise TargetError('source_changed')
                    summary = json.loads(meta['summary']); summary['status'] = 'reused'
                    if recovering:
                        prior_manifest.update(write_in_progress=False, output_identity=_identity(target), status='complete',
                            copy_complete=True,resolve_complete=True,mapping_sha256=mapping_hash,
                            coverage_scope='selected_available_records_only',atomic_publisher_snapshot=False,
                            app_binding='deferred',public_data=False,semantic_review_performed=False)
                        _write_manifest(manifest_path, prior_manifest)
                    return {'summary': sanitize_relational_summary(summary), 'manifest': dict(prior_manifest,status='reused',input_wal_identities=wal_identities)}
            finally: pre.close()
        else:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600); os.close(fd)
        db = sqlite3.connect(target)
        stack.callback(db.close)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA trusted_schema=OFF')
        db.execute('PRAGMA synchronous=FULL')
        if not exists:
            db.executescript(Path(__file__).with_name('relational-targets.schema.sql').read_text())
            db.executemany('INSERT INTO target_meta VALUES(?,?)', [('schema', SCHEMA), ('snapshot', snapshot), ('binding', BINDING), ('copy_complete','false'), ('resolve_complete','false')])
            for domain in DOMAINS:
                has_selection = any(d == domain for d, _, _ in selected)
                status = 'partial' if has_selection else 'schema_only' if domain in PRIVATE else 'empty' if domain in inputs else 'unavailable'
                db.execute('INSERT INTO domains(domain,status,selected_sources) VALUES(?,?,?)', (domain, status, sum(d==domain for d,_,_ in selected)))
            db.commit()
        _write_manifest(manifest_path, {'schema':SCHEMA, 'binding':BINDING, 'snapshot':snapshot,
            'path':str(target), 'status':'building', 'write_in_progress':True,
            'output_identity':_identity(target), 'code_sha256':code_hash,
            'selected_sources':selected, 'input_identities':identities, 'input_wal_identities':wal_identities})
        last_progress = time.monotonic()
        def progress():
            nonlocal last_progress
            now = time.monotonic()
            if not callable(progress_callback) or now-last_progress < max(0,float(progress_interval)):
                return
            last_progress = now
            # Only committed counts, fixed vocabulary and the partial phase
            # status cross the callback boundary; never source values or paths.
            try:
                progress_callback(_summary(db, False, blockers))
            except Exception:
                pass
        copy_complete = True
        try:
            for domain, key, version in selected:
                src = inputs.get(domain)
                source = src.execute('SELECT * FROM sources WHERE source_key=? AND version=?', (key, version)).fetchone() if src else None
                if source is None:
                    blockers.add('source_selection_missing'); copy_complete = False; continue
                if source['status'] != 'complete' or source['errors']:
                    blockers.add('source_partial')
                fingerprint = json.loads(source['fingerprint_json'])
                origin = _hash({k:v for k,v in fingerprint.items() if k != 'adapter_version'}) if all(k in fingerprint for k in ('path','device','inode','size','mtime_ns')) else None
                db.execute('INSERT OR IGNORE INTO source_snapshots VALUES(?,?,?,?,?,?,?)', (domain,key,version,source['provider'],origin,source['status'],source['fingerprint_json']))
                db.execute('INSERT OR IGNORE INTO copy_cursors(domain,source_key,source_version) VALUES(?,?,?)', (domain,key,version))
                cursor = db.execute('SELECT last_record_id,complete FROM copy_cursors WHERE domain=? AND source_key=? AND source_version=?', (domain,key,version)).fetchone()
                if cursor['complete']: continue
                for record in src.execute('SELECT record_id,content_sha256,payload_json FROM records WHERE source_key=? AND source_version=? AND (? IS NULL OR record_id>?) ORDER BY record_id', (key,version,cursor[0],cursor[0])):
                    check()
                    raw = record['payload_json']
                    if len(raw.encode()) > max_record_bytes: raise TargetError('derived_target_invalid')
                    disk_check(4*len(raw.encode())+1024*1024)
                    if hashlib.sha256(raw.encode()).hexdigest() != record['content_sha256']: raise TargetError('payload_hash_mismatch')
                    p = json.loads(raw)
                    if not isinstance(p, dict): raise TargetError('derived_target_invalid')
                    uid = _hash([domain,key,version,record['record_id'],record['content_sha256']])
                    row = {'domain':domain, 'source_key':key, 'source_version':version, 'provider':source['provider']}
                    db.execute('INSERT INTO source_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (uid,domain,key,version,record['record_id'],record['content_sha256'],p.get('kind',p.get('record_type',p.get('type'))),source['provider'],origin,p.get('source_family'),_json(p.get('source_scope')),_json(p.get('source_native_id')),_json(_scope(p))))
                    typed = _project(db, uid, row, p)
                    db.execute('UPDATE domains SET records=records+1,typed_records=typed_records+? WHERE domain=?', (int(typed),domain))
                    db.execute('UPDATE copy_cursors SET last_record_id=? WHERE domain=? AND source_key=? AND source_version=?', (record['record_id'],domain,key,version))
                    copied += 1
                    if copied % 1000 == 0:
                        db.commit(); progress()
                db.execute('UPDATE copy_cursors SET complete=1 WHERE domain=? AND source_key=? AND source_version=?', (domain,key,version))
                db.commit()
                progress()
        except _Limit as exc:
            blockers.update(('resource_budget',exc.reason)); copy_complete = False
        resolve_complete = copy_complete
        if copy_complete:
            try:
                resolved_count = 0
                # Resolution has a separate time budget check; record cap only bounds copying.
                for claim in db.execute("SELECT c.* FROM relation_claims c JOIN relation_resolutions r USING(owner_uid,ordinal) WHERE r.reason='snapshot_coverage_incomplete' ORDER BY c.owner_uid,c.ordinal"):
                    if time.monotonic()-start >= max(.01,float(max_seconds)): raise _Limit()
                    disk_check()
                    owner = dict(db.execute('SELECT * FROM source_records WHERE uid=?', (claim['owner_uid'],)).fetchone())
                    contract, reason, candidates, lookup = _resolve(db, owner, json.loads(claim['detail_json']))
                    candidates = sorted(set(r[0] for r in candidates))
                    disk_check(len(candidates)*512+1024*1024)
                    disposition = 'deferred' if reason else 'missing' if not candidates else 'resolved' if len(candidates)==1 else 'ambiguous'
                    db.execute('UPDATE relation_resolutions SET contract=?,disposition=?,reason=?,candidate_count=?,lookup_json=? WHERE owner_uid=? AND ordinal=?',
                        (contract,disposition,reason or 'exact_selected_snapshot_'+disposition,len(candidates),_json(lookup),claim['owner_uid'],claim['ordinal']))
                    db.executemany('INSERT OR IGNORE INTO relation_candidates VALUES(?,?,?)', [(claim['owner_uid'],claim['ordinal'],x) for x in candidates])
                    resolved_count += 1
                    if resolved_count % 1000 == 0:
                        db.commit(); progress()
            except _Limit as exc:
                blockers.update(('resource_budget',exc.reason)); resolve_complete = False
        for domain in DOMAINS:
            count = db.execute('SELECT COUNT(*) FROM copy_cursors WHERE domain=? AND complete=0',(domain,)).fetchone()[0]
            if copy_complete and not count:
                db.execute("UPDATE domains SET status=CASE WHEN records>0 THEN 'materialized' ELSE 'empty' END WHERE domain=? AND selected_sources>0", (domain,))
        db.execute("UPDATE target_meta SET value=? WHERE key='copy_complete'", ('true' if copy_complete else 'false',))
        db.execute("UPDATE target_meta SET value=? WHERE key='resolve_complete'", ('true' if resolve_complete else 'false',))
        for domain, identity in identities.items():
            if _identity(_store(state, domain)) != identity: raise TargetError('source_changed')
            if _identity(str(_store(state, domain))+'-wal') != wal_identities[domain]: raise TargetError('source_changed')
            if _identity(str(_store(state, domain))+'-journal') is not None: raise TargetError('source_changed')
        if db.execute('PRAGMA foreign_key_check').fetchone() is not None: raise TargetError('derived_target_invalid')
        summary = _summary(db, copy_complete and resolve_complete, blockers)
        db.execute('INSERT OR REPLACE INTO target_meta VALUES(?,?)', ('summary', _json(summary)))
        db.commit()
        db.close()
        manifest = {'schema':SCHEMA, 'binding':BINDING, 'snapshot':snapshot, 'path':str(target), 'status':summary['status'],
            'input_identities':identities, 'selected_sources':selected, 'code_sha256':code_hash,
            'input_wal_identities':wal_identities,
            'mapping_sha256':mapping_hash, 'coverage_scope':'selected_available_records_only',
            'atomic_publisher_snapshot':False, 'write_in_progress':False,
            'copy_complete':copy_complete, 'resolve_complete':resolve_complete, 'output_identity':_identity(target),
            'app_binding':'deferred', 'public_data':False, 'semantic_review_performed':False}
        _write_manifest(manifest_path, manifest)
        return {'summary':summary, 'manifest':manifest}
