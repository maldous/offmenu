"""BN/BI/BJ/BL retained-METADATA bindings; never a source-body adapter.

Only reviewed metadata files named by the portfolio profile are opened. Original
asset paths and source selectors are declarations, never followed. A valid result
means metadata shape/provenance only, not SourceContract qualification/admission.
"""
import argparse
import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timezone
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from .acquisition import MIN_TTL
from .core import (RefreshError, canonical, fsync_directory, safe_path,
                   sha, strict_json, timestamp, writer_lock)
from .field_provenance import datum_pointers, field_origin_errors
from .national_tabular import valid_input_name
from .serialization import encode_records
from .portfolio16_catalogue import CATALOGUE

MAX_METADATA = 4 * 1024 * 1024
COUNTRIES = frozenset(('BN', 'BI', 'BJ', 'BL'))


@dataclass(frozen=True)
class MetadataBinding:
    """Reviewed code/config input; contains no executable hooks or rights grant."""
    source_id: str
    country: str
    release_id: str
    metadata_path: str
    metadata_sha256: str
    metadata_bytes: int
    original_acquired_at: object
    last_validated_pointer: str
    selectors: dict
    declarations: dict
    holds: tuple
    evidence: dict
    expected_values: dict = field(default_factory=dict)


def pointer(document, selector):
    """RFC6901 string form, without URI fragments or inferred array aliases."""
    if not isinstance(selector, str) or (selector and not selector.startswith('/')):
        raise RefreshError('metadata-selector-invalid')
    value = document
    for raw in selector.split('/')[1:]:
        if re.search(r'~(?![01])', raw):
            raise RefreshError('metadata-selector-invalid')
        token = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', token):
            index = int(token)
            if index >= len(value):
                raise RefreshError('metadata-field-missing')
            value = value[index]
        else:
            raise RefreshError('metadata-field-missing')
    return value


def load_profile():
    """Copy the owned installed code catalogue; never read source metadata."""
    value = copy.deepcopy(CATALOGUE)
    if value.get('schema') != 'offmenu-portfolio16-metadata-bindings/1':
        raise RefreshError('portfolio-profile-invalid')
    bindings = tuple(MetadataBinding(**item) for item in value['bindings'])
    return bindings, sha(canonical(value))


def _check_binding(spec):
    if (spec.country not in COUNTRIES or not spec.source_id or not spec.release_id
            or not valid_input_name(spec.metadata_path)
            or not isinstance(spec.metadata_sha256, str)
            or not re.fullmatch('[0-9a-f]{64}', spec.metadata_sha256)
            or type(spec.metadata_bytes) is not int
            or not 0 < spec.metadata_bytes <= MAX_METADATA
            or not isinstance(spec.selectors, dict) or not spec.selectors
            or not isinstance(spec.declarations, dict)
            or set(spec.selectors) & set(spec.declarations)
            or any(not isinstance(k, str) or not k for k in
                   (*spec.selectors, *spec.declarations))
            or not isinstance(spec.holds, (tuple, list))
            or any(not isinstance(x, str) or not x for x in spec.holds)):
        raise RefreshError('portfolio-binding-invalid')


