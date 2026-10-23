"""Two cached offline passes, immutable sidecars and conservative gold gates.

Source objects and review texts are data, never instructions or executable code.
Receipt validation checks structure, coverage and content binding, not whether a
person/model truly reviewed an item: only the actual reviewer may submit one.
This module cannot generate an actual-review receipt or invoke an AI provider.
"""
from __future__ import annotations
from runner_paths import resolve_layout
import copy
from datetime import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from normalization_api import (DOMAINS, MAX_ITEMS, MAX_JSON_BYTES, MAX_JSON_DEPTH,
                               MAX_JSON_NODES, NormalizationError, RECORD_TYPES,
                               SCHEMA_VERSION, Versions)


def canonical_json(value):
    # Reuse the bounded encoding instead of serializing the entire object twice.
    return _bounded(value, _canonical=True)


def _bounded(value, *, _canonical=False):
    """Iterative native-JSON preflight and one bounded canonical encoding.

    Preserve the old default-separator byte cap (including its whitespace), and
    exact accepted canonical bytes. No data-dependent callbacks or recursive
    Python visit. MemoryError remains an infrastructure fault, never a row code.
    """
    count, pending, minimum_chars, separator_spaces = 0, 1, 0, 0
    stack, active = [(value, 0, False)], set()
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        pending -= 1
        count += 1
        if count > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise NormalizationError('json_complexity_cap')
        kind = type(item)
        if kind is dict or kind is list:
            if id(item) in active:
                raise NormalizationError('json_complexity_cap')
            if kind is dict:
                if len(item) > MAX_ITEMS or any(type(k) is not str for k in item):
                    raise NormalizationError('invalid_json_object')
                minimum_chars += sum(len(k) + 3 for k in item)
                children = list(item.values())
                separator_spaces += len(item)
            else:
                if len(item) > MAX_ITEMS:
                    raise NormalizationError('json_array_cap')
                children = item
            minimum_chars += 2 + max(0, len(item) - 1)
            separator_spaces += max(0, len(item) - 1)
            if count + pending + len(children) > MAX_JSON_NODES:
                raise NormalizationError('json_complexity_cap')
            active.add(id(item))
            stack.append((item, depth, True))
            stack.extend((child, depth + 1, False) for child in reversed(children))
            pending += len(children)
        elif kind is str:
            minimum_chars += len(item) + 2
        elif kind is int:
            # Four bits per decimal digit is a conservative lower bound; avoid
            # constructing an arbitrarily large decimal scalar before the cap.
            if item.bit_length() > 4 * MAX_JSON_BYTES:
                raise NormalizationError('json_size_cap')
            minimum_chars += 1
        elif kind in (float, bool, type(None)):
            minimum_chars += 1
        else:
            raise NormalizationError('non_json_value')
        # Lower bound checked before escaping/UTF8 allocation. The encoder may
        # still allocate one escaped scalar chunk, bounded by this input budget.
        if minimum_chars + separator_spaces > MAX_JSON_BYTES:
            raise NormalizationError('json_size_cap')
    chunks, size = [], separator_spaces
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False)
    try:
        # _one_shot=False uses incremental encoding rather than a whole-object
        # C encoder call. Depth/cycles/types were already bounded above.
        for chunk in encoder.iterencode(value, _one_shot=False):
            size += len(chunk.encode('utf-8'))
            if size > MAX_JSON_BYTES:
                raise NormalizationError('json_size_cap')
            chunks.append(chunk)
    except NormalizationError:
        # NormalizationError is a ValueError: do not mask our finite cap code.
        raise
    except (ValueError, TypeError, OverflowError, UnicodeError, RecursionError) as exc:
        raise NormalizationError('invalid_json') from exc
    if _canonical:
        return ''.join(chunks)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def artifact_digest(artifact):
    return digest(artifact)


def _string(value, name, limit=4096):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise NormalizationError('invalid_' + name)
    return value


