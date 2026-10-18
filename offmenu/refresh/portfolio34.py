"""Worker34 metadata bindings. Never opens or admits a source data body.

This is a portfolio declaration adapter over shared refresh primitives. A valid
metadata declaration is not a SourceContract or a permission to parse food data.
"""
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat

from .acceptance import fingerprint
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .national_tabular import valid_input_name
from .serialization import encode_records

MAX_METADATA_BYTES = 512 * 1024
POLICY = 'worker34-metadata-declaration-v1-no-source-body-or-admission'


@dataclass(frozen=True)
class MetadataPin:
    name: str
    path: str
    sha256: str


@dataclass(frozen=True)
class Binding:
    country: str
    source_id: str
    release_id: str
    role: str
    metadata: tuple
    fields: tuple  # (declaration field, input alias, exact JSON pointer)
    acquisition: tuple | None  # input alias/pointer; never validation age or mtime
    holds: tuple
    unknowns: tuple
    fixture: bool = False


def pointer(document, selector):
    """Strict existing JSON pointer, with no search, fallback or guessed field."""
    if selector == '':
        return document
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-invalid')
    value = document
    for raw in selector[1:].split('/'):
        if re.search(r'~(?![01])', raw):
            raise ValueError('selector-invalid')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch('0|[1-9][0-9]*', key):
                raise ValueError('selector-invalid')
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise ValueError('selector-invalid')
    return value


def _binding_errors(binding):
    if (not isinstance(binding, Binding)
            or binding.country not in ('GQ', 'GS', 'GT', 'GU')
            or any(not isinstance(x, str) or not x for x in
                   (binding.source_id, binding.release_id, binding.role))
            or not binding.metadata or len(binding.metadata) > 16
            or len({p.name for p in binding.metadata}) != len(binding.metadata)
            or type(binding.fixture) is not bool):
        return ['binding-invalid']
    names = {p.name for p in binding.metadata}
    for pin in binding.metadata:
        if (not valid_input_name(pin.name) or not isinstance(pin.path, str)
                or not isinstance(pin.sha256, str)
                or not re.fullmatch('[0-9a-f]{64}', pin.sha256)):
            return ['binding-invalid']
    seen = set()
    for field in binding.fields:
        if (not isinstance(field, tuple) or len(field) != 3
                or not all(isinstance(x, str) and x for x in field)
                or '/' in field[0] or '~' in field[0] or field[0] in seen
                or field[1] not in names or not field[2].startswith('/')):
            return ['binding-invalid']
        seen.add(field[0])
    if not binding.fields:
        return ['binding-invalid']
    if (binding.acquisition is not None
            and (len(binding.acquisition) != 2 or binding.acquisition[0] not in names)):
        return ['binding-invalid']
    if any(not isinstance(x, str) or not x for x in (*binding.holds, *binding.unknowns)):
        return ['binding-invalid']
    return []


def _row(binding, documents):
    policy = fingerprint({'policy': POLICY, 'binding': asdict(binding)})
    data, origins = {}, {}
    pins = {p.name: p.sha256 for p in binding.metadata}
    for field, alias, selector in binding.fields:
        data[field] = pointer(documents[alias], selector)
        # Preserve every scalar, including null, without interpreting units/bases.
        for target in datum_pointers(data[field], '/data/' + field):
            suffix = target[len('/data/' + field):]
            origins[target] = {'kind': 'source', 'sourceId': binding.source_id,
                               'releaseId': binding.release_id, 'inputPath': alias,
                               'inputSha256': pins[alias], 'sourceRecordId': selector,
                               'sourceField': selector + suffix}
    acquired = (pointer(documents[binding.acquisition[0]], binding.acquisition[1])
                if binding.acquisition is not None else None)
    return {'id': binding.source_id + ':metadata', 'kind': 'sourceInputDeclaration',
            'schemaVersion': '1.0', 'data': data,
            'provenance': {'sourceId': binding.source_id, 'releaseId': binding.release_id,
                           'fetchedAt': acquired,
                           'fieldOrigins': origins}}, policy


def semantic_errors(binding, documents, row):
    """Shared SourceContract callback for this metadata representation only.

Checks literal coordinates/values, not a nutrition/price/recipe interpretation.
Never use this callback to qualify food or statistical observation records.
"""
    try:
        expected, _ = _row(binding, documents)
        errors = field_origin_errors(row, {p.name: p.sha256 for p in binding.metadata})
        if fingerprint(row) != fingerprint(expected):
            errors.append('metadata-selector-value-mismatch')
        return sorted(set(errors))
    except (KeyError, ValueError, TypeError, IndexError, RecursionError):
        return ['metadata-selector-invalid']


