"""BH/KI/RE retained-metadata bindings; never a source-body execution route.

Uses the shared strict JSON, path, field-origin and serialization contracts.
Inputs and output are bounded metadata, not recipe/CPI/nutrient payloads.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .refresh.core import (RefreshError, atomic_json, canonical, safe_path, sha,
                           strict_json, timestamp)
from .refresh.field_provenance import datum_pointers, field_origin_errors
from .refresh.national_tabular import valid_input_name
from .refresh.serialization import encode_records

CONFIG = Path(__file__).resolve().parents[1] / 'config/portfolio-worker09-bindings.json'
MAX_METADATA = 256 * 1024
MAX_RECORDS = 32
MIN_REUSE_SECONDS = 30 * 86400
COUNTRIES = {'BH', 'KI', 'RE'}
ROLES = {'recipe-index-link', 'recipe-submission-link', 'cookbook-catalogue-link',
         'certificate-document-link'}
KI_FIELDS = ('country', 'id', 'canonical_url', 'version', 'category',
             'dataset_acquired', 'redistribution_rights', 'acquisition_rights',
             'http_status', 'bytes', 'sha256', 'utc', 'scope')


def _require(condition, code):
    if not condition:
        raise RefreshError(code)


def _url(value):
    _require(isinstance(value, str) and not any(ord(c) < 32 for c in value),
             'metadata-url-invalid')
    try:
        u = urlsplit(value)
        _require(u.scheme == 'https' and bool(u.hostname) and not u.username
                 and not u.password, 'metadata-url-invalid')
    except ValueError:
        raise RefreshError('metadata-url-invalid') from None


def _load_pin(root, item):
    _require(isinstance(item, dict) and valid_input_name(item.get('path')),
             'metadata-input-path-invalid')
    _require(item['path'].endswith('.json'), 'metadata-json-only')
    _require(type(item.get('bytes')) is int and 0 < item['bytes'] <= MAX_METADATA
             and isinstance(item.get('sha256'), str)
             and bool(re.fullmatch('[0-9a-f]{64}', item['sha256'])),
             'metadata-input-pin-invalid')
    p = safe_path(safe_path(root) / item['path'])
    try:
        with p.open('rb') as stream:
            raw = stream.read(MAX_METADATA + 1)
    except FileNotFoundError:
        raise RefreshError('metadata-input-missing') from None
    _require(len(raw) == item['bytes'] and sha(raw) == item['sha256'],
             'metadata-input-pin-mismatch')
    try:
        return strict_json(raw)
    except (ValueError, UnicodeError, TypeError):
        raise RefreshError('metadata-json-malformed') from None


def _select(binding, value):
    _require(isinstance(value, dict), 'metadata-object-required')
    if binding['profile'] == 'bfm-catalogue':
        _require(value.get('country') == 'BH'
                 and value.get('source', {}).get('sha256') == binding['publisherBodySha256']
                 and value.get('recordCount') == binding['expectedRecords'],
                 'metadata-catalogue-identity-mismatch')
        rows = value.get('records')
        _require(isinstance(rows, list), 'metadata-records-required')
        for row in rows:
            _require(isinstance(row, dict) and row.get('country') == 'BH'
                     and row.get('sourceURL') == binding['sourceURL']
                     and row.get('role') in ROLES
                     and type(row.get('sourceLocator', {}).get('htmlAnchorOrdinal')) is int
                     and row['sourceLocator']['htmlAnchorOrdinal'] > 0
                     and isinstance(row.get('literalHref'), str)
                     and all(row.get(k) is False for k in
                             ('targetFetched', 'recipeBodyEstablished',
                              'certificateValidityEstablished')),
                     'metadata-catalogue-scope-invalid')
            _url(row.get('targetURL'))
            _require(urljoin(binding['sourceURL'], row['literalHref']) == row['targetURL'],
                     'metadata-link-resolution-mismatch')
        return [(r, f'/records/{i}') for i, r in enumerate(rows)]
    if binding['profile'] == 'ki-cpi-receipt':
        _require(value.get('country') == 'KI'
                 and value.get('canonical_url') == binding['sourceURL']
                 and value.get('version') == 'September2025'
                 and value.get('http_status') == 200
                 and value.get('dataset_acquired') is True
                 and all(k in value for k in KI_FIELDS),
                 'metadata-cpi-identity-mismatch')
        return [({k: value[k] for k in KI_FIELDS}, '')]
    raise RefreshError('metadata-profile-unsupported')


def _project(binding, value, policy_pin):
    selected = _select(binding, value)
    _require(type(binding['expectedRecords']) is int
             and 0 < len(selected) == binding['expectedRecords'] <= MAX_RECORDS,
             'metadata-count-mismatch')
    ids, records = set(), []
    for raw, selector in selected:
        identifier = raw.get('id')
        _require(isinstance(identifier, str) and identifier.strip() and identifier not in ids,
                 'metadata-id-duplicate-or-missing')
        ids.add(identifier)
        origins = {}
        for pointer in datum_pointers(raw, '/data/sourceRecord'):
            origins[pointer] = {
                'kind': 'source', 'sourceId': binding['sourceId'],
                'releaseId': binding['releaseId'], 'inputPath': binding['input']['path'],
                'inputSha256': binding['input']['sha256'], 'sourceRecordId': identifier,
                'sourceField': selector + pointer[len('/data/sourceRecord'):],
            }
        for name in ('nativeUnit', 'nativeBasis'):
            origins['/data/' + name] = {'kind': 'constant', 'policySha256': policy_pin,
                                        'symbol': 'metadata-does-not-establish-' + name}
        row = {'schemaVersion': 'offmenu-worker09-metadata-candidate/1',
               'kind': 'sourceMetadataReference',
               'id': binding['id'] + ':' + identifier, 'countries': [binding['country']],
               'provenance': {'sourceId': binding['sourceId'],
                              'releaseId': binding['releaseId'],
                              'fetchedAt': binding['originalAcquiredAt'],
                              'fieldOrigins': origins},
               'data': {'sourceRecord': raw, 'nativeUnit': None, 'nativeBasis': None}}
        errors = field_origin_errors(row,
                                     {binding['input']['path']: binding['input']['sha256']},
                                     policy_pins=(policy_pin,))
        _require(not errors, 'metadata-field-origin-invalid')
        records.append(row)
    return records


def diagnose(binding, metadata_root, *, now, validated_at, policy_pin):
    """One isolated diagnostic; held descriptors are returned before any file read.

    This API cannot grant source operations even if a caller supplies different
    descriptors. Only .json metadata pins and the two exact projections exist.
    """
    result = {'id': None, 'status': 'malformed-input', 'diagnostics': [], 'records': [],
              'nativeUnit': None, 'nativeBasis': None, 'sourceOperationsAuthorized': False,
              'countryComplete': False, 'goldAdmitted': False, 'networkRequests': 0,
              'metadataRecords': 0, 'sourceContentRecords': 0}
    try:
        _require(isinstance(binding, dict), 'metadata-binding-invalid')
        identifier = binding.get('id')
        _require(isinstance(identifier, str)
                 and bool(re.fullmatch('[a-z0-9-]{1,80}', identifier))
                 and binding.get('country') in COUNTRIES
                 and binding.get('state') in ('held', 'metadata'), 'metadata-binding-invalid')
        result['id'] = identifier
        result.update(country=binding['country'], domain=binding['domain'],
                      sourceId=binding['sourceId'], releaseId=binding['releaseId'],
                      scope='retained-metadata-reference-only')
        if binding['state'] == 'held':
            result.update(status='held-input', diagnostics=[binding['blocker']])
            return result
        _url(binding['sourceURL'])
        _require(binding.get('nativeUnit') is None and binding.get('nativeBasis') is None,
                 'metadata-quantity-inference-rejected')
        clock, validation = timestamp(now), timestamp(validated_at)
        acquired = timestamp(binding['originalAcquiredAt'])
        _require(acquired <= validation <= clock, 'metadata-clock-order-invalid')
        value = _load_pin(metadata_root, binding['input'])
        acquisition = _load_pin(metadata_root, binding['acquisitionEvidence'])
        _require(isinstance(acquisition, dict)
                 and acquisition.get('utc') == binding['originalAcquiredAt'],
                 'metadata-acquisition-evidence-mismatch')
        lineage = None
        if 'lineageEvidence' in binding:
            lineage = _load_pin(metadata_root, binding['lineageEvidence'])
            _require(isinstance(lineage, dict)
                     and lineage.get('candidate', {}).get('sha256') == binding['input']['sha256']
                     and lineage.get('source', {}).get('sha256') == binding['publisherBodySha256']
                     and lineage.get('passed') == binding['expectedRecords']
                     and lineage.get('failed') == 0, 'metadata-lineage-evidence-mismatch')
        age = (clock - acquired).total_seconds()
        result['cache'] = {'originalAcquiredAt': binding['originalAcquiredAt'],
                           'sharedPlanner': 'not-available-at-abec',
                           'scope': 'portfolio-metadata-age-diagnostic-only',
                           'validatedAt': validated_at, 'acquisitionAgeSeconds': age,
                           'validationAgeSeconds': (clock - validation).total_seconds(),
                           'minimumReuseDays': 30, 'mtimeUsed': False,
                           'revalidationResetsAcquisitionAge': False,
                           'retentionDays': binding.get('retentionDays'),
                           'retentionQualified': type(binding.get('retentionDays')) is int
                           and binding['retentionDays'] >= 30,
                           'decision': 'reuse-retained-metadata-no-download' if age < MIN_REUSE_SECONDS
                           else 'conditional-review-required-no-download'}
        if age >= MIN_REUSE_SECONDS:
            result.update(status='stale-input', diagnostics=['metadata-acquisition-stale'])
            return result
        result['records'] = _project(binding, value, policy_pin)
        result['metadataRecords'] = len(result['records'])
        result['status'] = 'metadata-candidate'
        if not result['cache']['retentionQualified']:
            result['diagnostics'].append('source-retention-duration-unqualified')
        result['useScope'] = binding['useScope']
        result['inputPins'] = [binding['input'], binding['acquisitionEvidence']]
        if lineage is not None:
            result['inputPins'].append(binding['lineageEvidence'])
            result['upstreamOriginEvidence'] = {
                'sourcePin': lineage['source'],
                'lineageReceipt': binding['lineageEvidence'],
                'selector': '/checks',
                'meaning': 'Prior source-anchor verification reused; original body not opened here.'}
    except RefreshError as error:
        code = str(error)
        result.update(status='missing-input' if code == 'metadata-input-missing'
                      else 'malformed-input', diagnostics=[code], records=[], metadataRecords=0)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        result.update(status='malformed-input', diagnostics=['metadata-binding-malformed'],
                      records=[], metadataRecords=0)
    except OSError:
        result.update(status='missing-input', diagnostics=['metadata-input-unreadable'],
                      records=[], metadataRecords=0)
    return result


def build(config, metadata_root, *, now, validated_at):
    """Pure metadata binding orchestration; no global registry or handlers changed."""
    _require(isinstance(config, dict)
             and config.get('schemaVersion') == 'offmenu-worker09-metadata-bindings/1'
             and isinstance(config.get('bindings'), list)
             and len(config['bindings']) <= 16, 'metadata-config-invalid')
    policy_pin = sha(canonical(config))
    ids, results = set(), []
    for index, binding in enumerate(config['bindings']):
        result = diagnose(binding, metadata_root, now=now,
                          validated_at=validated_at, policy_pin=policy_pin)
        result['bindingIndex'] = index
        if result['id'] is not None:
            if result['id'] in ids:
                result.update(status='malformed-input', diagnostics=['metadata-binding-id-duplicate'],
                              records=[], metadataRecords=0)
            ids.add(result['id'])
        raw = encode_records(result.pop('records'))
        if result['status'] == 'metadata-candidate':
            result.update(candidateBytes=raw, candidateSha256=sha(raw),
                          buildKey=sha(canonical({'policySha256': policy_pin,
                                                 'candidateSha256': sha(raw),
                                                 'inputs': result['inputPins']})))
        results.append(result)
    return {'schemaVersion': 'offmenu-worker09-staging-report/1',
            'policySha256': policy_pin, 'results': results,
            'stage': 'unreviewed-metadata-candidate', 'sourceBodyReads': 0,
            'networkRequests': 0, 'aiCalls': 0, 'countryCompletions': 0,
            'goldAdmitted': False, 'countries': config.get('countries', []),
            'requiredDomains': config.get('requiredDomains', []),
            'categoryAcceptance': 'not-established-for-any-country-domain'}


def _owned_regular(path):
    """Reject aliases/special files before any output-slot mutation."""
    path = safe_path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
             'metadata-output-file-unsafe')
    _require(info.st_uid == os.geteuid(), 'metadata-output-not-owned')


@contextmanager
def _output_lock(path):
    """Portfolio lock: validate its inode and NEVER write/truncate its contents.

    The shared writer_lock writes a PID and is not safe for an aliased input.
    Keep shared core unchanged; this boundary needs only an owned flock inode.
    """
    _owned_regular(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        opened, current = os.fstat(fd), path.lstat()
        _require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1,
                 'metadata-output-file-unsafe')
        _require(opened.st_uid == os.geteuid(), 'metadata-output-not-owned')
        _require((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino),
                 'metadata-output-lock-changed')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RefreshError('metadata-output-lock-held') from None
        yield
    finally:
        os.close(fd)


def publish_report(report, output):
    """Private candidate artifacts are immutable; identical content is a no-op.

    Only candidates referenced by this report are current. Old artifacts are
    preserved when a later diagnostic is held/stale/missing, never reactivated.
    """
    output = safe_path(output)
    if output.exists():
        _require(output.is_dir() and output.stat().st_uid == os.geteuid(),
                 'metadata-output-not-owned')
    output.mkdir(parents=True, exist_ok=True)
    slots = [output / name for name in ('.worker09.lock', 'report.json', 'report.json.pending')]
    slots += [output / (r['id'] + '-' + r['candidateSha256'] + '.jsonl')
              for r in report['results'] if 'candidateBytes' in r]
    for path in slots:
        _owned_regular(path)
    with _output_lock(output / '.worker09.lock'):
        for path in slots:
            _owned_regular(path)
        for result in report['results']:
            raw = result.pop('candidateBytes', None)
            if raw is None:
                continue
            name = result['id'] + '-' + result['candidateSha256'] + '.jsonl'
            path = safe_path(output / name)
            if path.exists():
                _require(path.read_bytes() == raw, 'metadata-existing-output-mismatch')
                action = 'no-op'
            else:
                with path.open('xb') as stream:
                    stream.write(raw)
                action = 'created'
            result.update(artifact=name, writeAction=action)
        atomic_json(output / 'report.json', report)
    return report


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--now', required=True, help='UTC evaluation time; never inferred from mtime')
    parser.add_argument('--validated-at', help='UTC validation observation; does not reset acquisition')
    args = parser.parse_args(argv)
    root, output = safe_path(args.metadata_root), safe_path(args.output)
    config = strict_json(CONFIG.read_bytes())
    # A root is only an explicit prefix for pinned JSON names; no inventory or
    # source path from inside an input document is followed.
    for b in config['bindings']:
        for key in ('input', 'acquisitionEvidence', 'evidence', 'lineageEvidence'):
            if key in b:
                p = safe_path(root / b[key]['path'])
                _require(not (output == p or output.is_relative_to(p.parent)),
                         'metadata-output-input-overlap')
    report = build(config, root, now=args.now, validated_at=args.validated_at or args.now)
    publish_report(report, output)
    print(canonical({k: v for k, v in report.items() if k != 'results'}).decode(), end='')
    return 0 if all(r['status'] in ('metadata-candidate', 'held-input')
                    for r in report['results']) else 2


def main(argv=None):
    try:
        return _main(argv)
    except RefreshError as error:
        code = str(error)
    except (KeyError, ValueError, TypeError, UnicodeError):
        code = 'metadata-cli-config-malformed'
    except OSError:
        code = 'metadata-cli-filesystem-unavailable'
    print(canonical({'status': 'failed', 'diagnostics': [code],
                     'sourceOperationsAuthorized': False,
                     'countryCompletions': 0}).decode(), file=sys.stderr, end='')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
