"""Worker 62's offline metadata bindings, never a PDF parser or admission.

The repository-owned configuration is the metadata read allowlist. Original asset
paths are documentary references only. No fetch, dynamic adapter, SourceContract
construction or acceptance is exposed here. Shared validators remain authoritative.
"""
import argparse
from enum import Enum
import os
from pathlib import Path
import re
import stat
import uuid

from .refresh.core import (RefreshError, canonical, safe_path, sha,
                           strict_json, timestamp)
from .refresh.field_provenance import datum_pointers, field_origin_errors
from .refresh.global_run import StageResult
from .refresh.serialization import encode_records

CONFIG = Path(__file__).resolve().parents[1] / 'docs/portfolios/worker62-inputs.json'
COUNTRIES = ('GR', 'OM', 'TT', 'ZA')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')
MAX_METADATA = 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')


class MetadataReadFailure(Enum):
    MISSING = 'metadata-missing'
    INVALID = 'metadata-file-invalid'


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_regular(path, limit):
    """Nonblocking open, then verify descriptor type/identity before any read."""
    path = safe_path(path)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise RefreshError('metadata-file-invalid')
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
            raise RefreshError('metadata-file-invalid')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        if _identity(os.fstat(fd)) != _identity(opened):
            raise RefreshError('metadata-file-invalid')
        return raw
    finally:
        os.close(fd)


def _output_target(directory_fd, name):
    try:
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RefreshError('output-target-not-owned-regular-file')
    return info


