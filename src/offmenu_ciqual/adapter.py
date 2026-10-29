"""Synthetic-only CIQUAL candidate. No acquisition, acceptance or publication.

Ported semantics are regression-tested against the exact retained legacy
functions. Pins describe byte identity; they do not confer source-use rights.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
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

from .xmlxlsx import DataError, DECIMAL, MAX_TEXT, finite_decimal, parse_xml, read_workbook

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = ('offmenu_ciqual/__init__.py', 'offmenu_ciqual/adapter.py',
                'offmenu_ciqual/xmlxlsx.py', 'offmenu_ciqual/contract.json')
WORKBOOK = 'Table Ciqual 2025_ENG_2025_11_03.xlsx'
IDENTITIES = 'alim_2025_11_03.xml'
DICTIONARY = 'ciqual-columns.json'
INPUTS = {WORKBOOK: 'workbook', IDENTITIES: 'identities', DICTIONARY: 'column-map'}
MAX_ASSET = 64 * 1024 * 1024
MAX_BUNDLE = 128 * 1024 * 1024
CANONICAL = {11: ('energy', 'kcal'), 15: ('protein', 'g'), 16: ('proteinNx625', 'g'),
             17: ('carbohydrate', 'g'), 18: ('fat', 'g'), 19: ('sugars', 'g'),
             27: ('fibre', 'g'), 32: ('saturatedFat', 'g'), 50: ('salt', 'g'),
             51: ('calcium', 'mg'), 54: ('iron', 'mg'), 59: ('potassium', 'mg'),
             61: ('sodium', 'mg'), 73: ('vitaminC', 'mg')}
BASIS = {'amount': 100, 'unit': 'g', 'state': 'as-described', 'portion': 'source edible portion'}
HOLDS = ['historical-source-input-not-enabled', 'source-use-review-pending',
         'public-export-not-enabled', 'country-coverage-unassessed',
         'fineli-access-and-zero-semantics-unchanged', 'danish-definition-and-basis-holds-unchanged',
         'production-and-cix-unchanged']


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def deterministic_gzip(raw):
    output = io.BytesIO()
    # GzipFile emits OS=255 and no filename; gzip.compress(mtime=0) on some
    # supported Python versions delegates to a platform-specific zlib header.
    with gzip.GzipFile(filename='', mode='wb', fileobj=output, compresslevel=9, mtime=0) as stream:
        stream.write(raw)
    return output.getvalue()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise DataError('duplicate-json-key')
            result[key] = value
        return result
    def bad(_):
        raise DataError('nonfinite-json-number')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad,
                          parse_float=lambda v: finite_decimal(v)[1])
    except (json.JSONDecodeError, UnicodeError, RecursionError):
        raise DataError('invalid-json') from None


def exact(value, fields, error='invalid-lock-fields'):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise DataError(error)


@contextmanager
def directory_fd(path):
    """Open each absolute path component without following symbolic links."""
    absolute = Path(os.path.abspath(path))
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            for part in absolute.parts[1:]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
        except OSError:
            raise DataError('directory-unavailable-or-symlink') from None
        yield fd
    finally:
        os.close(fd)


def read_bytes(path, maximum=MAX_ASSET, expected=None):
    path = Path(path)
    try:
        with directory_fd(path.parent) as parent:
            fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise DataError('regular-file-required')
                if not 0 < before.st_size <= maximum:
                    raise DataError('asset-size-limit')
                if expected is not None and before.st_size != expected['bytes']:
                    raise DataError('asset-size-mismatch')
                raw = stream.read(maximum + 1)
                after = os.fstat(stream.fileno())
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        stable = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if stable(before) != stable(after) or stable(before) != stable(current):
            raise DataError('input-changed-during-read')
    except OSError:
        raise DataError('input-unavailable-or-symlink') from None
    if len(raw) != before.st_size or len(raw) > maximum:
        raise DataError('asset-size-limit')
    if expected is not None and sha(raw) != expected['sha256']:
        raise DataError('asset-sha256-mismatch')
    return raw


def pin(path, name):
    raw = read_bytes(path)
    return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}


def runtime():
    import pyexpat
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'zlib': zlib.ZLIB_RUNTIME_VERSION, 'expat': pyexpat.EXPAT_VERSION,
            'xlsxReader': 'bounded-stdlib-ooxml/1'}


def fixture_lock(input_root):
    """Synthetic test authoring helper; a scope label is not proof of origin."""
    return {'schemaVersion': 'offmenu-ciqual-input-lock/1', 'sourceId': 'ciqual',
            'releaseId': '2025', 'scope': 'synthetic-fixture',
            'inputs': [{**pin(Path(input_root) / name, name), 'role': INPUTS[name], 'releaseId': '2025'}
                       for name in sorted(INPUTS)],
            'dependencies': [pin(ROOT / name, name) for name in DEPENDENCIES], 'runtime': runtime()}


def validate_lock(lock):
    exact(lock, ('schemaVersion', 'sourceId', 'releaseId', 'scope', 'inputs', 'dependencies', 'runtime'))
    if lock['schemaVersion'] != 'offmenu-ciqual-input-lock/1':
        raise DataError('unsupported-lock-version')
    if lock['sourceId'] != 'ciqual' or lock['releaseId'] != '2025':
        raise DataError('unsupported-source-release')
    if lock['scope'] != 'synthetic-fixture':
        raise DataError('historical-source-input-not-enabled')
    for group, names in [('inputs', INPUTS), ('dependencies', DEPENDENCIES)]:
        items = lock[group]
        if not isinstance(items, list) or len(items) != len(names):
            raise DataError('dependency-set-mismatch')
        seen, total = set(), 0
        for item in items:
            fields = ('path', 'bytes', 'sha256', 'role', 'releaseId') if group == 'inputs' else ('path', 'bytes', 'sha256')
            exact(item, fields)
            name = item['path']
            if not isinstance(name, str) or name not in names or name in seen:
                raise DataError('dependency-set-mismatch')
            seen.add(name)
            if type(item['bytes']) is not int or not 0 < item['bytes'] <= MAX_ASSET:
                raise DataError('invalid-asset-size')
            if not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
                raise DataError('invalid-asset-hash')
            if group == 'inputs' and (item['role'] != INPUTS[name] or item['releaseId'] != '2025'):
                raise DataError('input-release-or-role-mismatch')
            total += item['bytes']
        if total > MAX_BUNDLE:
            raise DataError('bundle-size-limit')
    if lock['runtime'] != runtime():
        raise DataError('runtime-pin-mismatch')


def content_lock(lock):
    validate_lock(lock)
    return {**lock, 'inputs': sorted(lock['inputs'], key=lambda x: x['path']),
            'dependencies': sorted(lock['dependencies'], key=lambda x: x['path'])}


def numeric(raw):
    if raw is None:
        return {'value': None, 'qualifier': 'unknown'}
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise DataError('invalid-quantity-shape')
    original = str(raw)
    if len(original) > MAX_TEXT:
        raise DataError('source-text-limit')
    s = original.strip().replace(',', '.')
    if s in ('', '-'):
        return {'value': None, 'qualifier': 'unknown'}
    qualifiers = {'TR': 'trace', 'TRACE': 'trace', 'N': 'present-no-reliable-amount',
                  'ND': 'not-detected', 'NOT DETECTED': 'not-detected',
                  'NT': 'not-tested', 'NOT TESTED': 'not-tested'}
    if s.upper() in qualifiers:
        return {'value': None, 'qualifier': qualifiers[s.upper()]}
    if s.lower().lstrip('+-') in ('nan', 'inf', 'infinity'):
        raise DataError('nonfinite-quantity')
    match = re.fullmatch(r'<\s*([0-9]+(?:\.[0-9]*)?|\.[0-9]+)', s)
    if match:
        return {'value': None, 'qualifier': 'less-than', 'limit': finite_decimal(match[1])[1]}
    if DECIMAL.fullmatch(s):
        return {'value': finite_decimal(s)[1], 'qualifier': 'source'}
    return {'value': None, 'qualifier': 'source-text', 'originalText': original}


def identity(value):
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,12}', value):
        raise DataError('invalid-native-food-identity')
    return value


def source_text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT:
        raise DataError('invalid-source-text')
    return value


def identities(raw):
    root = parse_xml(raw)
    if root.tag != 'ALIMENTS' or root.attrib or (root.text or '').strip():
        raise DataError('unreviewed-identity-xml-envelope')
    result = {}
    for entry in root:
        if entry.tag != 'ALIMENT' or entry.attrib or (entry.text or '').strip() or (entry.tail or '').strip():
            raise DataError('unreviewed-identity-xml-entry')
        fields = {}
        for child in entry:
            if child.tag in fields or len(child) or child.attrib or (child.tail or '').strip():
                raise DataError('ambiguous-identity-field')
            if child.tag not in ('alim_code', 'alim_nom_fr', 'alim_grp_nom_fr', 'alim_nom_sci'):
                raise DataError('unreviewed-identity-field')
            fields[child.tag] = (child.text or '').strip()
        code = identity(fields.get('alim_code'))
        source_text(fields.get('alim_nom_fr'))
        if code in result:
            raise DataError('duplicate-xml-identity')
        result[code] = fields
    if not result:
        raise DataError('empty-identity-table')
    return result


def validate_dictionary(dictionary, contract):
    if dictionary != contract.get('columnMap'):
        raise DataError('dictionary-contract-drift')
    if dictionary.get('basis') != BASIS or dictionary.get('releaseId') != '2025':
        raise DataError('basis-or-release-drift')
    headers, definitions = dictionary['headers'], dictionary['nutrients']
    if len(headers) != 73 or len(definitions) != 64 or len(set(headers)) != len(headers):
        raise DataError('header-dictionary-shape')
    keys = set()
    for column, definition in enumerate(definitions, 10):
        expected_key, expected_unit = CANONICAL.get(column, ('ciqual:column:' + str(column), definition['unit']))
        if (definition['sourceColumn'] != column or definition['header'] != headers[column - 1]
                or definition['key'] != expected_key or definition['unit'] != expected_unit
                or definition['basis'] != BASIS or definition['key'] in keys
                or definition['unit'] not in ('g', 'mg', 'µg', 'kcal', 'kJ')
                or not definition['header'].endswith('(' + definition['unit'] + '/100g)')):
            raise DataError('column-unit-basis-or-key-drift')
        keys.add(definition['key'])


def normalize(blobs, contract, bundle_sha):
    dictionary = strict_json(blobs[DICTIONARY])
    validate_dictionary(dictionary, contract)
    names = identities(blobs[IDENTITIES])
    workbook = read_workbook(blobs[WORKBOOK])
    headers = dictionary['headers']
    if workbook[0][1] != {i + 1: value for i, value in enumerate(headers)}:
        raise DataError('workbook-header-drift')
    rows, seen, blank = [], set(), 0
    for _, cells in workbook[1:]:
        if not any(value is not None for value in cells.values()):
            blank += 1
            continue
        if any(column > len(headers) for column in cells):
            raise DataError('row-column-overflow')
        code = identity(cells.get(7))
        if code in seen:
            raise DataError('duplicate-workbook-identity')
        seen.add(code)
        if code not in names:
            raise DataError('workbook-xml-identity-mismatch')
        english = source_text(cells.get(8))
        nutrients = {}
        for definition in dictionary['nutrients']:
            column = definition['sourceColumn']
            nutrients[definition['key']] = {**numeric(cells.get(column)), 'unit': definition['unit'],
                'name': ' '.join(definition['header'].split()), 'sourceColumn': column,
                'method': 'ANSES CIQUAL 2025; source definition'}
        rows.append({'schemaVersion': '1.0', 'kind': 'nutrientProfile',
            'id': 'ciqual:nutrientProfile:' + code, 'countries': ['FR'],
            'provenance': {'sourceId': 'ciqual', 'recordId': code,
                'url': 'https://zenodo.org/records/17550133', 'license': 'Etalab Licence Ouverte 2.0',
                'attribution': 'Anses. 2025. Ciqual French food composition table.',
                'sourceDate': '2025', 'releaseId': '2025', 'visibility': 'local-candidate',
                'transform': 'offmenu-ciqual-candidate/1', 'inputBundleSha256': bundle_sha,
                'scope': 'synthetic-fixture',
                'rights': 'Original source terms govern reuse; normalization does not relicense the data.'},
            'data': {'foodName': names[code]['alim_nom_fr'], 'names': {'fr': names[code]['alim_nom_fr'], 'en': english},
                'identifiers': [{'system': 'ANSES-CIQUAL', 'value': code}], 'basis': BASIS,
                'nutrients': nutrients}})
    if seen != set(names):
        raise DataError('workbook-xml-identity-mismatch')
    return rows, {'columnDictionary': dictionary, 'identityDictionary': names}, blank


def render(input_root, lock):
    lock = content_lock(lock)  # Scope checked before source reads.
    dependencies = {p['path']: read_bytes(ROOT / p['path'], expected=p) for p in lock['dependencies']}
    blobs = {p['path']: read_bytes(Path(input_root) / p['path'], expected=p) for p in lock['inputs']}
    contract = strict_json(dependencies['offmenu_ciqual/contract.json'])
    bundle_sha = sha(canonical({'sourceId': 'ciqual', 'releaseId': '2025', 'inputs': lock['inputs']}))
    rows, metadata, blank = normalize(blobs, contract, bundle_sha)
    content = b''.join(canonical([row]) for row in rows)
    files = {'normalized.jsonl.gz': deterministic_gzip(content),
             'source-metadata.json': canonical(metadata)}
    manifest = {'schemaVersion': 'offmenu-ciqual-candidate/1', 'sourceId': 'ciqual', 'releaseId': '2025',
        'scope': 'synthetic-fixture', 'status': 'synthetic-normalized-candidate',
        'buildKey': sha(canonical(lock)), 'inputBundleSha256': bundle_sha, 'dependencyLock': lock,
        'counts': {'raw': len(rows), 'normalized': len(rows), 'accepted': None, 'duplicates': 0,
                   'excluded': 0, 'quarantined': 0, 'blankWorkbookRows': blank, 'nutrientDefinitions': 64},
        'acceptance': 'not-performed', 'publicExport': 'not-enabled', 'holds': HOLDS,
        'completeness': {'executionComplete': True, 'selectedInputSetComplete': True,
                         'selectedScopeComplete': False, 'countryCoverageComplete': False,
                         'countryCoverage': 'unassessed', 'registryComplete': False},
        'artifacts': [{'path': name, 'bytes': len(raw), 'sha256': sha(raw)} for name, raw in sorted(files.items())]}
    files['content-manifest.json'] = canonical(manifest)
    return files


def build(input_root, lock, output):
    """Publish immutable local candidate atomically; no accepted pointer exists."""
    files = render(input_root, lock)
    output = Path(os.path.abspath(output))
    # Output parent must already exist and may not contain symbolic links.
    with directory_fd(output.parent):
        pass
    lock_path = output.parent / '.ciqual-candidate.lock'
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise DataError('output-lock-not-regular')
        fcntl.flock(fd, fcntl.LOCK_EX)
        if output.is_symlink():
            raise DataError('output-symlink-rejected')
        if output.exists():
            if not output.is_dir() or {p.name for p in output.iterdir()} != set(files):
                raise DataError('existing-candidate-conflict')
            for name, raw in files.items():
                if read_bytes(output / name) != raw:
                    raise DataError('existing-candidate-conflict')
            return strict_json(files['content-manifest.json'])
        temporary = Path(tempfile.mkdtemp(prefix='.ciqual-stage-', dir=output.parent))
        try:
            for name, raw in files.items():
                with (temporary / name).open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.rename(temporary, output)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return strict_json(files['content-manifest.json'])
    finally:
        os.close(fd)


def plan_reuse(evidence, bundle_sha, now):
    """Pure 30-day planning; no acquisition, source permission or file verification."""
    exact(evidence, ('scope', 'inputBundleSha256', 'acquiredAt', 'revalidations'), 'invalid-acquisition-evidence')
    if evidence['scope'] != 'synthetic-fixture' or evidence['inputBundleSha256'] != bundle_sha:
        raise DataError('acquisition-evidence-mismatch')
    def instant(value):
        if not isinstance(value, str):
            raise DataError('invalid-evidence-time')
        try:
            result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise DataError('invalid-evidence-time') from None
        if result.tzinfo is None:
            raise DataError('timezone-required')
        return result.astimezone(timezone.utc)
    acquisition, current = instant(evidence['acquiredAt']), instant(now)
    if acquisition > current or not isinstance(evidence['revalidations'], list):
        raise DataError('invalid-acquisition-evidence')
    previous = acquisition
    for item in evidence['revalidations']:
        exact(item, ('at', 'result', 'inputBundleSha256'), 'invalid-revalidation')
        at = instant(item['at'])
        if not previous <= at <= current or item['inputBundleSha256'] != bundle_sha or item['result'] not in ('304', '200-identical'):
            raise DataError('invalid-revalidation')
        previous = at
    age = (current - acquisition).total_seconds()
    return {'action': 'reuse-verified-retained-input' if age < 30 * 86400 else 'revalidation-review-needed',
            'ageSeconds': age, 'minimumReuseDays': 30, 'acquisitionAllowed': False,
            'sourceUsePermission': 'not-established', 'bytesVerifiedByThisDecision': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--lock', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.inputs, strict_json(read_bytes(args.lock, 256 * 1024)), args.output)
    except DataError as error:
        print(json.dumps({'status': 'held', 'code': str(error)}))
        return 2
    print(json.dumps({'status': result['status'], 'buildKey': result['buildKey'], 'normalized': result['counts']['normalized']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