def _metadata_identity(value):
    return (value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


@contextmanager
def _metadata_bytes(path, expected):
    """Pin one bounded regular descriptor through the caller's consumption.

    A pathname check alone cannot make a subsequent blocking open safe. Open
    nonblocking/nofollow, compare the opened inode with the pre-open snapshot,
    and never reopen the pathname for digesting or parsing.
    """
    try:
        before = os.stat(path, follow_symlinks=False)
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise RefreshError('metadata-input-missing') from None
    except OSError:
        raise RefreshError('metadata-input-invalid') from None
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise RefreshError('regular-file-required')
        if _metadata_identity(before) != _metadata_identity(opened):
            raise RefreshError('metadata-input-changed')
        if not opened.st_size == expected['bytes'] <= MAX_METADATA:
            raise RefreshError('metadata-input-pin-mismatch')
        raw = stream.read(expected['bytes'] + 1)
        if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
            raise RefreshError('metadata-input-pin-mismatch')

        def unchanged():
            try:
                after = os.fstat(stream.fileno())
                current = os.stat(path, follow_symlinks=False)
            except OSError:
                raise RefreshError('metadata-input-changed') from None
            if (not stat.S_ISREG(current.st_mode)
                    or not _metadata_identity(opened) == _metadata_identity(after)
                    == _metadata_identity(current)):
                raise RefreshError('metadata-input-changed')

        unchanged()
        yield raw
        unchanged()


def bind_metadata(spec, metadata_root, *, now, policy_sha256):
    """Return one isolated result and optional METADATA candidate. No network.

    The caller supplies a reviewed MetadataBinding, not source permission. Holds
    are additive diagnostics. Validation time cannot renew original acquisition.
    Original source bodies/retained staged food rows are never opened here.
    """
    result = {'sourceId': spec.source_id, 'country': spec.country,
              'releaseId': spec.release_id, 'status': 'malformed', 'errors': [],
              'metadataCandidate': None, 'originalAcquiredAt': spec.original_acquired_at,
              'lastValidatedAt': None, 'acquisitionAgeDays': None,
              'validationAgeDays': None, 'cacheDecision': 'unavailable',
              'minimumReuseDays': MIN_TTL // 86400,
              'sharedPureCachePlanner': 'absent-at-abecb99',
              'realSourceRefreshCapability': 'unsupported-no-reviewed-source-binding',
              'ageCalculationScope': 'metadata-age-diagnostic-and-intent-only',
              'sourceOperationsEnabled': False, 'datasetAccepted': False,
              'countryComplete': False, 'networkRequests': 0}
    errors = set()
    try:
        _check_binding(spec)
        if not re.fullmatch('[0-9a-f]{64}', policy_sha256):
            raise RefreshError('portfolio-policy-pin-invalid')
        clock = timestamp(now).astimezone(timezone.utc)
        if spec.holds:
            errors.add('source-held')
        if spec.original_acquired_at is None:
            errors.add('original-acquisition-time-missing')
        else:
            acquired = timestamp(spec.original_acquired_at)
            age = (clock - acquired).total_seconds()
            if age < 0:
                raise RefreshError('acquisition-timestamp-in-future')
            result['acquisitionAgeDays'] = int(age // 86400)
            if age < MIN_TTL:
                result['cacheDecision'] = 'reuse-retained-metadata-zero-download'
            else:
                result['cacheDecision'] = 'conditional-review-only-no-download'
                errors.add('input-stale')
        path = safe_path(safe_path(metadata_root) / spec.metadata_path)
        expected = {'bytes': spec.metadata_bytes, 'sha256': spec.metadata_sha256}
        with _metadata_bytes(path, expected) as raw:
            document = strict_json(raw)
            canonical(document)  # Also rejects overflowed JSON numeric values.
            if not isinstance(document, dict):
                raise RefreshError('metadata-object-required')
            validated = pointer(document, spec.last_validated_pointer)
            validated_stamp = timestamp(validated)
            if validated_stamp > clock:
                raise RefreshError('validation-timestamp-in-future')
            if spec.original_acquired_at is not None and validated_stamp < acquired:
                raise RefreshError('validation-before-acquisition')
            result['lastValidatedAt'] = validated
            result['validationAgeDays'] = int((clock - validated_stamp).total_seconds() // 86400)
            data, origins = {}, {}
            for name, selector in sorted(spec.selectors.items()):
                data[name] = copy.deepcopy(pointer(document, selector))
                # Selectors are restricted to scalar metadata declarations here.
                if isinstance(data[name], (dict, list)):
                    raise RefreshError('metadata-scalar-required')
                target = '/data/' + name.replace('~', '~0').replace('/', '~1')
                origins[target] = {'kind': 'source', 'sourceId': spec.source_id,
                    'releaseId': spec.release_id, 'inputPath': spec.metadata_path,
                    'inputSha256': spec.metadata_sha256,
                    'sourceRecordId': spec.source_id + ':retained-metadata',
                    'sourceField': selector}
            for name, value in sorted(spec.declarations.items()):
                data[name] = copy.deepcopy(value)
                for target in datum_pointers(value, '/data/' + name.replace('~', '~0').replace('/', '~1')):
                    origins[target] = {'kind': 'constant', 'policySha256': policy_sha256,
                                       'symbol': 'reviewed-metadata-declaration:' + name}
            if any(name not in data or type(data[name]) is not type(value) or data[name] != value
                   for name, value in spec.expected_values.items()):
                raise RefreshError('metadata-semantic-mismatch')
            row = {'id': spec.source_id + ':metadata-binding',
                   'kind': 'source-input-metadata-binding', 'schemaVersion': '1.0',
                   'data': data, 'provenance': {'sourceId': spec.source_id,
                       'releaseId': spec.release_id,
                       'fetchedAt': spec.original_acquired_at,
                       'fieldOrigins': origins}}
            errors.update(field_origin_errors(row, {spec.metadata_path: spec.metadata_sha256},
                                               policy_pins=(policy_sha256,)))
        result['metadataCandidate'] = row
    except FileNotFoundError:
        errors.add('metadata-input-missing')
    except RefreshError as error:
        errors.add(str(error))  # Shared helpers use fixed, non-source error codes.
    except (ValueError, TypeError, OSError, OverflowError, KeyError, RecursionError):
        errors.add('metadata-malformed')
    result['errors'] = sorted(errors)
    malformed = errors - {'source-held', 'input-stale', 'metadata-input-missing',
                          'metadata-field-missing', 'original-acquisition-time-missing'}
    result['status'] = ('malformed' if malformed else 'held' if 'source-held' in errors
        else 'missing' if errors & {'metadata-input-missing', 'metadata-field-missing',
                                   'original-acquisition-time-missing'}
        else 'stale' if 'input-stale' in errors else 'valid-metadata-only')
    if result['status'] in ('missing', 'malformed'):
        result['metadataCandidate'] = None
    result['holds'] = list(spec.holds)
    result['evidenceDeclarations'] = copy.deepcopy(spec.evidence)
    return result


def run_bindings(bindings, metadata_root, *, now, policy_sha256):
    """A source failure never suppresses another selected metadata result."""
    bindings = tuple(bindings)
    if not 0 < len(bindings) <= 128 or len({s.source_id for s in bindings}) != len(bindings):
        raise RefreshError('portfolio-binding-inventory-invalid')
    results = [bind_metadata(s, metadata_root, now=now, policy_sha256=policy_sha256)
               for s in sorted(bindings, key=lambda s: s.source_id)]
    rows = [x['metadataCandidate'] for x in results if x['metadataCandidate'] is not None]
    content = encode_records(rows)
    return {'schema': 'offmenu-portfolio16-metadata-report/1', 'results': results,
            'countryTypeApplicability': {s.country: copy.deepcopy(s.evidence.get('countryTypeApplicability', {}))
                                         for s in sorted(bindings, key=lambda s: s.source_id)},
            'candidateSha256': sha(content), 'candidateBytes': len(content),
            'metadataCandidates': len(rows), 'datasetRowsAccepted': 0,
            'sourceOperationsEnabled': False, 'networkRequests': 0,
            'countryComplete': False, 'policySha256': policy_sha256}, content


def publish(report, content, output):
    """Content-equal files are untouched; no mutable accepted-source pointer.

    Each file replacement is atomic. This is not a transactional multi-file
    acceptance protocol. Consumers must check candidateSha256 in the report.
    """
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=True)
    changed = []
    with writer_lock(output / '.portfolio16.lock'):
        for name, raw in [('metadata-candidate.jsonl', content),
                          ('binding-report.json', canonical(report))]:
            path = safe_path(output / name)
            if path.exists() and path.read_bytes() == raw:
                continue
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=output, prefix='.portfolio16-', delete=False) as f:
                    temporary = Path(f.name)
                    f.write(raw)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, path)
                fsync_directory(output)
                changed.append(name)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    return {'status': 'written' if changed else 'no-op', 'changedFiles': changed,
            'datasetAccepted': False, 'networkRequests': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--now', required=True, help='Explicit UTC clock; never filesystem mtime')
    args = parser.parse_args()
    metadata_root, output = safe_path(args.metadata_root), safe_path(args.output)
    if output == metadata_root or metadata_root in output.parents:
        raise RefreshError('metadata-output-overlaps-input-root')
    bindings, policy = load_profile()
    report, content = run_bindings(bindings, metadata_root, now=args.now, policy_sha256=policy)
    print(json.dumps(publish(report, content, output), sort_keys=True))


if __name__ == '__main__':
    main()
