"""Strict offline Matvaretabellen candidate, derived from the pinned legacy reader.

Only authored fixtures are enabled in this review slice. The adapter has no
network, source acquisition, curation, acceptance, or public publication path.
Operational acquisition/revalidation evidence is deliberately outside content.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = ('offmenu_norway/__init__.py', 'offmenu_norway/adapter.py',
                'offmenu_norway/contract.json')
INPUTS = ('en-foods.json', 'nb-foods.json', 'en-nutrients.json', 'en-sources.json')
HEX = re.compile(r'[0-9a-f]{64}')
MAX_ASSET = 32 * 1024 * 1024
MAX_BUNDLE = 64 * 1024 * 1024


class AdapterError(ValueError):
    """Fixed, source-content-free error codes suitable for run receipts."""


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise AdapterError('duplicate-json-key')
            value[key] = item
        return value
    def constant(_):
        raise AdapterError('nonfinite-json-number')
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise AdapterError('nonfinite-json-number')
        if number == 0 and Decimal(value) != 0:
            raise AdapterError('quantity-underflow-held')
        return number
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
        raise AdapterError('invalid-json') from None


def exact(value, fields, code='invalid-lock-fields'):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise AdapterError(code)


def text(value, code='invalid-source-text'):
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(code)
    return value


def safe_path(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise AdapterError('symlink-path-rejected')
    return path


def read_bytes(path, maximum, expected=None):
    """Bound and verify selected regular files; never discover adjacent inputs."""
    path = safe_path(path)
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise AdapterError('regular-file-required')
        if before.st_size > maximum:
            raise AdapterError('asset-size-limit-exceeded')
        if expected is not None and before.st_size != expected['bytes']:
            raise AdapterError('asset-size-mismatch')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        current = path.stat()
    except OSError:
        raise AdapterError('input-file-unavailable') from None
    fields = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    if any(fields(x) != fields(before) for x in (opened, after, current)):
        raise AdapterError('input-changed-during-read')
    if len(raw) > maximum:
        raise AdapterError('asset-size-limit-exceeded')
    if expected is not None and sha(raw) != expected['sha256']:
        raise AdapterError('asset-sha256-mismatch')
    return raw


def pin(path, name):
    raw = read_bytes(path, MAX_ASSET)
    return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}


def runtime():
    return {'implementation': platform.python_implementation(),
            'python': platform.python_version(), 'zlib': zlib.ZLIB_RUNTIME_VERSION}


def fixture_lock(input_root):
    """Authoring helper for this package's synthetic test inputs, never an import grant."""
    root = safe_path(input_root)
    return {'schemaVersion': 'offmenu-norway-input-lock/1',
            'sourceId': 'matvaretabellen', 'releaseId': '2026',
            'scope': 'synthetic-fixture',
            'inputs': [pin(root / name, name) for name in sorted(INPUTS)],
            'dependencies': [pin(ROOT / name, name) for name in DEPENDENCIES],
            'runtime': runtime()}


def validate_inventory(items, expected_names):
    if not isinstance(items, list) or len(items) != len(expected_names):
        raise AdapterError('dependency-set-mismatch')
    seen = set()
    total = 0
    for item in items:
        exact(item, ('path', 'bytes', 'sha256'))
        name = item['path']
        if not isinstance(name, str) or name not in expected_names or name in seen:
            raise AdapterError('dependency-set-mismatch')
        seen.add(name)
        if type(item['bytes']) is not int or not 1 <= item['bytes'] <= MAX_ASSET:
            raise AdapterError('invalid-asset-size')
        if not isinstance(item['sha256'], str) or not HEX.fullmatch(item['sha256']):
            raise AdapterError('invalid-asset-hash')
        total += item['bytes']
    if total > MAX_BUNDLE:
        raise AdapterError('bundle-size-limit-exceeded')


def validate_lock(lock):
    exact(lock, ('schemaVersion', 'sourceId', 'releaseId', 'scope', 'inputs',
                 'dependencies', 'runtime'))
    if lock['schemaVersion'] != 'offmenu-norway-input-lock/1':
        raise AdapterError('unsupported-lock-version')
    if lock['sourceId'] != 'matvaretabellen' or lock['releaseId'] != '2026':
        raise AdapterError('unsupported-source-release')
    if lock['scope'] != 'synthetic-fixture':
        raise AdapterError('historical-source-input-not-enabled')
    validate_inventory(lock['inputs'], set(INPUTS))
    validate_inventory(lock['dependencies'], set(DEPENDENCIES))
    if lock['runtime'] != runtime():
        raise AdapterError('runtime-pin-mismatch')