def _publish(output, candidate, report):
    """Preflight both names; bounded comparison and replace owned temp files.

    Never truncate an existing inode. Concurrent aliases inserted after preflight
    cannot redirect replacement writes into an external file.
    """
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    names = ('metadata-candidate.jsonl', 'metadata-report.json')
    temporary = []
    try:
        snapshots = {name: _output_target(directory_fd, name) for name in names}
        info = snapshots[names[0]]
        unchanged = False
        if info is not None and info.st_size == len(candidate):
            fd = os.open(names[0], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=directory_fd)
            try:
                opened = os.fstat(fd)
                if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                        or _identity(opened) != _identity(info)):
                    raise RefreshError('output-custody-changed')
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    previous = stream.read(len(candidate) + 1)
                if _identity(os.fstat(fd)) != _identity(opened):
                    raise RefreshError('output-custody-changed')
                if previous == candidate:
                    unchanged = True
            finally:
                os.close(fd)
        report['replay'] = 'no-op' if unchanged else 'metadata-build'
        pending = [(names[1], canonical(report))]
        if not unchanged:
            pending.insert(0, (names[0], candidate))
        for name, raw in pending:
            temp = '.worker62-' + uuid.uuid4().hex + '.tmp'
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=directory_fd)
            temporary.append((temp, name))
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        # No artifact is replaced if either target changed while preparing bytes.
        for name in names:
            current = _output_target(directory_fd, name)
            before = snapshots[name]
            if (None if current is None else _identity(current)) != (
                    None if before is None else _identity(before)):
                raise RefreshError('output-custody-changed')
        for temp, name in temporary:
            os.replace(temp, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        for temp, _ in temporary:
            try:
                os.unlink(temp, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        os.close(directory_fd)


def pointer(value, selector):
    """Resolve a literal RFC6901 coordinate; absent is not a null value."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise RefreshError('metadata-selector-invalid')
    for token in selector[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise RefreshError('metadata-selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise RefreshError('metadata-selector-missing')
            index = int(token)
            if index >= len(value):
                raise RefreshError('metadata-selector-missing')
            value = value[index]
        elif isinstance(value, dict) and token in value:
            value = value[token]
        else:
            raise RefreshError('metadata-selector-missing')
    return value


def _validate(config):
    if (not isinstance(config, dict) or config.get('schemaVersion') != 'worker62-metadata-bindings/1'
            or config.get('countries') != list(COUNTRIES)
            or not isinstance(config.get('metadata'), dict)
            or not 1 <= len(config['metadata']) <= 32
            or not isinstance(config.get('sources'), list)
            or not 1 <= len(config['sources']) <= 16):
        raise RefreshError('portfolio-config-invalid')
    for alias, pin in config['metadata'].items():
        if (not re.fullmatch(r'[a-z0-9-]+', alias)
                or not isinstance(pin, dict)
                or not isinstance(pin.get('sha256'), str)
                or not HEX.fullmatch(pin['sha256'])
                or type(pin.get('bytes')) is not int
                or not 0 < pin['bytes'] <= MAX_METADATA
                or not isinstance(pin.get('path'), str)
                or not Path(pin['path']).is_absolute()
                or not pin['path'].endswith('.json')):
            raise RefreshError('metadata-pin-invalid')
    ids = set()
    for source in config['sources']:
        if (not isinstance(source, dict) or not isinstance(source.get('sourceId'), str)
                or not source['sourceId'] or source['sourceId'] in ids
                or source.get('country') not in COUNTRIES
                or not isinstance(source.get('releaseId'), str) or not source['releaseId']
                or not isinstance(source.get('holds'), list)
                or any(not isinstance(x, str) or not x for x in source['holds'])
                or not isinstance(source.get('fields'), dict) or not source['fields']
                or not isinstance(source.get('unknowns'), dict)
                or set(source['fields']) & set(source['unknowns'])
                or any(not isinstance(v, str) or not v for v in source['unknowns'].values())
                or not isinstance(source.get('countryTypes'), list)
                or not source['countryTypes'] or not set(source['countryTypes']) <= set(TYPES)):
            raise RefreshError('source-binding-invalid')
        ids.add(source['sourceId'])
        for name, field in source['fields'].items():
            if (not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9]*', name)
                    or not isinstance(field, dict)
                    or field.get('metadata') not in config['metadata']
                    or not isinstance(field.get('selector'), str)):
                raise RefreshError('source-field-invalid')
        if any(not isinstance(k, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9]*', k)
               for k in source['unknowns']):
            raise RefreshError('source-field-invalid')


def bind(config, metadata, *, now, previous_key=None, validated_at=None):
    """Pure bounded binding; metadata bytes supplied by caller, no asset access.

    now is explicit. Validation time never changes acquisition age or content key.
    A 'valid' result means metadata binding only, not permitted body processing.
    """
    _validate(config)
    now = timestamp(now)
    if validated_at is not None and timestamp(validated_at) > now:
        raise RefreshError('validation-timestamp-in-future')
    policy_pin = sha(canonical(config))
    documents, input_errors = {}, {}
    for alias, pin in sorted(config['metadata'].items()):
        raw = metadata.get(alias)
        if isinstance(raw, MetadataReadFailure):
            input_errors[alias] = raw.value
        elif raw is None:
            input_errors[alias] = 'metadata-missing'
        elif not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
            input_errors[alias] = 'metadata-malformed'
        elif sha(raw) != pin['sha256'] or len(raw) != pin['bytes']:
            input_errors[alias] = 'metadata-stale-input'
        else:
            try:
                document = strict_json(raw)
                if not isinstance(document, dict):
                    raise RefreshError('metadata-object-required')
                # strict_json rejects NaN tokens, but an exponent can overflow
                # during JSON float decoding. Keep that failure local to its input.
                canonical(document)
                documents[alias] = document
            except (ValueError, UnicodeError, RecursionError):
                input_errors[alias] = 'metadata-malformed'
    records, outcomes = [], []
    for source in config['sources']:
        data, origins, pins, errors = {}, {}, {}, set()
        for name, field in source['fields'].items():
            alias, selector = field['metadata'], field['selector']
            if alias in input_errors:
                errors.add(input_errors[alias])
                continue
            try:
                value = pointer(documents[alias], selector)
            except RefreshError as error:
                errors.add(str(error))
                continue
            data[name] = value
            relative = f'metadata/{alias}.json'
            pins[relative] = config['metadata'][alias]['sha256']
            for target in datum_pointers(value, '/data/' + name):
                suffix = target[len('/data/' + name):]
                origins[target] = {'kind': 'source', 'sourceId': source['sourceId'],
                    'releaseId': source['releaseId'], 'inputPath': relative,
                    'inputSha256': pins[relative], 'sourceRecordId': alias,
                    'sourceField': selector + suffix}
        for name in source['unknowns']:
            data[name] = None
            origins['/data/' + name] = {'kind': 'constant', 'policySha256': policy_pin,
                                       'symbol': 'explicit-unknown:' + name}
        row = {'id': source['sourceId'], 'kind': 'source-input-metadata-reference',
            'schemaVersion': 1, 'data': data,
            'provenance': {'sourceId': source['sourceId'], 'releaseId': source['releaseId'],
                           'fetchedAt': data.get('originalAcquiredAt'),
                           'fieldOrigins': origins}}
        # No partial record is emitted after a missing, changed or malformed input.
        if not errors:
            errors.update(field_origin_errors(row, pins, policy_pins=(policy_pin,)))
        acquired = data.get('originalAcquiredAt')
        # Time annotations only. abec has no source-neutral pure cache planner.
        # Do not call the Wikibooks policy or operational CachedAcquirer here.
        cache = {'decision': 'unsupported-source-neutral-cache-planner',
                 'acquisitionAgeDays': None, 'underMinimumReuseWindow': None,
                 'timeEvidenceStatus': 'acquisition-time-unknown'}
        if acquired is not None:
            try:
                age = (now - timestamp(acquired)).total_seconds()
                if age < 0:
                    raise RefreshError('acquisition-timestamp-in-future')
                cache.update(acquisitionAgeDays=int(age // 86400),
                    underMinimumReuseWindow=age < 30 * 86400,
                    timeEvidenceStatus='recorded-receipt-utc')
            except (RefreshError, TypeError):
                errors.add('acquisition-timestamp-invalid')
        cache.update(minimumReuseDays=30, networkRequests=0,
            conditionalRefreshEligible=False, originalBytesVerified=False,
            validationAgeDays=None if validated_at is None else
                int((now - timestamp(validated_at)).total_seconds() // 86400))
        status = ('stale-input' if 'metadata-stale-input' in errors else
                  'malformed' if errors - {'metadata-missing', 'metadata-selector-missing'} else
                  'missing' if errors else 'held' if source['holds'] else 'valid')
        if not errors:
            records.append(row)
        stage = StageResult('failed' if errors else 'held' if source['holds'] else 'succeeded',
            code=sorted(errors)[0] if errors else 'source-body-held' if source['holds'] else 'metadata-only',
            evidence=(policy_pin,), observed_count=0 if errors else 1).receipt()
        outcomes.append({'sourceId': source['sourceId'], 'country': source['country'],
            'countryTypes': source['countryTypes'], 'applicability': 'reference-only-not-complete',
            'status': status, 'diagnostics': sorted(errors), 'holds': source['holds'],
            'unknowns': source['unknowns'], 'metadataStage': stage, 'cache': cache,
            'bodyProcessing': 'not-selected', 'acceptance': 'not-requested'})
    candidate = encode_records(records)
    key = sha(canonical({'policy': policy_pin, 'candidate': sha(candidate),
        'inputErrors': input_errors, 'outcomes': [
            [x['sourceId'], x['status'], x['diagnostics']] for x in outcomes]}))
    report = {'schemaVersion': 'worker62-metadata-result/1', 'contentKey': key,
        'replay': 'no-op' if previous_key == key else 'metadata-build',
        'metadataRecords': len(records), 'candidateSha256': sha(candidate),
        'outcomes': outcomes, 'countryRequirements': [
            {'country': c, 'dataType': t, 'accepted': False, 'status': 'not-qualified'}
            for c in COUNTRIES for t in TYPES], 'bodyOperations': 0,
        'acceptedDatasetRecords': 0, 'goldAdmissions': 0}
    return candidate, report


def load_metadata(config):
    """Read only repository-allowlisted JSON metadata, never original paths."""
    _validate(config)
    result = {}
    for alias, pin in config['metadata'].items():
        try:
            result[alias] = _read_regular(pin['path'], MAX_METADATA)
        except FileNotFoundError:
            result[alias] = MetadataReadFailure.MISSING
        except (OSError, RefreshError):
            # Missing/unavailable metadata is a per-source result, not a failed portfolio.
            result[alias] = MetadataReadFailure.INVALID
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC evaluation time')
    parser.add_argument('--validated-at', help='Prior validation UTC; not acquisition time')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    config = strict_json(CONFIG.read_bytes())
    candidate, report = bind(config, load_metadata(config), now=args.now,
                             validated_at=args.validated_at)
    _publish(args.output, candidate, report)
    print(canonical({'contentKey': report['contentKey'], 'replay': report['replay'],
                     'metadataRecords': report['metadataRecords'],
                     'bodyOperations': 0}).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
