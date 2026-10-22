"""Finite, offline bridge from reviewed acquisition receipts to ingest sources.

PRIVATE local metadata only. This module does not fetch, walk directories, write
cache files, repair permissions, extract archives, or open databases. A verified
artifact is an input candidate, not proof of an accepted record or app DB write.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from ingest_catalog import _absolute, _opaque

SCHEMA = 'offmenu-acquired-source-catalog/1'
CURSOR_SCHEMA = 'offmenu-acquired-catalog-cursor/1'
DEFAULT_CACHE = Path('/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache')
DEFAULT_MANIFEST = Path(__file__).with_name('fetch-sources.json')
SHA = re.compile(r'^[a-f0-9]{64}$')
SOURCE_ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,79}$')
ARTIFACT_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$')
MAX_METADATA_BYTES = 4 * 1024**2
CHUNK = 1024**2
# Every filename is an explicit reviewed input, not an extension-based heuristic.
CNOUS_NAMES = ('versailles', 'toulouse', 'strasbourg', 'normandie', 'reunion',
    'rennes', 'reims', 'poitiers', 'paris', 'orleans.tours', 'nice', 'nantes',
    'nancy.metz', 'montpellier', 'lyon', 'limoges', 'lille', 'grenoble', 'creteil',
    'corte', 'clermont.ferrand', 'bordeaux', 'bfc', 'antilles.guyane', 'amiens',
    'aix.marseille')
MEDLINE_NAMES = ('en-any-berry-sauce', 'es-salsa-de-cualquier-baya',
    'en-applesauce-french-toast', 'es-tostada-francesa-con-pure-de-manzana',
    'en-baked-berry-oatmeal', 'es-avena-horneada-con-bayas',
    'en-breakfast-banana-split', 'es-banana-split-para-el-desayuno',
    'en-breakfast-burritos', 'es-burritos-de-desayuno',
    'en-oatmeal-pecan-waffles-or-pancakes', 'es-waffles-panqueques-de-avena-con-pacanas')


def _spec(adapter, role, fmt, domains, compression=None):
    return {'acquired_adapter': adapter, 'acquired_role': role, 'format': fmt,
            'compression': compression, 'domains': list(domains)}


BINDINGS = {}
for _n in range(5):
    BINDINGS['foodista_common_pile', f'{_n:05d}_foodista.jsonl.gz'] = _spec(
        'foodista_common_pile', 'recipe_document', 'jsonl', ('recipes', 'ingredients', 'citations'), 'gz')
BINDINGS['forkrecipe', 'forkrecipe-934319313379201f91ddccdd29abd054039a3ad6.tar.gz'] = _spec(
    'forkrecipe', 'recipe_archive', 'archive', ('recipes', 'ingredients', 'citations'), 'gz')
for _name in MEDLINE_NAMES:
    BINDINGS['medlineplus_healthy_recipes', _name + '.html'] = _spec(
        'medlineplus_healthy_recipes', 'recipe_document', 'html', ('recipes', 'ingredients', 'citations'))
for _name in CNOUS_NAMES:
    BINDINGS['fr_cnous_menus', _name + '.xml'] = _spec(
        'fr_cnous_menus', 'menu', 'xml', ('recipes', 'ingredients', 'citations'))
for _sid, _name, _role, _domains in (
    ('fr_begles_menus', 'met_menu_cantine.json', 'menu', ('recipes', 'citations')),
    ('fr_begles_menus', 'met_plat_cantine.json', 'dish', ('recipes', 'ingredients', 'citations')),
    ('fr_toulouse_menus', 'menus.json', 'menu', ('recipes', 'citations')),
    ('fr_toulouse_menus', 'plats-extrait-de-datameal.json', 'dish', ('recipes', 'citations')),
    ('fr_toulouse_menus', 'denrees-extrait-de-datameal.json', 'ingredient', ('ingredients', 'citations')),
    ('fr_toulouse_menus', 'liste-des-ft-des-denrees-de-la-cc-tls.json', 'technical_sheet_reference', ('citations',)),
):
    BINDINGS[_sid, _name] = _spec(_sid, _role, 'json', _domains)


class CatalogRefusal(ValueError):
    """A fixed, payload-free reason; failure applies to one input, not its peers."""


class ScanBudget(CatalogRefusal):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode()


def artifact_key(source, artifact):
    """Must match fetch_sources.artifact_key without importing the network tool."""
    return hashlib.sha256(_canonical({'source': source['id'],
        'revision': source['revision'], 'artifact': artifact})).hexdigest()


def _identity(st):
    return {'device': st.st_dev, 'inode': st.st_ino, 'size': st.st_size,
            'mtime_ns': st.st_mtime_ns}


def _signature(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _open_dir(path):
    # O_PATH supports exact-name openat/stat without directory listing rights.
    # This is important for the separately approved named-user traverse-only ACL.
    flags = getattr(os, 'O_PATH', os.O_RDONLY) | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for component in _absolute(path).parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _stat(path):
    parent = _open_dir(path.parent)
    try:
        return os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    finally:
        os.close(parent)


def _regular(path):
    # Open each directory through its parent descriptor; no symlink parents.
    parent = _open_dir(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    stream = os.fdopen(fd, 'rb')
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        stream.close()
        raise CatalogRefusal('not_regular_file')
    return stream


def _read_json(path):
    with _regular(path) as stream:
        before = os.fstat(stream.fileno())
        data = stream.read(MAX_METADATA_BYTES + 1)
        if len(data) > MAX_METADATA_BYTES:
            raise CatalogRefusal('metadata_size_limit')
        after = os.fstat(stream.fileno())
        if _signature(before) != _signature(after):
            raise CatalogRefusal('metadata_changed')
    if _signature(after) != _signature(_stat(path)):
        raise CatalogRefusal('metadata_changed')
    value = json.loads(data)
    if not isinstance(value, dict):
        raise CatalogRefusal('invalid_metadata_object')
    return value, hashlib.sha256(data).hexdigest()


def _manifest(options):
    selected = options.get('acquired_manifest', DEFAULT_MANIFEST)
    if isinstance(selected, dict):
        # Explicit in-memory contract fixtures or caller-reviewed metadata only.
        value = json.loads(_canonical(selected))
    else:
        value, _ = _read_json(_absolute(selected))
    if (value.get('schema') != 'offmenu-fetch-sources/1'
            or value.get('execution_host') != 'Foo'
            or value.get('operation') != 'acquisition_only'
            or value.get('ingestion_enabled') is not False
            or not isinstance(value.get('sources'), list)
            or not 1 <= len(value['sources']) <= 100):
        raise CatalogRefusal('invalid_acquisition_manifest')
    return value, hashlib.sha256(_canonical(value)).hexdigest()


def _rights_hold(source):
    # Acquisition approval is not blanket per-record content approval. Adapters
    # still perform row-specific recipe/content/attribution checks.
    if source.get('production_enabled') is not True:
        return 'source_disabled_in_reviewed_manifest'
    if (source.get('rights_status') != 'verified_open_content'
            or not source.get('license') or not source.get('license_evidence')
            or not source.get('attribution')):
        return 'source_rights_not_cleared'
    return None


def _verify_receipt(receipt, source, artifact):
    required = {'schema': 'offmenu-source-fetch/1', 'source_id': source['id'],
        'artifact': artifact['name'], 'artifact_key': artifact_key(source, artifact),
        'source_revision': source['revision'], 'origin_url': artifact['url'],
        'license': source['license'], 'license_evidence': source['license_evidence'],
        'attribution': source['attribution'], 'status': 'complete',
        'acquisition_only': True, 'ingested': False, 'raw_data_uploaded': False,
        'transport_integrity': artifact.get('transport_integrity', 'https')}
    for key, expected in required.items():
        if receipt.get(key) != expected or (isinstance(expected, bool) and type(receipt.get(key)) is not bool):
            raise CatalogRefusal('receipt_binding_mismatch')
    for key, expected in (('license_scope_note', source.get('license_scope_note')),
            ('artifact_metadata_evidence', source.get('artifact_metadata_evidence')),
            ('catalog_resource_id', artifact.get('resource_id')),
            ('artifact_license_evidence', artifact.get('license_evidence'))):
        if receipt.get(key) != expected:
            raise CatalogRefusal('receipt_custody_mismatch')
    size, digest = receipt.get('bytes'), receipt.get('sha256')
    if type(size) is not int or size < 1 or not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise CatalogRefusal('invalid_receipt_integrity')
    maximum = artifact.get('max_bytes')
    if type(maximum) is not int or not 1 <= maximum <= 512 * 1024**2 or size > maximum:
        raise CatalogRefusal('receipt_size_exceeds_manifest')
    if artifact.get('expected_bytes') is not None and size != artifact['expected_bytes']:
        raise CatalogRefusal('receipt_expected_size_mismatch')
    if artifact.get('sha256') is not None and digest != artifact['sha256']:
        raise CatalogRefusal('receipt_expected_checksum_mismatch')
    if (receipt.get('expected_bytes') != artifact.get('expected_bytes')
            or receipt.get('expected_sha256') != artifact.get('sha256')):
        raise CatalogRefusal('receipt_expected_integrity_mismatch')
    basis = 'publisher_sha256_verified' if artifact.get('sha256') else 'locally_observed_not_publisher_authenticated'
    if receipt.get('checksum_basis') != basis:
        raise CatalogRefusal('receipt_checksum_basis_mismatch')


def _reuse_verification(path, receipt, receipt_sha, manifest_sha, previous):
    if not previous:
        return None
    acquisition = (previous.get('metadata') or {}).get('acquisition') or {}
    if not (acquisition.get('verified') is True
            and acquisition.get('manifest_sha256') == manifest_sha
            and acquisition.get('receipt_sha256') == receipt_sha
            and acquisition.get('artifact_key') == receipt['artifact_key']
            and acquisition.get('sha256') == receipt['sha256']
            and acquisition.get('bytes') == receipt['bytes']):
        return None
    # Opening read-only still checks current read permission; a prior hash must
    # never hide an unreadable artifact. No content bytes are read on this path.
    with _regular(path) as stream:
        observed = os.fstat(stream.fileno())
    if (list(_signature(observed)) != acquisition.get('verification_identity')
            or _signature(observed) != _signature(_stat(path))):
        return None
    return observed


def _verify_file(path, receipt, budget):
    with _regular(path) as stream:
        before = os.fstat(stream.fileno())
        if before.st_size != receipt['bytes']:
            raise CatalogRefusal('cache_size_mismatch')
        if before.st_size > budget['remaining_bytes']:
            raise ScanBudget('hash_byte_budget')
        digest = hashlib.sha256()
        read = 0
        while True:
            if time.monotonic() >= budget['deadline']:
                raise ScanBudget('scan_time_budget')
            block = stream.read(min(CHUNK, before.st_size - read + 1))
            if not block:
                break
            read += len(block)
            budget['remaining_bytes'] -= len(block)
            if read > before.st_size:
                raise CatalogRefusal('cache_changed_during_verification')
            digest.update(block)
        after = os.fstat(stream.fileno())
    if _signature(before) != _signature(after) or _signature(after) != _signature(_stat(path)):
        raise CatalogRefusal('cache_changed_during_verification')
    if read != receipt['bytes'] or digest.hexdigest() != receipt['sha256']:
        raise CatalogRefusal('cache_checksum_mismatch')
    return before


def _error_code(exc):
    if isinstance(exc, CatalogRefusal):
        return str(exc)
    if isinstance(exc, PermissionError):
        return 'read_permission_denied'
    if isinstance(exc, FileNotFoundError):
        return 'selected_file_missing'
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)):
        return 'invalid_json_metadata'
    if isinstance(exc, OSError):
        return 'unsafe_or_unreadable_path'
    return 'invalid_manifest_entry'


def _descriptor(root, source, artifact, manifest_sha):
    path = root / source['id'] / artifact['name']
    binding = BINDINGS.get((source['id'], artifact['name']))
    spec = dict(binding) if binding else {'format': 'unknown', 'compression': None, 'domains': ['citations']}
    spec['domains'] = list(spec['domains'])
    result = {'id': _opaque(path), 'acquired_source': True, 'path': str(path), 'provider': source['id'],
        'provider_basis': 'exact_reviewed_manifest_artifact', 'artifact_name': artifact['name'],
        'source_revision': source.get('revision'), 'source_url': artifact.get('url'),
        'license': source.get('license'), 'license_status': 'reviewed_manifest_claim',
        'existing_store': False, 'loaded': False, 'restricted': False,
        'incomplete': False, 'disposition': 'unclassified', 'reason': 'verification_pending',
        'custody': 'unverified_acquisition_cache', 'max_expanded_bytes': artifact.get('max_expanded_bytes'),
        'schema_shape': ('menu_structured' if spec.get('acquired_role') in {'menu', 'dish'} else
            'citation' if spec.get('acquired_role') == 'technical_sheet_reference' else 'unknown'),
        'metadata': {'schema_shape_basis': 'reviewed_manifest_adapter_contract_not_parsed',
          'acquisition': {'verified': False, 'source_id': source['id'],
            'artifact': artifact['name'], 'revision': source.get('revision'),
            'manifest_sha256': manifest_sha, 'license_evidence': source.get('license_evidence'),
            'attribution': source.get('attribution'), 'license_scope_note': source.get('license_scope_note'),
            'lineage_family': source.get('lineage_family'),
            'origin_url': artifact.get('url'), 'transport_integrity': artifact.get('transport_integrity', 'https'),
            'artifact_license_evidence': artifact.get('license_evidence'),
            'catalog_resource_id': artifact.get('resource_id')}}, **spec}
    for key in ('language', 'work_id', 'counterpart_url'):
        if key in artifact:
            result[key] = artifact[key]
    # Preserve artifact-specific credits as well as the family-level attribution.
    if artifact.get('attribution'):
        result['metadata']['acquisition']['artifact_attribution'] = artifact['attribution']
    return result


def _alias_indexes(existing):
    paths, inodes, digests = {}, {}, collections.defaultdict(list)
    for row in existing:
        if not isinstance(row, dict) or not row.get('path'):
            continue
        paths.setdefault(str(_absolute(row['path'])), row)
        ident = row.get('identity') or {}
        if all(key in ident for key in ('device', 'inode', 'size', 'mtime_ns')):
            inodes.setdefault((ident['device'], ident['inode']), row)
            digest = (row.get('metadata') or {}).get('acquisition', {}).get('sha256') or row.get('sha256')
            if isinstance(digest, str) and SHA.fullmatch(digest):
                digests[(digest, ident['size'])].append(row)
    return paths, inodes, digests


def _current_alias(row):
    try:
        observed = _stat(_absolute(row['path']))
        return stat.S_ISREG(observed.st_mode) and _identity(observed) == row.get('identity')
    except (OSError, ValueError):
        return False


def _deduplicate(row, paths, inodes, digests, restriction_updates):
    previous = paths.get(row['path'])
    if previous:
        row['id'] = previous['id']
        # A selected path cannot clear a pre-existing rights hold.
        if previous.get('restricted'):
            row.update(restricted=True, disposition='restricted', reason='alias_of_known_restricted_source')
        # Preserve versions/cursors on repeat discovery of an already-bound
        # acquired source. Parser migrations require explicit adapter versioning.
        if (previous.get('acquired_adapter') == row.get('acquired_adapter')
                and previous.get('identity') == row.get('identity')
                and (previous.get('metadata') or {}).get('acquisition', {}).get('sha256')
                    == row['metadata']['acquisition'].get('sha256')):
            for field in ('sha256', 'format', 'adapter_version'):
                if field in previous:
                    row[field] = previous[field]
                else:
                    row.pop(field, None)
        return
    ident = row.get('identity') or {}
    acquisition = row['metadata']['acquisition']
    candidates = []
    inode_alias = inodes.get((ident.get('device'), ident.get('inode')))
    if inode_alias:
        candidates.append(inode_alias)
    candidates.extend(digests.get((acquisition.get('sha256'), ident.get('size')), []))
    for previous in candidates:
        if previous['id'] == row['id'] or not _current_alias(previous):
            continue
        if previous.get('restricted'):
            row.update(restricted=True, disposition='restricted', reason='alias_of_known_restricted_source',
                       duplicate_of=previous['id'])
            return
        if row.get('restricted'):
            restriction_updates.append({'id': previous['id'], 'reason': 'alias_of_known_restricted_source'})
        compatible = (previous.get('acquired_adapter') == row.get('acquired_adapter')
                      and previous.get('acquired_role') == row.get('acquired_role')
                      and set(previous.get('domains', [])) >= set(row['domains'])
                      and previous.get('work_id') == row.get('work_id')
                      and previous.get('language') == row.get('language'))
        if compatible and previous.get('disposition') in {'candidate', 'duplicate'}:
            row.update(disposition='duplicate', reason='verified_acquired_byte_or_inode_alias', duplicate_of=previous['id'])
            return
        # Byte equality alone cannot reuse a cursor from a different parser.
        acquisition.setdefault('content_aliases', []).append(previous['id'])


def discover_acquired_sources(options=None, existing_sources=()):
    """Verify a finite manifest page; return a private retained-compatible catalog.

    Options: acquired_manifest (path or reviewed dict), acquired_cache_root,
    acquired_resume_cursor, acquired_max_files=100, acquired_max_hash_bytes=512MiB,
    acquired_max_scan_seconds=120. Resume uses a separate cursor; never put it in
    the retained catalog's resume_cursor. The module never persists anything.
    """
    options = dict(options or {})
    root = _absolute(options.get('acquired_cache_root', DEFAULT_CACHE))
    result = {'schema': SCHEMA, 'sources': [], 'errors': [], 'counts': {},
              'source_dispositions': [], 'restriction_updates': [], 'roots': [],
              'truncated': False, 'complete': False, 'resume_cursor': None,
              'stop_reason': None, 'cache_root': str(root)}
    try:
        manifest, manifest_sha = _manifest(options)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        result['errors'].append({'source_id': _opaque('acquired-manifest'), 'operation': 'read_manifest', 'code': _error_code(exc)})
        return result
    result['manifest_sha256'] = manifest_sha
    jobs, source_ids = [], set()
    for source in manifest['sources']:
        sid = source.get('id') if isinstance(source, dict) else None
        if not isinstance(sid, str) or not SOURCE_ID.fullmatch(sid) or sid in source_ids:
            result['errors'].append({'source_id': _opaque(sid), 'operation': 'validate_manifest_entry', 'code': 'invalid_or_duplicate_source_id'})
            continue
        source_ids.add(sid)
        if source.get('production_enabled') is not True:
            result['source_dispositions'].append({'source_id': sid, 'status': 'disabled',
                'reason': 'source_disabled_in_reviewed_manifest'})
            # Disabled rows normally have no artifacts; they are not invented files.
            continue
        artifacts = source.get('artifacts')
        if (not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 50
                or not isinstance(source.get('revision'), str) or not source['revision']):
            result['errors'].append({'source_id': _opaque(sid), 'operation': 'validate_manifest_entry', 'code': 'invalid_source_artifacts'})
            continue
        names = set()
        for artifact in artifacts:
            name = artifact.get('name') if isinstance(artifact, dict) else None
            if not isinstance(name, str) or not ARTIFACT_NAME.fullmatch(name) or name in names:
                result['errors'].append({'source_id': _opaque(sid), 'operation': 'validate_manifest_entry', 'code': 'invalid_or_duplicate_artifact_name'})
                continue
            names.add(name)
            jobs.append((source, artifact))
    cursor = options.get('acquired_resume_cursor') or {}
    if cursor and (cursor.get('schema') != CURSOR_SCHEMA or cursor.get('cache_root') != str(root)
            or cursor.get('manifest_sha256') != manifest_sha or type(cursor.get('next_index')) is not int
            or not 0 <= cursor['next_index'] <= len(jobs)):
        raise ValueError('acquired_catalog_cursor_identity_changed')
    index = cursor.get('next_index', 0)
    max_files = max(1, min(5000, int(options.get('acquired_max_files', 100))))
    budget = {'remaining_bytes': max(0, min(4 * 1024**3, int(options.get('acquired_max_hash_bytes', 512 * 1024**2)))),
              'deadline': time.monotonic() + max(.001, min(3600, float(options.get('acquired_max_scan_seconds', 120))))}
    paths, inodes, digests = _alias_indexes(existing_sources)
    try:
        fd = _open_dir(root)
        os.close(fd)
        result['roots'].append({'path': str(root), 'status': 'present'})
    except OSError as exc:
        # No chmod, credential discovery, sudo, or fallback copy from another host.
        result['roots'].append({'path': str(root), 'status': 'unreadable', 'reason': _error_code(exc)})
    processed = 0
    while index < len(jobs):
        if processed >= max_files or time.monotonic() >= budget['deadline']:
            result['stop_reason'] = 'file_budget' if processed >= max_files else 'scan_time_budget'
            break
        source, artifact = jobs[index]
        row = _descriptor(root, source, artifact, manifest_sha)
        if row['path'] in paths:
            row['id'] = paths[row['path']]['id']
        hold = _rights_hold(source)
        operation = 'read_receipt'
        try:
            if hold:
                row.update(restricted=True, disposition='restricted', reason=hold)
            elif (source['id'], artifact['name']) not in BINDINGS:
                row.update(disposition='adapter-required', reason='no_exact_reviewed_artifact_binding')
            else:
                receipt_path = Path(row['path'] + '.receipt.json')
                receipt, receipt_sha = _read_json(receipt_path)
                expected_format = {'jsonl': 'jsonl.gz', 'archive': 'tar.gz',
                    'html': 'html_recipe', 'xml': 'xml', 'json': 'json'}[row['format']]
                if artifact.get('format') != expected_format:
                    raise CatalogRefusal('manifest_format_binding_mismatch')
                if type(artifact.get('max_expanded_bytes')) is not int or not 1 <= artifact['max_expanded_bytes'] <= 1024**3:
                    raise CatalogRefusal('invalid_expansion_limit')
                _verify_receipt(receipt, source, artifact)
                operation = 'verify_cache_bytes'
                before = _reuse_verification(Path(row['path']), receipt, receipt_sha,
                    manifest_sha, paths.get(row['path']))
                verification_basis = 'cached_byte_hash_and_current_metadata' if before else 'current_full_byte_hash'
                if before is None:
                    before = _verify_file(Path(row['path']), receipt, budget)
                # Re-read the tiny receipt to detect a concurrent receipt replacement.
                _, receipt_sha_after = _read_json(receipt_path)
                if receipt_sha != receipt_sha_after:
                    raise CatalogRefusal('receipt_changed_during_verification')
                if _signature(before) != _signature(_stat(Path(row['path']))):
                    raise CatalogRefusal('cache_changed_during_verification')
                row.update(disposition='candidate', reason='verified_acquisition_receipt_and_bytes',
                    custody='private_local_cache_verified_against_receipt', bytes=before.st_size,
                    mtime_ns=before.st_mtime_ns, identity=_identity(before), sha256=receipt['sha256'])
                row['metadata']['acquisition'].update(verified=True, receipt_path=str(receipt_path),
                    receipt_sha256=receipt_sha, artifact_key=receipt['artifact_key'],
                    sha256=receipt['sha256'], bytes=receipt['bytes'],
                    checksum_basis=receipt['checksum_basis'], completed_at=receipt.get('completed_at'),
                    verification_identity=list(_signature(before)), verification_basis=verification_basis)
            _deduplicate(row, paths, inodes, digests, result['restriction_updates'])
        except ScanBudget as exc:
            result['stop_reason'] = str(exc)
            break
        except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
            code = _error_code(exc)
            row.update(disposition='unreadable' if isinstance(exc, (OSError, PermissionError)) else 'incomplete-hold',
                incomplete=True, reason=code)
            result['errors'].append({'source_id': row['id'], 'operation': operation, 'code': code})
        result['sources'].append(row)
        # The page also deduplicates later manifest inputs without scanning a tree.
        new_paths, new_inodes, new_digests = _alias_indexes([row])
        paths.update(new_paths)
        inodes.update(new_inodes)
        for key, values in new_digests.items():
            digests[key].extend(values)
        processed += 1
        index += 1
    result['truncated'] = index < len(jobs)
    if result['truncated']:
        result['resume_cursor'] = {'schema': CURSOR_SCHEMA, 'cache_root': str(root),
            'manifest_sha256': manifest_sha, 'next_index': index}
    result['complete'] = (not result['truncated'] and not result['errors']
        and all(row['disposition'] in {'candidate', 'duplicate', 'restricted', 'adapter-required'} for row in result['sources']))
    result['counts'] = dict(collections.Counter(row['disposition'] for row in result['sources']))
    result['counts'].update(artifacts_manifest=len(jobs), artifacts_inspected=processed,
        verified_bytes=sum(row.get('bytes', 0) for row in result['sources'] if row['metadata']['acquisition']['verified']),
        disabled_sources=len(result['source_dispositions']), errors=len(result['errors']))
    return result


def merge_acquired_sources(existing_sources, acquired_result):
    """Return merged descriptors, preserving unrelated source IDs/fingerprints.

    Discovery, not this helper, verifies and annotates aliases. This helper only
    replaces the same exact path and merges additive metadata; it never changes
    retained/acquired resume cursors or touches a DB checkpoint.
    """
    merged = [dict(row) for row in existing_sources]
    by_path = {str(_absolute(row['path'])): index for index, row in enumerate(merged) if row.get('path')}
    by_id = {row['id']: index for index, row in enumerate(merged) if row.get('id')}
    for row in acquired_result.get('sources', []):
        row = dict(row)
        index = by_path.get(row['path'], by_id.get(row['id']))
        if index is not None:
            previous = merged[index]
            row['id'] = previous['id']
            row['metadata'] = {**previous.get('metadata', {}), **row.get('metadata', {})}
            merged[index] = {**previous, **row}
        else:
            by_path[row['path']] = len(merged)
            by_id[row['id']] = len(merged)
            merged.append(row)
    restrictions = {item['id']: item['reason'] for item in acquired_result.get('restriction_updates', [])}
    for row in merged:
        if row.get('id') in restrictions:
            row.update(restricted=True, disposition='restricted', reason=restrictions[row['id']])
    return merged


def preflight_acquired_access(options=None):
    """Read-only exact-file open checks; no hash/parse/mutation or ACL changes.

    The returned paths are PRIVATE operational metadata. A readable result proves
    current access only, not receipt integrity or database readiness.
    """
    options = dict(options or {})
    root = _absolute(options.get('acquired_cache_root', DEFAULT_CACHE))
    result = {'schema': 'offmenu-acquired-access/1', 'status': 'unknown',
              'files': [], 'counts': {}, 'integrity_verified': False}
    try:
        manifest, manifest_sha = _manifest(options)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        result.update(status='blocked', reason=_error_code(exc))
        return result
    result['manifest_sha256'] = manifest_sha
    for source in manifest['sources']:
        if not isinstance(source, dict) or source.get('production_enabled') is not True:
            continue
        sid = source.get('id')
        if not isinstance(sid, str) or not SOURCE_ID.fullmatch(sid):
            continue
        for artifact in source.get('artifacts', []):
            name = artifact.get('name') if isinstance(artifact, dict) else None
            if (sid, name) not in BINDINGS:
                continue
            target = root / sid / name
            row = {'source_id': sid, 'artifact': name, 'path': str(target),
                   'artifact_readable': False, 'receipt_readable': False, 'errors': []}
            for label, path in (('artifact', target), ('receipt', Path(str(target) + '.receipt.json'))):
                try:
                    with _regular(path):
                        pass
                    row[label + '_readable'] = True
                except (OSError, ValueError) as exc:
                    row['errors'].append({'target': label, 'code': _error_code(exc)})
            result['files'].append(row)
    readable = sum(row['artifact_readable'] and row['receipt_readable'] for row in result['files'])
    result['counts'] = {'artifacts_total': len(result['files']), 'artifact_receipt_pairs_readable': readable,
                        'artifact_receipt_pairs_blocked': len(result['files']) - readable}
    result['status'] = 'readable' if result['files'] and readable == len(result['files']) else 'blocked'
    return result