def content_pins(lock):
    validate_lock(lock)
    # Inventory order and caller filesystem location have no semantic meaning.
    return {**lock, 'inputs': sorted(lock['inputs'], key=lambda x: x['path']),
            'dependencies': sorted(lock['dependencies'], key=lambda x: x['path'])}


def build_key(lock):
    return sha(canonical(content_pins(lock)))


def bundle_key(lock):
    validate_lock(lock)
    return sha(canonical({'sourceId': lock['sourceId'], 'releaseId': lock['releaseId'],
                         'inputs': sorted(lock['inputs'], key=lambda x: x['path'])}))


def verify_bundle(lock, input_root):
    validate_lock(lock)
    resources = {}
    for item in lock['dependencies']:
        resources[item['path']] = read_bytes(ROOT / item['path'], item['bytes'], item)
    contract = strict_json(resources['offmenu_norway/contract.json'])
    if (contract.get('sourceId') != lock['sourceId'] or
            contract.get('releaseId') != lock['releaseId'] or
            contract.get('scope') != 'synthetic-fixture-only' or
            set(contract.get('inputFiles', {})) != set(INPUTS)):
        raise AdapterError('adapter-contract-mismatch')
    # Every asset is verified before parsing any source body. These exact verified
    # bytes are then parsed, so a second path open cannot substitute source data.
    raw = {item['path']: read_bytes(Path(input_root) / item['path'], item['bytes'], item)
           for item in lock['inputs']}
    return {name: strict_json(body) for name, body in raw.items()}, contract


def numeric(raw):
    """Legacy qualifiers, hardened against malformed bounds, booleans and overflow."""
    if raw is None or (isinstance(raw, str) and raw.strip() in ('', '-')):
        return {'value': None, 'qualifier': 'unknown'}
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise AdapterError('invalid-quantity-shape')
    value = str(raw).strip().replace(',', '.')
    if value.upper() in ('TR', 'TRACE'):
        return {'value': None, 'qualifier': 'trace'}
    if value.upper() == 'N':
        return {'value': None, 'qualifier': 'present-no-reliable-amount'}
    if value.upper() in ('ND', 'NOT DETECTED'):
        return {'value': None, 'qualifier': 'not-detected'}
    if value.upper() in ('NT', 'NOT TESTED'):
        return {'value': None, 'qualifier': 'not-tested'}
    bound = re.fullmatch(r'<\s*(\d+(?:\.\d*)?|\.\d+)', value)
    if bound:
        limit = float(bound[1])
        if not math.isfinite(limit):
            raise AdapterError('nonfinite-quantity')
        if limit == 0 and Decimal(bound[1]) != 0:
            raise AdapterError('quantity-underflow-held')
        return {'value': None, 'qualifier': 'less-than', 'limit': limit}
    # Python's float parser accepts underscores that are not part of the verified
    # source numeric grammar. Keep such notation unresolved rather than coerce it.
    if '_' in value:
        return {'value': None, 'qualifier': 'source-text', 'originalText': str(raw)}
    try:
        decimal = Decimal(value)
        number = float(value)
    except (ValueError, InvalidOperation):
        return {'value': None, 'qualifier': 'source-text', 'originalText': str(raw)}
    if not math.isfinite(number):
        raise AdapterError('nonfinite-quantity')
    if number == 0 and decimal != 0:
        raise AdapterError('quantity-underflow-held')
    return {'value': number, 'qualifier': 'source'}


def indexed(document, array_key, id_key):
    if not isinstance(document, dict) or not isinstance(document.get(array_key), list):
        raise AdapterError('invalid-source-envelope')
    rows = document[array_key]
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise AdapterError('invalid-source-row')
        identity = text(row.get(id_key), 'invalid-native-identity')
        if identity in result:
            raise AdapterError('duplicate-native-identity')
        result[identity] = row
    return result


def reference(value):
    if value is not None:
        text(value, 'invalid-source-reference')
    return value


def validate_explicit_bases(value, expected):
    """Do not erase a contradictory denominator at any source coordinate."""
    if isinstance(value, dict):
        if 'basis' in value and value['basis'] != expected:
            raise AdapterError('source-basis-drift-held')
        for key, child in value.items():
            if key != 'basis':
                validate_explicit_bases(child, expected)
    elif isinstance(value, list):
        for child in value:
            validate_explicit_bases(child, expected)