def _exact(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise NormalizationError('unexpected_or_missing_fields')


def _issues(issues):
    if not isinstance(issues, list) or len(issues) > MAX_ITEMS:
        raise NormalizationError('invalid_issues')
    for issue in issues:
        _exact(issue, ('code', 'severity', 'path', 'detail'))
        _string(issue['code'], 'issue_code', 256)
        if issue['severity'] not in ('warning', 'error'):
            raise NormalizationError('invalid_issue_severity')
        if not isinstance(issue['path'], str) or not isinstance(issue['detail'], str):
            raise NormalizationError('invalid_issue_text')


def validate_normalized(value):
    _bounded(value)
    _exact(value, ('title', 'language', 'fields', 'relations', 'field_lineage'))
    if any(value[k] is not None and not isinstance(value[k], str) for k in ('title', 'language')):
        raise NormalizationError('invalid_title_or_language')
    if not isinstance(value['fields'], dict):
        raise NormalizationError('invalid_fields')
    for key in ('relations', 'field_lineage'):
        if not isinstance(value[key], list) or any(not isinstance(v, dict) for v in value[key]):
            raise NormalizationError('invalid_' + key)
    return value


def _source(record):
    _bounded(record)
    required = ('domain', 'source_key', 'source_version', 'record_id', 'content_sha256', 'payload')
    _exact(record, required, ('record_type', 'provenance', 'row_number'))
    if record['domain'] not in DOMAINS or not isinstance(record['payload'], dict):
        raise NormalizationError('invalid_domain_or_payload')
    for key in ('source_key', 'source_version', 'record_id'):
        _string(record[key], key)
    if record['content_sha256'] != digest(record['payload']):
        raise NormalizationError('source_content_hash_mismatch')
    provenance = record.get('provenance', {})
    if not isinstance(provenance, dict):
        raise NormalizationError('invalid_provenance')
    identity = {key: record[key] for key in required if key != 'payload'}
    return identity, copy.deepcopy(provenance)


def _record_type(record):
    kind = record.get('record_type')
    if kind is None and record['domain'] == 'recipes':
        declared = str(record['payload'].get('record_type', record['payload'].get('type', record['payload'].get('kind', '')))).casefold()
        kind = 'menu' if 'menu' in declared else 'recipe'
    kind = kind or RECORD_TYPES[record['domain']][0]
    if kind not in RECORD_TYPES[record['domain']]:
        raise NormalizationError('record_type_domain_mismatch')
    return kind


def _rule_context(record, versions=None):
    """Shared verified rule identity; does not project or persist the payload."""
    identity, provenance = _source(record)
    versions = (versions or Versions()).as_dict()
    kind = _record_type(record)
    module = importlib.import_module('normalize_recipes' if identity['domain'] == 'recipes' else 'normalization_domains')
    versions['domain_rule_version'] = getattr(module, 'RULE_VERSION', getattr(module, 'VERSION', 'unversioned'))
    cache_key = digest({'pass': 'rules', 'source': identity, 'record_type': kind,
                        'versions': versions, 'provenance': provenance})
    return identity, provenance, versions, kind, module, cache_key


def rule_cache_key(record, versions=None):
    return _rule_context(record, versions)[-1]


def run_rules(record, versions=None, store=None):
    """Rule-only projection. Source originals remain unchanged; no review claim."""
    identity, provenance, versions, kind, module, cache_key = _rule_context(record, versions)
    if store is not None:
        cached = store.get(cache_key)
        if cached is not None:
            validate_artifact(cached, verify_projection=False)
            return cached
    if identity['domain'] == 'recipes':
        projected = module.normalize_record(copy.deepcopy(record['payload']), source_context={**identity, 'record_type': kind})
    else:
        projected = module.normalize_payload(copy.deepcopy(record['payload']), record_type=kind)
    normalized = validate_normalized(projected['normalized'])
    issues = projected.get('issues', [])
    _issues(issues)
    item_ids = projected.get('review_item_ids') or [identity['record_id']]
    if not isinstance(item_ids, list) or not item_ids or len(item_ids) != len(set(item_ids)):
        raise NormalizationError('invalid_review_item_ids')
    for item in item_ids:
        _string(item, 'review_item_id')
    uncertainty = projected.get('uncertainty', [])
    if not isinstance(uncertainty, list) or any(not isinstance(x, str) for x in uncertainty):
        raise NormalizationError('invalid_uncertainty')
    artifact = {
        'artifact_id': 'rules:' + cache_key, 'cache_key': cache_key, 'pass': 'rules',
        'domain': identity['domain'], 'record_type': kind, 'source': identity,
        'source_original': copy.deepcopy(record['payload']), 'versions': versions,
        'normalized': normalized, 'issues': issues, 'uncertainty': uncertainty,
        'provenance': provenance, 'review_item_ids': item_ids,
        'review': {'status': 'pendingreview', 'required': True, 'receipt': None},
        'translation': {'status': 'needs_assessment'},
        'lineage': {'parent_artifact_id': None, 'parent_artifact_sha256': None},
        'normalization_status': 'rules_only', 'gold_status': 'blocked'}
    validate_artifact(artifact, verify_projection=False)
    if store is not None:
        store.put(artifact)
    return artifact


def validate_artifact(artifact, *, verify_projection=True):
    _bounded(artifact)
    _exact(artifact, ('artifact_id', 'cache_key', 'pass', 'domain', 'record_type', 'source',
                     'source_original', 'versions', 'normalized', 'issues', 'uncertainty',
                     'provenance', 'review_item_ids', 'review', 'translation', 'lineage',
                     'normalization_status', 'gold_status'))
    _exact(artifact['versions'], ('rule_version', 'template_version', 'schema_version', 'model_version', 'prompt_version', 'domain_rule_version'))
    _exact(artifact['source'], ('domain', 'source_key', 'source_version', 'record_id', 'content_sha256'))
    _exact(artifact['review'], ('status', 'required', 'receipt'))
    _exact(artifact['lineage'], ('parent_artifact_id', 'parent_artifact_sha256'))
    if not isinstance(artifact['source_original'], dict) or not isinstance(artifact['provenance'], dict):
        raise NormalizationError('invalid_original_or_provenance')
    for key in ('source_key', 'source_version', 'record_id'):
        _string(artifact['source'][key], key)
    if artifact['domain'] not in DOMAINS or artifact['record_type'] not in RECORD_TYPES[artifact['domain']]:
        raise NormalizationError('invalid_artifact_domain')
    if artifact['versions'].get('schema_version') != SCHEMA_VERSION:
        raise NormalizationError('unsupported_schema_version')
    if artifact['source']['domain'] != artifact['domain'] or artifact['source']['content_sha256'] != digest(artifact['source_original']):
        raise NormalizationError('source_identity_mismatch')
    validate_normalized(artifact['normalized'])
    _issues(artifact['issues'])
    if artifact['pass'] not in ('rules', 'interpreted') or artifact['gold_status'] != 'blocked':
        raise NormalizationError('invalid_artifact_state')
    if artifact['pass'] == 'rules' and artifact['review'] != {'status': 'pendingreview', 'required': True, 'receipt': None}:
        raise NormalizationError('rules_cannot_claim_review')
    for version in artifact['versions'].values():
        _string(version, 'version', 256)
    if artifact['review']['required'] is not True:
        raise NormalizationError('actual_review_always_required')
    if artifact['normalization_status'] not in ('rules_only', 'validated', 'pendingreview') or artifact['translation'] != {'status': 'needs_assessment'}:
        raise NormalizationError('invalid_normalization_or_translation_state')
    if not isinstance(artifact['review_item_ids'], list) or not artifact['review_item_ids'] or any(not isinstance(i, str) or not i for i in artifact['review_item_ids']) or len(set(artifact['review_item_ids'])) != len(artifact['review_item_ids']):
        raise NormalizationError('invalid_review_item_ids')
    if not isinstance(artifact['uncertainty'], list) or any(not isinstance(i, str) for i in artifact['uncertainty']):
        raise NormalizationError('invalid_uncertainty')
    if artifact['pass'] == 'rules':
        key = digest({'pass': 'rules', 'source': artifact['source'], 'record_type': artifact['record_type'],
                      'versions': artifact['versions'], 'provenance': artifact['provenance']})
        if artifact['normalization_status'] != 'rules_only' or any(artifact['lineage'].values()):
            raise NormalizationError('invalid_rules_state')
    else:
        parent = artifact['lineage']['parent_artifact_id']
        parent_sha = artifact['lineage']['parent_artifact_sha256']
        if not isinstance(parent, str) or not parent.startswith('rules:') or not isinstance(parent_sha, str):
            raise NormalizationError('invalid_review_lineage')
        key = digest({'pass': 'interpreted', 'parent': parent[6:], 'parent_sha256': parent_sha, 'versions': artifact['versions']})
        if artifact['review']['status'] not in ('reviewed', 'needs_changes', 'rejected') or not isinstance(artifact['review']['receipt'], dict):
            raise NormalizationError('actual_review_receipt_required')
    if artifact['cache_key'] != key or artifact['artifact_id'] != artifact['pass'] + ':' + key:
        raise NormalizationError('artifact_cache_identity_mismatch')
    if verify_projection and artifact['pass'] == 'rules':
        envelope = {**artifact['source'], 'payload': artifact['source_original'],
                    'provenance': artifact['provenance'], 'record_type': artifact['record_type']}
        version_args = {k: v for k, v in artifact['versions'].items() if k != 'domain_rule_version'}
        expected = run_rules(envelope, Versions(**version_args))
        if expected != artifact:
            raise NormalizationError('rules_projection_mismatch_recompute_required')
    return artifact


def interpretation_key(artifact):
    """Content cache excludes fetch/file metadata but keeps all semantic context.

    Exact JSON content is deliberately conservative: IDs and source assertions
    are part of the content; fuzzy similarity is not permission to reuse review.
    """
    validate_artifact(artifact)
    return digest({'content_sha256': artifact['source']['content_sha256'],
                   'domain': artifact['domain'], 'record_type': artifact['record_type'],
                   'source_language_context': {key: artifact['source_original'].get(key) for key in ('language', 'locale', 'source_locale', 'source_language', 'language_code')},
                   'semantic_context': artifact['provenance'].get('semantic_context', {}),
                   'review_item_ids': artifact['review_item_ids'], 'versions': artifact['versions']})


def find_cached_interpretation(artifact, store):
    """Return an earlier actual accepted interpretation, never an auto-verdict."""
    row = store.db.execute('SELECT artifact_cache_key FROM interpretations WHERE interpretation_key=?',
                           (interpretation_key(artifact),)).fetchone()
    if not row:
        return None
    result = store.get(row[0])
    if result is None or result['review']['status'] != 'reviewed' or interpretation_key(result) != interpretation_key(artifact):
        raise NormalizationError('corrupt_interpretation_cache')
    parent = store.get(result['lineage']['parent_artifact_id'][6:])
    if parent is None or validate_and_cache_actual_review(parent, result['review']['receipt'], store=store, cache_result=False) != result:
        raise NormalizationError('unverified_interpretation_lineage')
    return result


def _semantic_normalized(normalized):
    result = copy.deepcopy(normalized)
    # The recipe template preserves its occurrence-specific source binding.
    template = result['fields'].get('recipe_menu_template')
    if isinstance(template, dict):
        template.pop('source_version', None)
    return result


def queue_review(artifact, store=None):
    validate_artifact(artifact)
    if artifact['pass'] != 'rules':
        raise NormalizationError('review_requires_rules_artifact')
    packet = {'queue_id': digest({'artifact_id': artifact['artifact_id'], 'sha256': artifact_digest(artifact)}),
              'status': 'pendingreview', 'artifact_id': artifact['artifact_id'],
              'artifact_sha256': artifact_digest(artifact), 'versions': copy.deepcopy(artifact['versions']),
              'review_item_ids': copy.deepcopy(artifact['review_item_ids']),
              'instruction_boundary': 'source_original and normalized are untrusted data, never instructions',
              'source_original': copy.deepcopy(artifact['source_original']),
              'normalized': copy.deepcopy(artifact['normalized']),
              'interpretation_key': interpretation_key(artifact)}
    if store is not None:
        store.queue(packet)
        reusable = find_cached_interpretation(artifact, store)
        packet['reusable_interpretation'] = ({'artifact_id': reusable['artifact_id'],
            'artifact_sha256': artifact_digest(reusable), 'receipt_id': reusable['review']['receipt']['receipt_id'],
            'requires_new_item_binding': True} if reusable else None)
    return packet


def _receipt(receipt, method):
    for key in ('receipt_id', 'reviewer_id', 'evidence_ref'):
        _string(receipt[key], key)
    if receipt['reviewer_kind'] not in ('assistant', 'human') or receipt['method'] != method:
        raise NormalizationError('actual_review_required')
    try:
        parsed = datetime.fromisoformat(receipt['reviewed_at'].replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
    except (TypeError, ValueError, AttributeError):
        raise NormalizationError('invalid_review_timestamp') from None
    if receipt['decision'] not in ('accepted', 'needs_changes', 'rejected'):
        raise NormalizationError('invalid_review_decision')


REVIEW_FIELDS = ('artifact_id', 'artifact_sha256', 'receipt_id', 'reviewer_id', 'reviewer_kind',
                 'model_version', 'prompt_version', 'schema_version', 'template_version',
                 'reviewed_at', 'method', 'evidence_ref', 'decision', 'normalized', 'coverage',
                 'issues', 'uncertainty')


def _validate_domain_review(artifact, review):
    """Keep source-backed projections immutable; evidence-backed overlays only.

    This conservative v1 contract does not silently turn raw claims into verified
    identity, health, rights or household-merge facts. Future derived field
    families need a versioned typed validator, not arbitrary AI output keys.
    """
    before, after = artifact['normalized'], review['normalized']
    if any(before[key] != after[key] for key in ('title', 'language', 'relations', 'field_lineage')):
        raise NormalizationError('source_projection_scaffold_changed')
    if any(after['fields'].get(key) != value or key not in after['fields'] for key, value in before['fields'].items()):
        raise NormalizationError('source_projection_fields_changed')
    if set(after['fields']) - set(before['fields']) - {'review_interpretation'}:
        raise NormalizationError('untyped_interpretation_fields')
    overlay = after['fields'].get('review_interpretation', {'notes': '', 'resolutions': []})
    _exact(overlay, ('notes', 'resolutions'))
    if not isinstance(overlay['notes'], str) or not isinstance(overlay['resolutions'], list):
        raise NormalizationError('invalid_interpretation_overlay')
    resolved = []
    prior = set(artifact['uncertainty']) | {issue['code'] for issue in artifact['issues']}
    for resolution in overlay['resolutions']:
        _exact(resolution, ('code', 'reason', 'evidence_ref'))
        for key in ('code', 'reason', 'evidence_ref'):
            _string(resolution[key], 'resolution_' + key)
        if resolution['code'] not in prior or resolution['code'] in resolved:
            raise NormalizationError('unknown_or_duplicate_resolution')
        resolved.append(resolution['code'])
    cleared = (set(artifact['uncertainty']) - set(review['uncertainty'])) | ({i['code'] for i in artifact['issues']} - {i['code'] for i in review['issues']})
    if not cleared <= set(resolved):
        raise NormalizationError('cleared_uncertainty_requires_review_evidence')


def validate_and_cache_actual_review(artifact, review, store=None, *, cache_result=True):
    """Accept an externally performed review only; never synthesize a receipt.

    Whole-batch success is insufficient: each item's explicit coverage decision
    is required. A rejection/needs-changes is cached as such, never promoted.
    """
    validate_artifact(artifact)
    _bounded(review)
    _exact(review, REVIEW_FIELDS, ('reuse_of_artifact_id',))
    if artifact['pass'] != 'rules' or review['artifact_id'] != artifact['artifact_id'] or review['artifact_sha256'] != artifact_digest(artifact):
        raise NormalizationError('stale_or_wrong_review')
    _receipt(review, 'direct_item_review')
    for key in ('model_version', 'prompt_version', 'schema_version', 'template_version'):
        if review[key] != artifact['versions'][key] or review[key] == 'unconfigured':
            raise NormalizationError('review_version_mismatch')
    validate_normalized(review['normalized'])
    _issues(review['issues'])
    if not isinstance(review['uncertainty'], list) or any(not isinstance(x, str) for x in review['uncertainty']):
        raise NormalizationError('invalid_uncertainty')
    coverage = review['coverage']
    if not isinstance(coverage, list):
        raise NormalizationError('invalid_coverage')
    covered = []
    for item in coverage:
        _exact(item, ('item_id', 'decision', 'notes'))
        _string(item['item_id'], 'review_item_id')
        if item['decision'] not in ('accepted', 'needs_changes', 'rejected') or not isinstance(item['notes'], str):
            raise NormalizationError('invalid_coverage_decision')
        covered.append(item['item_id'])
    if sorted(covered) != sorted(artifact['review_item_ids']):
        raise NormalizationError('missing_duplicate_or_extra_item_review')
    if review['decision'] == 'accepted' and any(item['decision'] != 'accepted' for item in coverage):
        raise NormalizationError('contradictory_review_decision')
    if artifact['domain'] == 'recipes':
        module = importlib.import_module('normalize_recipes')
        validator = getattr(module, 'validate_reviewed_template', None)
        if validator is None:
            raise NormalizationError('recipe_review_validator_unavailable')
        validator(artifact['normalized'], review['normalized'], review=review)
    else:
        _validate_domain_review(artifact, review)
    if 'reuse_of_artifact_id' in review:
        if store is None:
            raise NormalizationError('interpretation_reuse_requires_verified_cache')
        origin = find_cached_interpretation(artifact, store)
        if origin is None or origin['artifact_id'] != review['reuse_of_artifact_id']:
            raise NormalizationError('stale_or_wrong_interpretation_reuse')
        if review['decision'] != 'accepted' or review['receipt_id'] == origin['review']['receipt']['receipt_id']:
            raise NormalizationError('explicit_new_item_binding_required')
        if (_semantic_normalized(review['normalized']) != _semantic_normalized(origin['normalized'])
                or review['issues'] != origin['issues'] or review['uncertainty'] != origin['uncertainty']):
            raise NormalizationError('interpretation_reuse_changed_semantics')
    cache_key = digest({'pass': 'interpreted', 'parent': artifact['cache_key'],
                        'parent_sha256': artifact_digest(artifact), 'versions': artifact['versions']})
    result = copy.deepcopy(artifact)
    result.update(artifact_id='interpreted:' + cache_key, cache_key=cache_key, **{'pass': 'interpreted'})
    result['normalized'] = copy.deepcopy(review['normalized'])
    result['issues'] = copy.deepcopy(review['issues'])
    result['uncertainty'] = copy.deepcopy(review['uncertainty'])
    result['review'] = {'status': 'reviewed' if review['decision'] == 'accepted' else review['decision'],
                        'required': True, 'receipt': copy.deepcopy(review)}
    result['lineage'] = {'parent_artifact_id': artifact['artifact_id'], 'parent_artifact_sha256': artifact_digest(artifact)}
    result['normalization_status'] = 'validated' if review['decision'] == 'accepted' and not any(i['severity'] == 'error' for i in review['issues']) else 'pendingreview'
    validate_artifact(result)
    if store is not None and cache_result:
        store.put(result)
        if result['review']['status'] == 'reviewed':
            ikey = interpretation_key(artifact)
            store.db.execute('INSERT OR IGNORE INTO interpretations VALUES(?,?)', (ikey, result['cache_key']))
            origin_id = review.get('reuse_of_artifact_id', result['artifact_id'])
            origin_receipt = store.get(origin_id.split(':', 1)[1])['review']['receipt']['receipt_id']
            proof = {'interpretation_key': ikey, 'content_sha256': artifact['source']['content_sha256'],
                     'source_binding': artifact['source'], 'reused_from_review_id': origin_receipt if 'reuse_of_artifact_id' in review else None,
                     'semantic_output_sha256': digest(_semantic_normalized(result['normalized'])),
                     'equivalence': 'exact_content_context_versions_and_coverage'}
            store.db.execute('INSERT OR IGNORE INTO review_bindings VALUES(?,?,?,?,?)',
                (result['artifact_id'], ikey, origin_id, review['receipt_id'], canonical_json(proof)))
            store.db.commit()
        store.finish_queue(artifact['artifact_id'], result['review']['status'])
    return result


def _secure_directory(path):
    path = Path(os.path.abspath(path))
    for parent in (*reversed(path.parents), path):
        if parent.is_symlink():
            raise NormalizationError('symlink_directory_refused')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not path.is_dir() or path.stat().st_mode & 0o077:
        raise NormalizationError('private_directory_permissions_required')
    return path


class NormalizationStore:
    """Only owned private sidecars; never opens a staging/canonical DB for writes."""
    def __init__(self, state_dir):
        directory = _secure_directory(resolve_layout(state_dir).normalization)
        self.path = directory / 'normalized-sidecars.sqlite3'
        if self.path.is_symlink():
            raise NormalizationError('symlink_store_refused')
        if self.path.exists():
            info = self.path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise NormalizationError('private_regular_store_required')
        if self.path.exists() and self.path.stat().st_size:
            check = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
            try:
                if check.execute("SELECT value FROM normalization_meta WHERE key='binding'").fetchone() != ('normalization_sidecar_only/1',):
                    raise NormalizationError('non_owned_store_refused')
            finally:
                check.close()
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS normalization_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT OR IGNORE INTO normalization_meta VALUES('binding','normalization_sidecar_only/1');
        CREATE TABLE IF NOT EXISTS artifacts(cache_key TEXT PRIMARY KEY, artifact_id TEXT UNIQUE NOT NULL, body_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS review_queue(queue_id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL, status TEXT NOT NULL, body_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS interpretations(interpretation_key TEXT PRIMARY KEY, artifact_cache_key TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS review_bindings(artifact_id TEXT PRIMARY KEY, interpretation_key TEXT NOT NULL, origin_artifact_id TEXT NOT NULL, receipt_id TEXT NOT NULL, equivalence_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS translation_units(unit_id TEXT PRIMARY KEY, body_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS translation_bindings(artifact_id TEXT NOT NULL, unit_id TEXT NOT NULL, PRIMARY KEY(artifact_id,unit_id));
        CREATE TABLE IF NOT EXISTS translation_results(unit_id TEXT PRIMARY KEY, body_json TEXT NOT NULL);
        ''')
        self.db.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.db.close()

    def get(self, cache_key):
        row = self.db.execute('SELECT body_json FROM artifacts WHERE cache_key=?', (cache_key,)).fetchone()
        return json.loads(row[0]) if row else None

    def _immutable(self, table, key_name, key, body, extras=()):
        encoded = canonical_json(body)
        row = self.db.execute(f'SELECT body_json FROM {table} WHERE {key_name}=?', (key,)).fetchone()
        if row and row[0] != encoded:
            raise NormalizationError('immutable_cache_conflict_change_version_to_retry')
        values = (key, *extras, encoded)
        self.db.execute(f'INSERT OR IGNORE INTO {table} VALUES({",".join("?" for _ in values)})', values)
        # Another process may have inserted after the first read. Never report a
        # conflicting interpretation as cached merely because INSERT was ignored.
        stored = self.db.execute(f'SELECT body_json FROM {table} WHERE {key_name}=?', (key,)).fetchone()
        self.db.commit()
        if stored != (encoded,):
            raise NormalizationError('immutable_cache_conflict_change_version_to_retry')

    def put(self, artifact):
        validate_artifact(artifact)
        self._immutable('artifacts', 'cache_key', artifact['cache_key'], artifact, (artifact['artifact_id'],))

    def queue(self, packet):
        self._immutable('review_queue', 'queue_id', packet['queue_id'], packet, (packet['artifact_id'], 'pendingreview'))

    def finish_queue(self, artifact_id, status):
        self.db.execute('UPDATE review_queue SET status=? WHERE artifact_id=?', (status, artifact_id))
        self.db.commit()


def iter_staged_records(path, domain):
    """Read the existing identity/payload contract without mutating source staging."""
    if domain not in DOMAINS:
        raise NormalizationError('unknown_domain')
    path = Path(path).absolute()
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise NormalizationError('symlink_staging_refused')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        meta = dict(db.execute('SELECT key,value FROM ingest_meta'))
        if meta.get('binding') != 'additive_staging_not_app_bound' or meta.get('domain') != domain or meta.get('schema_version') != '1':
            raise NormalizationError('incompatible_staging')
        for row in db.execute('''SELECT r.source_key,r.source_version,r.record_id,r.content_sha256,r.payload_json,r.row_number,
                                      s.license,s.provider,s.custody_json
                               FROM records r JOIN sources s ON r.source_key=s.source_key AND r.source_version=s.version
                               ORDER BY r.source_key,r.source_version,r.row_number'''):
            yield {'domain': domain, 'source_key': row[0], 'source_version': row[1], 'record_id': row[2],
                   'content_sha256': row[3], 'payload': json.loads(row[4]), 'row_number': row[5],
                   'provenance': {'license': row[6], 'provider': row[7], 'custody': json.loads(row[8]) if row[8] else None,
                                  'rights_status': 'unverified'}}
    finally:
        db.close()


def _texts(value, pointer):
    if isinstance(value, str) and value.strip():
        yield pointer, value
    elif isinstance(value, dict):
        for key in sorted(value):
            yield from _texts(value[key], pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _texts(child, pointer + '/' + str(index))


def _pointer_value(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise NormalizationError('invalid_translation_field_path')
    try:
        for component in pointer[1:].split('/'):
            component = component.replace('~1', '/').replace('~0', '~')
            value = value[int(component)] if isinstance(value, list) else value[component]
        if not isinstance(value, str) or not value.strip():
            raise ValueError()
    except (KeyError, IndexError, TypeError, ValueError):
        raise NormalizationError('invalid_translation_field_value') from None
    return value


def register_translation_units(artifact, target_language, store=None):
    """Versioned domain text scope or reviewed recipe grammar/lexical units.

    Source text/IDs are never rewritten. Every artifact-to-unit binding remains
    explicit even when identical interpreted content reuses translation work.
    """
    validate_artifact(artifact)
    _string(target_language, 'target_language', 64)
    units = []
    if artifact['domain'] == 'recipes':
        module = importlib.import_module('normalize_recipes')
        hook = getattr(module, 'recipe_translation_units', None)
        if hook is None:
            raise NormalizationError('recipe_translation_registry_unavailable')
        units = hook(artifact, target_language)
        for unit in units:
            _bounded(unit)
            if store is not None:
                store._immutable('translation_units', 'unit_id', unit['unit_id'], unit)
                store.db.execute('INSERT OR IGNORE INTO translation_bindings VALUES(?,?)', (artifact['artifact_id'], unit['unit_id']))
        if store is not None:
            store.db.commit()
        return units
    module = importlib.import_module('normalization_domains')
    scope = getattr(module, 'translation_text_paths', None)
    paths = scope(artifact['normalized']) if scope else [p for p, _ in _texts({'title': artifact['normalized']['title'], 'fields': artifact['normalized']['fields']}, '')]
    if not isinstance(paths, list) or len(paths) != len(set(paths)):
        raise NormalizationError('invalid_translation_scope')
    for pointer in paths:
        original = _pointer_value(artifact['normalized'], pointer)
        key = {'interpretation_key': interpretation_key(artifact), 'record_type': artifact['record_type'],
               'field_path': pointer, 'source_text_sha256': digest(original),
               'source_language': artifact['normalized']['language'], 'target_language': target_language,
               'versions': artifact['versions']}
        unit = dict(key, unit_id=digest(key), source_text=original, status='pendingreview')
        if store is not None:
            store._immutable('translation_units', 'unit_id', unit['unit_id'], unit)
            store.db.execute('INSERT OR IGNORE INTO translation_bindings VALUES(?,?)', (artifact['artifact_id'], unit['unit_id']))
            store.db.commit()
        units.append(unit)
    return units


def validate_and_cache_translation(unit, receipt, store=None):
    _bounded(unit)
    _bounded(receipt)
    _exact(receipt, ('unit_id', 'unit_sha256', 'translated_text', 'receipt_id', 'reviewer_id', 'reviewer_kind',
                     'method', 'evidence_ref', 'reviewed_at', 'decision', 'model_version', 'prompt_version', 'schema_version', 'template_version'))
    _receipt(receipt, 'direct_unit_review')
    if receipt['unit_id'] != unit['unit_id'] or receipt['unit_sha256'] != digest(unit):
        raise NormalizationError('stale_translation')
    _string(receipt['translated_text'], 'translated_text', MAX_JSON_BYTES)
    if unit.get('unit_kind') == 'canonical_template' and receipt['decision'] == 'accepted':
        slots = unit.get('context', {}).get('slot_types')
        if not isinstance(slots, dict):
            raise NormalizationError('canonical_translation_slot_contract_missing')
        def placeholders(pattern):
            if not isinstance(pattern, str):
                raise NormalizationError('canonical_translation_pattern_invalid')
            names = re.findall(r'\{([a-z][a-z0-9_]*)\}', pattern)
            remainder = re.sub(r'\{[a-z][a-z0-9_]*\}', '', pattern)
            if '{' in remainder or '}' in remainder:
                raise NormalizationError('canonical_translation_placeholder_syntax')
            return names
        original = placeholders(unit['source_text'])
        translated = placeholders(receipt['translated_text'])
        if set(original) != set(slots) or sorted(original) != sorted(translated):
            raise NormalizationError('canonical_translation_placeholder_mismatch')
    for key in ('model_version', 'prompt_version', 'schema_version', 'template_version'):
        if receipt[key] != unit['versions'][key] or receipt[key] == 'unconfigured':
            raise NormalizationError('translation_version_mismatch')
    result = {'unit_id': unit['unit_id'], 'status': 'complete' if receipt['decision'] == 'accepted' else 'pendingreview',
              'receipt': copy.deepcopy(receipt)}
    if store is not None:
        store._immutable('translation_results', 'unit_id', unit['unit_id'], result)
    return result


def gold_readiness(artifact, target_language, store=None):
    """Report blockers only; never mutate sources, approve fetch or promote data."""
    validate_artifact(artifact)
    _string(target_language, 'target_language', 64)
    blockers = []
    # A reviewed-looking JSON object is not enough. Replay its cached receipt
    # against its immutable rules parent and compare the entire derived output.
    parent = store.get(artifact['lineage']['parent_artifact_id'][6:]) if store and artifact['pass'] == 'interpreted' else None
    cached = store.get(artifact['cache_key']) if store else None
    if parent is None or cached != artifact:
        blockers.append('validated_cache_lineage_required')
    else:
        try:
            replayed = validate_and_cache_actual_review(parent, artifact['review']['receipt'], store=store, cache_result=False)
            if replayed != artifact:
                blockers.append('review_receipt_output_mismatch')
        except (NormalizationError, ValueError, KeyError, TypeError):
            blockers.append('review_receipt_invalid')
    if artifact['pass'] != 'interpreted' or artifact['normalization_status'] != 'validated':
        blockers.append('validated_interpreted_pass_required')
    review = artifact['review']
    if review.get('status') != 'reviewed' or not review.get('receipt'):
        blockers.append('actual_item_review_required')
    elif not review['receipt'].get('coverage') or any(x.get('decision') != 'accepted' for x in review['receipt']['coverage']):
        blockers.append('complete_item_review_required')
    if artifact['uncertainty'] or any(issue['severity'] == 'error' for issue in artifact['issues']):
        blockers.append('unresolved_uncertainty_or_validation_error')
    if artifact['domain'] == 'recipes':
        hook = getattr(importlib.import_module('normalize_recipes'), 'recipe_gold_blockers', None)
        if hook is None:
            blockers.append('recipe_gold_validator_unavailable')
        else:
            additional = hook(artifact)
            if not isinstance(additional, list) or any(not isinstance(item, str) or not item for item in additional):
                raise NormalizationError('invalid_recipe_gold_blockers')
            blockers.extend(item for item in additional if item not in blockers)
    provenance = artifact['provenance']
    if provenance.get('rights_status') != 'cleared' or not isinstance(provenance.get('rights_evidence'), str) or not provenance['rights_evidence'].strip():
        blockers.append('rights_not_cleared')
    if not isinstance(provenance.get('custody'), (str, dict)) or not provenance.get('custody') or not isinstance(provenance.get('citation_ids'), list) or not provenance['citation_ids'] or any(not isinstance(c, str) or not c.strip() for c in provenance['citation_ids']):
        blockers.append('provenance_or_citations_incomplete')
    language = artifact['normalized']['language']
    if not language or language == 'und':
        blockers.append('source_language_unknown')
    if artifact['pass'] == 'interpreted' and review.get('status') == 'reviewed':
        units = register_translation_units(artifact, target_language)
        for unit in units:
            if not unit.get('source_language') or unit['source_language'] == 'und':
                blockers.append('translation_unit_language_unknown')
                break
            if unit['source_language'] == target_language:
                continue
            row = store.db.execute('SELECT body_json FROM translation_results WHERE unit_id=?', (unit['unit_id'],)).fetchone() if store else None
            result = json.loads(row[0]) if row else None
            if not result or result['status'] != 'complete' or validate_and_cache_translation(unit, result['receipt']) != result:
                blockers.append('translation_units_pendingreview')
                break
    return {'artifact_id': artifact['artifact_id'], 'artifact_sha256': artifact_digest(artifact),
            'ready': not blockers, 'blockers': blockers, 'target_language': target_language,
            'production_fetch_enabled': False}


def build_gold_manifest(artifacts, target_language, store=None, expected_counts=None):
    """Candidate evidence, not a claim the eight source databases are complete.

    Explicit authoritative expected record counts are mandatory in all 8 domains.
    This prevents empty, sampled or incomplete batches becoming a gold corpus.
    """
    entries, counts, seen = [], {domain: 0 for domain in DOMAINS}, set()
    source_versions, citation_counts, cited = {}, {}, set()
    for artifact in artifacts:
        source = artifact['source']
        identity = tuple(source[key] for key in ('domain', 'source_key', 'source_version', 'record_id'))
        if identity in seen:
            raise NormalizationError('duplicate_gold_source_identity')
        seen.add(identity)
        version_key = (source['domain'], source['source_key'])
        if version_key in source_versions and source_versions[version_key] != source['source_version']:
            raise NormalizationError('gold_manifest_mixes_historical_source_versions')
        source_versions[version_key] = source['source_version']
        if artifact['domain'] == 'citations':
            citation_counts[source['record_id']] = citation_counts.get(source['record_id'], 0) + 1
        cited.update(c for c in artifact['provenance'].get('citation_ids', []) if isinstance(c, str))
        entries.append(gold_readiness(artifact, target_language, store))
        counts[artifact['domain']] += 1
    coverage_complete = (isinstance(expected_counts, dict) and set(expected_counts) == set(DOMAINS)
                         and all(type(expected_counts[d]) is int and expected_counts[d] >= 0 and counts[d] == expected_counts[d] for d in DOMAINS))
    missing_citations = sorted(c for c in cited if citation_counts.get(c) != 1)
    return {'manifest_version': 'offmenu.gold-candidate-manifest/1', 'domains': counts,
            'expected_counts': expected_counts, 'coverage_complete': coverage_complete,
            'ready': bool(entries) and coverage_complete and not missing_citations and all(entry['ready'] for entry in entries),
            'citation_coverage_complete': not missing_citations, 'missing_or_ambiguous_citation_ids': missing_citations,
            'entries': entries, 'production_fetch_enabled': False,
            'status': 'candidate_only_not_promoted'}


class CompactNormalizationStore:
    """Bounded DB-only runner cache, separate from legacy full review artifacts.

    A rules projection is compressed once without source_original. The queue
    holds only its immutable cache/hash reference. Originals are resolved from
    the staging DB by the caller and verified again when a packet is needed.
    Batches atomically publish cache entries, unresolved references and cursor;
    legacy NormalizationStore/review validation are deliberately unchanged.
    """
    BINDING = 'compact_db_normalization_only/1'

    def __init__(self, state_dir, domain):
        if domain not in DOMAINS or domain in ('user_profiles', 'inventory'):
            raise NormalizationError('public_domain_required')
        self.layout = resolve_layout(state_dir)
        directory = _secure_directory(self.layout.normalization)
        self.path = directory / ('compact-' + domain + '.sqlite3')
        for path in (self.path, Path(str(self.path) + '-wal'), Path(str(self.path) + '-shm'), Path(str(self.path) + '-journal')):
            if path.is_symlink():
                raise NormalizationError('symlink_store_refused')
            if path.exists() and (not path.is_file() or path.stat().st_mode & 0o077):
                raise NormalizationError('private_regular_store_required')
        if self.path.exists() and self.path.stat().st_size:
            check = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=2)
            try:
                if check.execute("SELECT value FROM compact_meta WHERE key='binding'").fetchone() != (self.BINDING,):
                    raise NormalizationError('non_owned_store_refused')
            finally:
                check.close()
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        self.db = sqlite3.connect(self.path, timeout=2)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA cache_size=-4096')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS compact_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT OR IGNORE INTO compact_meta VALUES('binding','compact_db_normalization_only/1');
        CREATE TABLE IF NOT EXISTS rules_cache(cache_key TEXT PRIMARY KEY,
            artifact_sha256 TEXT NOT NULL,compact_sha256 TEXT NOT NULL,body_zlib BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS review_refs(cache_key TEXT PRIMARY KEY REFERENCES rules_cache(cache_key),
            artifact_sha256 TEXT NOT NULL,status TEXT NOT NULL CHECK(status='pendingreview'));
        CREATE TABLE IF NOT EXISTS progress(snapshot_key TEXT PRIMARY KEY,cursor_json TEXT NOT NULL,
            counters_json TEXT NOT NULL,complete INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS unresolved_refs(snapshot_key TEXT NOT NULL,source_key TEXT NOT NULL,
            source_version TEXT NOT NULL,record_id TEXT NOT NULL,content_sha256 TEXT,
            reason TEXT NOT NULL,PRIMARY KEY(snapshot_key,source_key,source_version,record_id));
        ''')
        self.db.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.db.close()

    def checkpoint(self, snapshot_key):
        row = self.db.execute('SELECT CASE WHEN length(CAST(cursor_json AS BLOB))<=? THEN cursor_json ELSE NULL END,counters_json,complete FROM progress WHERE snapshot_key=?', (MAX_JSON_BYTES, snapshot_key)).fetchone()
        if row is None:
            return None
        if row[0] is None:
            raise NormalizationError('invalid_compact_checkpoint')
        cursor, counters = json.loads(row[0]), json.loads(row[1])
        names = ('scanned', 'rules_new', 'rules_reused', 'pendingreview', 'accepted',
                 'rejected', 'needs_changes', 'unresolved', 'failed')
        self._cursor_json(cursor)
        _exact(counters, names)
        if (any(type(value) is not int or not 0 <= value <= 10**15 for value in counters.values())
                or row[2] not in (0, 1)
                or counters['scanned'] != counters['rules_new'] + counters['rules_reused'] + counters['failed']
                or counters['pendingreview'] != counters['rules_new'] + counters['rules_reused']
                or counters['unresolved'] > counters['scanned']
                or any(counters[key] for key in ('accepted', 'rejected', 'needs_changes'))):
            raise NormalizationError('invalid_compact_checkpoint')
        return cursor, counters, bool(row[2])

    @staticmethod
    def _cursor_json(cursor):
        # This is the private database PK, not an admitted normalization identity.
        # A long invalid identity must still be checkpointed and resumed past.
        if (cursor is not None and (not isinstance(cursor, list) or len(cursor) != 3
                or any(not isinstance(value, str) for value in cursor))):
            raise NormalizationError('invalid_compact_checkpoint')
        return canonical_json(cursor)  # Bounded by MAX_JSON_BYTES, including UTF-8.

    @classmethod
    def peek_checkpoint(cls, state_dir, domain, snapshot_key):
        """Read the bounded durable progress even when disk reserve blocks writes."""
        if domain not in DOMAINS or domain in ('user_profiles', 'inventory'):
            raise NormalizationError('public_domain_required')
        path = resolve_layout(state_dir).normalization / ('compact-' + domain + '.sqlite3')
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise NormalizationError('symlink_store_refused')
        if not path.exists():
            return None
        if (not path.is_file() or path.stat().st_mode & 0o077
                or path.parent.stat().st_mode & 0o077):
            raise NormalizationError('private_regular_store_required')
        for suffix in ('-wal', '-shm', '-journal'):
            if Path(str(path) + suffix).is_symlink():
                raise NormalizationError('symlink_store_refused')
        reader = object.__new__(cls)
        reader.db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)
        try:
            if reader.db.execute("SELECT value FROM compact_meta WHERE key='binding'").fetchone() != (cls.BINDING,):
                raise NormalizationError('non_owned_store_refused')
            return reader.checkpoint(snapshot_key)
        finally:
            reader.db.close()

    @staticmethod
    def encode(artifact):
        import zlib
        # run_rules already verifies the projection; do not run it a second time.
        validate_artifact(artifact, verify_projection=False)
        compact = {key: value for key, value in artifact.items() if key != 'source_original'}
        raw = canonical_json(compact).encode('utf-8')
        return (artifact['cache_key'], artifact_digest(artifact), hashlib.sha256(raw).hexdigest(), zlib.compress(raw, 1))

    @staticmethod
    def encode_compact(compact, artifact_sha256):
        import zlib
        # Validate/encode this root once. No bytes are persisted before all
        # compact state/normalized/issues checks below have passed.
        raw = canonical_json(compact).encode('utf-8')
        _exact(compact, ('artifact_id', 'cache_key', 'pass', 'domain', 'record_type', 'source',
            'versions', 'normalized', 'issues', 'uncertainty', 'provenance', 'review_item_ids',
            'review', 'translation', 'lineage', 'normalization_status', 'gold_status'))
        if (not isinstance(artifact_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', artifact_sha256)
                or compact['pass'] != 'rules' or compact['gold_status'] != 'blocked'
                or compact['normalization_status'] != 'rules_only'
                or compact['review'] != {'status': 'pendingreview', 'required': True, 'receipt': None}):
            raise NormalizationError('invalid_compact_rule_state')
        validate_normalized(compact['normalized'])
        _issues(compact['issues'])
        return (compact['cache_key'], artifact_sha256, hashlib.sha256(raw).hexdigest(), zlib.compress(raw, 1))

    def get_compact(self, cache_key):
        import zlib
        row = self.db.execute('SELECT artifact_sha256,compact_sha256,body_zlib FROM rules_cache WHERE cache_key=?', (cache_key,)).fetchone()
        if row is None:
            return None
        if len(row[2]) > MAX_JSON_BYTES:
            raise NormalizationError('compact_cache_size_cap')
        decoder = zlib.decompressobj()
        try:
            raw = decoder.decompress(row[2], MAX_JSON_BYTES + 1)
        except zlib.error as exc:
            raise NormalizationError('compact_cache_corrupt') from exc
        if len(raw) > MAX_JSON_BYTES or not decoder.eof or decoder.unused_data or hashlib.sha256(raw).hexdigest() != row[1]:
            raise NormalizationError('compact_cache_corrupt')
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise NormalizationError('compact_cache_corrupt')
        _bounded(body)
        if (body.get('cache_key') != cache_key or 'source_original' in body or body.get('pass') != 'rules'
                or body.get('normalization_status') != 'rules_only' or body.get('gold_status') != 'blocked'
                or body.get('review') != {'status': 'pendingreview', 'required': True, 'receipt': None}):
            raise NormalizationError('compact_cache_corrupt')
        return body, row[0]

    def resolve(self, cache_key, record):
        """Materialize ONE original-bound artifact; no file lookup or AI call."""
        found = self.get_compact(cache_key)
        if found is None:
            raise NormalizationError('compact_cache_missing')
        body, expected = found
        versions = Versions(**{key: value for key, value in body['versions'].items() if key != 'domain_rule_version'})
        if rule_cache_key(record, versions) != cache_key:
            raise NormalizationError('stale_database_source_reference')
        artifact = {**body, 'source_original': copy.deepcopy(record['payload'])}
        validate_artifact(artifact, verify_projection=False)
        if artifact_digest(artifact) != expected:
            raise NormalizationError('compact_artifact_hash_mismatch')
        return artifact

    def commit_batch(self, snapshot_key, entries, failures, cursor, counters, *, complete=False):
        """One transaction, including the durable cursor; no per-record commits."""
        self.layout.verify_lease()
        if len(entries) + len(failures) > 1000:
            raise NormalizationError('compact_batch_row_cap')
        cursor_json = self._cursor_json(cursor)
        try:
            self.db.execute('BEGIN IMMEDIATE')
            for entry in entries:
                prior = self.db.execute('SELECT artifact_sha256,compact_sha256,body_zlib FROM rules_cache WHERE cache_key=?', (entry[0],)).fetchone()
                if prior is not None and prior != tuple(entry[1:]):
                    raise NormalizationError('immutable_cache_conflict_change_version_to_retry')
                self.db.execute('INSERT OR IGNORE INTO rules_cache VALUES(?,?,?,?)', entry)
                self.db.execute("INSERT OR IGNORE INTO review_refs VALUES(?,?,'pendingreview')", entry[:2])
            for reference, reason in failures:
                self.db.execute('INSERT OR REPLACE INTO unresolved_refs VALUES(?,?,?,?,?,?)',
                    (snapshot_key, *reference, reason))
            self.db.execute('INSERT INTO progress VALUES(?,?,?,?) ON CONFLICT(snapshot_key) DO UPDATE SET cursor_json=excluded.cursor_json,counters_json=excluded.counters_json,complete=excluded.complete',
                (snapshot_key, cursor_json, canonical_json(counters), int(complete)))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