def diagnose(binding, supplied, *, now, previous_key=None):
    """Pure bounded metadata -> deterministic declaration/diagnostics; no I/O.

All failure codes are fixed and contain no source values or exception contents.
Each call is independent, so a held/malformed source cannot cancel its peers.
"""
    result = {'schemaVersion': 'offmenu-worker34-binding/1',
              'status': 'malformed', 'errors': [], 'rows': [], 'inputKey': None,
              'contentReplay': 'not-established', 'cache': None,
              'sourceBodyOperations': 0, 'networkRequests': 0,
              'capabilities': {'sharedPureRawCachePlanner': 'unavailable-on-pinned-baseline',
                               'realSourceDataAdapter': 'not-selected'},
              'sourceDataAccepted': False, 'countryComplete': False}
    errors = set(_binding_errors(binding))
    if errors:
        result['errors'] = sorted(errors)
        return result
    result.update(country=binding.country, sourceId=binding.source_id,
                  releaseId=binding.release_id, role=binding.role,
                  fixture=binding.fixture, holds=list(binding.holds),
                  unknowns=list(binding.unknowns))
    try:
        if (not isinstance(now, datetime) or now.tzinfo is None
                or now.utcoffset().total_seconds() != 0):
            raise ValueError('clock-invalid')
        if previous_key is not None and (not isinstance(previous_key, str)
                or not re.fullmatch('[0-9a-f]{64}', previous_key)):
            raise ValueError('previous-key-invalid')
        if not isinstance(supplied, dict):
            raise ValueError('metadata-envelope-invalid')
        documents = {}
        expected = {p.name for p in binding.metadata}
        if set(supplied) - expected:
            errors.add('metadata-inventory-unexpected')
        for pin in binding.metadata:
            if pin.name not in supplied:
                errors.add('metadata-missing')
                continue
            raw = supplied[pin.name]
            if not isinstance(raw, bytes) or len(raw) > MAX_METADATA_BYTES:
                errors.add('metadata-bound-or-type-invalid')
                continue
            if sha(raw) != pin.sha256:
                errors.add('metadata-pin-mismatch')
                continue
            try:
                documents[pin.name] = strict_json(raw)
                canonical(documents[pin.name])  # Reject overflowing JSON numbers.
            except (ValueError, UnicodeError, RecursionError):
                errors.add('metadata-json-invalid')
        if len(documents) != len(binding.metadata) or errors:
            result['status'] = ('stale-input' if 'metadata-pin-mismatch' in errors
                                else 'missing-input' if 'metadata-missing' in errors
                                else 'malformed')
            result['errors'] = sorted(errors)
            return result
        try:
            row, policy = _row(binding, documents)
        except (KeyError, ValueError, TypeError, IndexError, RecursionError):
            result.update(status='missing-input', errors=['metadata-selector-missing'])
            return result
        errors.update(semantic_errors(binding, documents, row))
        key = fingerprint({'policy': policy, 'metadataPins':
                           sorted((p.name, p.sha256) for p in binding.metadata)})
        result.update(inputKey=key, rows=[row], policySha256=policy,
                      contentReplay='unchanged-no-op' if previous_key == key else 'new-declaration')
        acquired = None
        if binding.acquisition is not None:
            try:
                acquired = timestamp(pointer(documents[binding.acquisition[0]],
                                             binding.acquisition[1]))
            except (KeyError, ValueError, TypeError, IndexError):
                errors.add('original-acquisition-evidence-invalid')
        else:
            errors.add('original-acquisition-evidence-missing')
        if acquired is not None:
            age = (now - acquired).total_seconds()
            if age < 0:
                errors.add('original-acquisition-in-future')
            else:
                result['cache'] = {'originalAcquiredAt': acquired.isoformat(),
                                   'acquisitionAgeDays': int(age // 86400),
                                   'minimumReuseDays': 30,
                                   'scope': 'metadata-age-intent-only',
                                   'validationAgeResetsAcquisition': False,
                                   'bodyCacheVerified': False,
                                   'decision': 'reuse-retained-metadata-only' if age < 30*86400
                                   else 'conditional-review-required-no-download'}
        if binding.holds:
            errors.add('source-held')
        if binding.unknowns:
            errors.add('source-fields-unresolved')
        stale = result['cache'] is not None and result['cache']['acquisitionAgeDays'] >= 30
        result['status'] = ('held' if binding.holds else 'missing-input' if errors
                            else 'stale-input' if stale
                            else 'ready-metadata-only')
        if stale:
            errors.add('metadata-cache-age-review-required')
        result['errors'] = sorted(errors)
        return result
    except (ValueError, TypeError, OverflowError, RecursionError):
        result.update(status='malformed', errors=['metadata-contract-invalid'], rows=[])
        return result


def read_declared_metadata(binding):
    """Open only trusted binding metadata paths. Never follow pointers into bodies."""
    result = {}
    for pin in binding.metadata:
        try:
            path = safe_path(pin.path)
            if not stat.S_ISREG(path.stat().st_mode):
                result[pin.name] = None
                continue
            with path.open('rb') as stream:
                result[pin.name] = stream.read(MAX_METADATA_BYTES + 1)
        except FileNotFoundError:
            continue
        except (OSError, RefreshError):
            result[pin.name] = None
    return result


def report(bindings, *, now, previous_keys=None, loader=None):
    loader = loader or read_declared_metadata
    results = []
    for binding in bindings:
        try:
            supplied = loader(binding)
        except Exception:
            supplied = None  # Isolate reader failures, never echo exception text.
        results.append(diagnose(binding, supplied, now=now,
                                previous_key=(previous_keys or {}).get(binding.source_id)))
    return {'schemaVersion': 'offmenu-worker34-portfolio-report/1', 'results': results,
            'sourceDataAccepted': False, 'networkRequests': 0,
            'declarationsSha256': sha(encode_records([row for r in results for row in r['rows']]))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC observation clock')
    parser.add_argument('--previous-key', action='append', default=[], metavar='SOURCE=SHA256')
    args = parser.parse_args(argv)
    from .portfolio34_bindings import BINDINGS
    previous = {}
    for pair in args.previous_key:
        source, sep, key = pair.partition('=')
        if not sep or source in previous or source not in {b.source_id for b in BINDINGS}:
            parser.error('invalid previous-key source')
        previous[source] = key
    try:
        value = report(BINDINGS, now=timestamp(args.now), previous_keys=previous)
    except ValueError:
        parser.error('invalid observation clock')
    print(canonical(value).decode(), end='')
    return 0 if all(r['status'] == 'ready-metadata-only' for r in value['results']) else 2


if __name__ == '__main__':
    # Fixed bindings import this module by its package name; use that same class
    # identity when invoked with -m, rather than a second __main__.Binding class.
    from offmenu.refresh.portfolio34 import main as entrypoint
    raise SystemExit(entrypoint())