def normalize(documents, contract, inventory_hash):
    validate_explicit_bases(documents, contract['basis'])
    foods = indexed(documents['en-foods.json'], 'foods', 'foodId')
    nb = indexed(documents['nb-foods.json'], 'foods', 'foodId')
    definitions = indexed(documents['en-nutrients.json'], 'nutrients', 'nutrientId')
    sources = indexed(documents['en-sources.json'], 'sources', 'sourceId')
    if not foods:
        raise AdapterError('empty-selected-release')
    if set(foods) != set(nb):
        raise AdapterError('locale-identity-set-mismatch')
    for definition in definitions.values():
        text(definition.get('name'))
        text(definition.get('unit'), 'invalid-nutrient-unit')
        if definition.get('euroFirId') is not None:
            text(definition['euroFirId'], 'invalid-component-identity')
    rows, unresolved = [], set()
    for key, food in foods.items():
        name = text(food.get('foodName'))
        native_name = text(nb[key].get('foodName'))
        uri = text(food.get('uri'))
        if not isinstance(food.get('constituents'), list):
            raise AdapterError('invalid-constituent-array')
        for field in ('portions', 'langualCodes'):
            if not isinstance(food.get(field), list):
                raise AdapterError('invalid-food-metadata')
        if 'basis' in food and food['basis'] != contract['basis']:
            raise AdapterError('source-basis-drift-held')
        nutrients, native_ids = {}, set()
        for observation in food['constituents']:
            if not isinstance(observation, dict):
                raise AdapterError('invalid-constituent-row')
            nutrient_id = text(observation.get('nutrientId'), 'invalid-component-identity')
            if nutrient_id in native_ids:
                raise AdapterError('duplicate-food-component')
            native_ids.add(nutrient_id)
            if nutrient_id not in definitions:
                raise AdapterError('missing-nutrient-definition-held')
            definition = definitions[nutrient_id]
            component = definition.get('euroFirId') or nutrient_id
            unit = observation.get('unit', definition['unit'])
            text(unit, 'invalid-nutrient-unit')
            if unit != definition['unit']:
                raise AdapterError('source-unit-drift-held')
            mapping = contract['canonicalComponents'].get(component)
            mapped = mapping[0] if mapping else 'matvaretabellen:' + component
            if mapping and unit != mapping[1]:
                raise AdapterError('canonical-unit-drift-held')
            if mapped in nutrients or mapped in ('energy', 'energyKJ'):
                raise AdapterError('canonical-component-collision-held')
            source_id = reference(observation.get('sourceId'))
            if source_id is not None and source_id not in sources:
                unresolved.add(source_id)
            nutrients[mapped] = {**numeric(observation.get('quantity')),
                'unit': unit, 'name': definition['name'], 'sourceComponent': component,
                'reference': source_id,
                'method': 'source-reported; see retained nutrient source metadata'}
        for field, mapped, unit in (('calories', 'energy', 'kcal'), ('energy', 'energyKJ', 'kJ')):
            energy = food.get(field)
            if not isinstance(energy, dict):
                raise AdapterError('invalid-energy-shape')
            if 'unit' in energy and energy['unit'] != unit:
                raise AdapterError('energy-unit-drift-held')
            source_id = reference(energy.get('sourceId'))
            if source_id is not None and source_id not in sources:
                unresolved.add(source_id)
            nutrients[mapped] = {**numeric(energy.get('quantity')), 'unit': unit,
                                 'method': 'source-reported', 'reference': source_id}
        rows.append({'schemaVersion': '1.0', 'kind': 'nutrientProfile',
            'id': 'matvaretabellen:nutrientProfile:' + key, 'countries': ['NO'],
            'provenance': {'sourceId': 'matvaretabellen', 'recordId': key, 'url': uri,
                'license': contract['license'], 'attribution': contract['attribution'],
                'sourceDate': '2026', 'releaseId': '2026',
                'inputBundleSha256': inventory_hash, 'visibility': 'local-candidate',
                'transform': 'offmenu-norway-offline-candidate/1',
                'rights': 'Original source terms govern reuse; normalization does not relicense the data.'},
            'data': {'foodName': name, 'names': {'en': name, 'nb': native_name},
                'identifiers': [{'system': 'NO-Matvaretabellen', 'value': key}],
                'basis': contract['basis'], 'nutrients': nutrients,
                'portions': food['portions'], 'langualCodes': food['langualCodes']}})
    metadata = {'schemaVersion': 'offmenu-norway-native-metadata/1',
                'nutrients': documents['en-nutrients.json'],
                'sources': documents['en-sources.json'],
                'unresolvedSourceIds': sorted(unresolved)}
    return rows, metadata


def render(lock, input_root):
    documents, contract = verify_bundle(lock, input_root)
    rows, metadata = normalize(documents, contract, bundle_key(lock))
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=1) as writer:
        for row in rows:
            writer.write(canonical([row]))
    assets = {'normalized.jsonl.gz': stream.getvalue(), 'source-metadata.json': canonical(metadata)}
    manifest = {'schemaVersion': 'offmenu-norway-candidate/1',
        'sourceId': 'matvaretabellen', 'releaseId': '2026', 'scope': lock['scope'],
        'status': 'synthetic-normalized-candidate', 'buildKey': build_key(lock),
        'inputBundleSha256': bundle_key(lock), 'dependencyLock': content_pins(lock),
        'artifacts': [{'path': name, 'bytes': len(body), 'sha256': sha(body)}
                      for name, body in sorted(assets.items())],
        'counts': {'raw': len(rows), 'normalized': len(rows), 'duplicates': 0,
                   'quarantined': 0, 'excluded': 0, 'accepted': None,
                   'nutrientDefinitions': len(metadata['nutrients']['nutrients']),
                   'sourceReferences': len(metadata['sources']['sources']),
                   'unresolvedSourceReferences': len(metadata['unresolvedSourceIds'])},
        'completeness': {'executionComplete': True, 'selectedInputSetComplete': True,
                         'selectedScopeComplete': False, 'registryComplete': False,
                         'countryCoverageComplete': False, 'countryCoverage': 'unassessed'},
        'acceptance': 'not-performed', 'publicExport': 'not-enabled',
        'holds': contract['holds']}
    assets['content-manifest.json'] = canonical(manifest)
    return assets


@contextmanager
def writer_lock(parent):
    path = safe_path(parent / '.norway-candidate.lock')
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except OSError:
        raise AdapterError('output-lock-unavailable') from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AdapterError('output-lock-must-be-regular-file')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def build(lock, input_root, output):
    """Immutable local candidate only. Repeats verify every previously written byte."""
    assets = render(lock, input_root)
    output = safe_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with writer_lock(output.parent):
        if output.exists():
            if not output.is_dir() or {p.name for p in output.iterdir()} != set(assets):
                raise AdapterError('existing-candidate-mismatch')
            for name, body in assets.items():
                if read_bytes(output / name, len(body)) != body:
                    raise AdapterError('existing-candidate-mismatch')
            return {'status': 'verified-existing-candidate', 'buildKey': build_key(lock)}
        stage = Path(tempfile.mkdtemp(prefix='.norway-stage-', dir=output.parent))
        try:
            for name, body in assets.items():
                with (stage / name).open('xb') as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
            stage_fd = os.open(stage, os.O_RDONLY)
            try:
                os.fsync(stage_fd)
            finally:
                os.close(stage_fd)
            os.rename(stage, output)
            directory_fd = os.open(output.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return {'status': 'created-local-candidate', 'buildKey': build_key(lock)}


def timestamp(value):
    if not isinstance(value, str):
        raise AdapterError('invalid-evidence-timestamp')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise AdapterError('invalid-evidence-timestamp') from None
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise AdapterError('evidence-timestamp-must-be-utc')
    return result


def plan_reuse(lock, evidence, *, now):
    """Read-only acquisition plan; code/retransform/revalidation cannot reset age."""
    validate_lock(lock)
    exact(evidence, ('schemaVersion', 'inputBundleSha256', 'originalAcquiredAt', 'revalidations'),
          'invalid-acquisition-evidence')
    inventory_hash = bundle_key(lock)
    if (evidence['schemaVersion'] != 'offmenu-norway-acquisition-evidence/1' or
            evidence['inputBundleSha256'] != inventory_hash):
        raise AdapterError('evidence-bundle-mismatch')
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise AdapterError('policy-clock-must-be-aware')
    acquired = timestamp(evidence['originalAcquiredAt'])
    age = (now - acquired).total_seconds()
    if age < 0:
        raise AdapterError('acquisition-timestamp-in-future')
    if not isinstance(evidence['revalidations'], list):
        raise AdapterError('invalid-revalidation-evidence')
    for event in evidence['revalidations']:
        exact(event, ('observedAt', 'result', 'inputBundleSha256'), 'invalid-revalidation-evidence')
        observed = timestamp(event['observedAt'])
        if (event['result'] not in ('not-modified-304', 'identical-body-200') or
                event['inputBundleSha256'] != inventory_hash or
                not acquired <= observed <= now):
            raise AdapterError('invalid-revalidation-evidence')
    return {'schemaVersion': 'offmenu-norway-reuse-plan/1',
            'inputBundleSha256': inventory_hash, 'minimumReuseDays': 30,
            'acquisitionAgeDays': int(age // 86400),
            'decision': 'reuse-verified-retained-inputs' if age < 30 * 86400
                        else 'revalidation-review-required-no-download',
            'assetBytesVerifiedByThisPlan': False, 'mtimeUsedForFreshness': False,
            'revalidationResetsAcquisitionAge': False, 'networkRequests': 0,
            'onlineAcquisition': 'not-implemented'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', required=True, type=Path)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        lock = strict_json(read_bytes(args.lock, 65536))
        print(json.dumps(build(lock, args.inputs, args.output), sort_keys=True))
    except AdapterError as error:
        print(json.dumps({'status': 'failed', 'code': str(error)}, sort_keys=True))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
