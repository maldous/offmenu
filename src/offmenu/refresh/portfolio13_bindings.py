"""Offline metadata bindings for MQ/MR/MS/MT; no dataset handlers or admissions.

Binding objects are reviewed Python configuration, never loaded from receipts or
CLI input. Only their exact JSON metadata file is read. Referenced body paths,
URLs and scripts are documentary values and are never dereferenced.
"""
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import stat

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp, verify_source
from .field_provenance import datum_pointers, field_origin_errors
from .global_run import CODE, StageResult, stream_report, write_report
from .national_tabular import valid_input_name

MAX_METADATA = 2 * 1024 * 1024


def _read_regular(path):
    """Read bounded bytes from one no-follow, nonblocking regular descriptor.

    Walk ancestors by directory descriptor too: replacing a checked path with
    a symlink cannot redirect a later open. Never reopen after verification.
    """
    path = safe_path(path)
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    descriptor = None
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                            | os.O_NONBLOCK, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('metadata-input-nonregular')
        if before.st_size > MAX_METADATA:
            raise RefreshError('metadata-input-too-large')
        blocks, consumed = [], 0
        while consumed <= MAX_METADATA:
            block = os.read(descriptor, min(65536, MAX_METADATA + 1 - consumed))
            if not block:
                break
            blocks.append(block)
            consumed += len(block)
        if consumed > MAX_METADATA:
            raise RefreshError('metadata-input-too-large')
        fields = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size,
                            s.st_mtime_ns, s.st_ctime_ns)
        current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if fields(before) != fields(os.fstat(descriptor)) or fields(before) != fields(current):
            raise RefreshError('metadata-input-changed')
        return b''.join(blocks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


@dataclass(frozen=True)
class SourceBinding:
    source_id: str
    country: str
    data_types: tuple
    release_id: str
    metadata_path: str
    metadata_bytes: int
    metadata_sha256: str
    release_pointer: str
    fields: tuple  # (output metadata field, exact RFC6901 receipt pointer)
    unknowns: tuple
    holds: tuple
    acquired_pointer: str | None = None
    fixture: bool = False


_ROOT = 'src/offmenu-data/originals/country-followthrough-20261015/'
_ORIGINAL = (('recordedBodySha256', '/requests/0/sha256'),
             ('recordedBodyBytes', '/requests/0/bytes'))
BINDINGS = (
    SourceBinding('mq-agreste-catalogue', 'MQ', ('retailers/providers',),
        'snapshot-20261015; publisher release version pending',
        _ROOT + 'owner-45/MQ/cff9ad550c549bc1187c/receipt.json', 5312,
        'd8225516cddd5799be5f895fe2acb10a6ca093af2cd4fe28058005570fe5a7b9', '/version',
        (('sourceLabel', '/title'), ('releaseLabel', '/version')) + _ORIGINAL,
        ('complete-original', 'mq-row-selector', 'native-unit', 'basis', 'original-acquired-at'),
        ('upstream-certificate-no-retry', 'source-custodian-unestablished', 'catalogue-only')),
    SourceBinding('mr-fews-retained', 'MR', ('prices/baskets',),
        'FEWS NET collected MR weekly complete filtered export snapshot 2026-10-15',
        _ROOT + 'owner-46/MR/b3eb74127e8d4d7eb747087b/receipt.json', 2990,
        'c807636a72e3931dd2256b00b9ba5d130a9c28542738d558ba25b79dfc7aecae', '/version',
        (('releaseLabel', '/version'), ('recordedBodySha256', '/sha256'),
         ('recordedBodyBytes', '/bytes'), ('headers', '/finite_original_verified/headers'),
         ('recordedPeriod', '/finite_original_verified/date_range'), ('attribution', '/rights/attribution')),
        ('denomination-rescaling', 'package-value-basis', 'unit-conversions', 'original-acquired-at'),
        ('source-custodian-unestablished', 'denomination-package-unresolved', 'no-body-operation-selected')),
    SourceBinding('ms-sdm-index', 'MS', ('prices/baskets',),
        'MontserratSDM-datatable-index2026-10-15',
        _ROOT + 'owner-47/MS/6a66d6839b975411c465/receipt.json', 1753,
        'c4f9bc709bec0b6ccc912c6e9754bef776fe3b4eb47182cb095e85982aa8d534',
        '/requests/0/claimedVersion',
        (('releaseLabel', '/requests/0/claimedVersion'), ('recordedBodySha256', '/requests/0/sha256'),
         ('recordedBodyBytes', '/requests/0/bodyBytes'), ('requestCaptureAt', '/requests/0/requestUTC')),
        ('workbook-manifest', 'sheet-range', 'index-base', 'month-extent', 'source-use', 'original-acquired-at'),
        ('source-custodian-unestablished', 'index-not-table', 'no-body-operation-selected')),
    SourceBinding('mt-kusksu-page', 'MT', ('ingredients', 'recipes'),
        '12 May 2025 recipe of the month',
        _ROOT + 'owner-48/MT/9db5099a5d1ae42b1585/receipt.json', 2732,
        '1216ec1d49aab4474c4dfd74e61b7898384c5147411acb8cbc8aece6b0566837', '/version_proposed',
        (('releaseLabel', '/version_proposed'), ('recordedBodySha256', '/artefacts/0/sha256'),
         ('recordedBodyBytes', '/artefacts/0/bytes'), ('sourceScope', '/scope')),
        ('yield-servings', 'derivative-use', 'ingredient-identity', 'basis', 'original-acquired-at'),
        ('taste-credit-use-unresolved', 'booklet-403-no-retry', 'thesis-restricted', 'no-body-operation-selected')),
)


def _pointer(value, pointer):
    if pointer == '':
        return value
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise RefreshError('metadata-selector-malformed')
    for token in pointer[1:].split('/'):
        # Reject malformed escapes rather than silently using a different key.
        if '~' in token.replace('~0', '').replace('~1', ''):
            raise RefreshError('metadata-selector-malformed')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not token.isascii() or not token.isdigit() or str(int(token)) != token:
                raise RefreshError('metadata-selector-malformed')
            value = value[int(token)]
        else:
            value = value[token]
    return value


def bind_metadata(binding, metadata_root, *, now):
    """Return a private metadata artifact and isolated typed diagnostic report.

No permission is derived from a pin. Real bindings retain explicit holds. A
successful fixture proves metadata linkage only, never accepted source data.
Capture/request timestamps are not silently relabelled original acquisition.
"""
    codes, data, origins = set(), {}, {}
    acquired = None
    artifact = None
    cache = {'originalAcquiredAt': None, 'validatedAt': now.isoformat(),
             'minimumReuseSeconds': MIN_TTL, 'decision': 'acquisition-time-unknown',
             'mtimeUsed': False, 'validationResetsAcquisition': False, 'networkRequests': 0}
    try:
        timestamp(now.isoformat())
        if (not isinstance(binding.source_id, str) or not CODE.fullmatch(binding.source_id)
                or binding.country not in ('MQ', 'MR', 'MS', 'MT')
                or not valid_input_name(binding.metadata_path) or not binding.metadata_path.endswith('.json')
                or type(binding.metadata_bytes) is not int or not 0 < binding.metadata_bytes <= MAX_METADATA):
            raise RefreshError('metadata-contract-malformed')
        raw = _read_regular(Path(metadata_root) / binding.metadata_path)
        verify_source(raw, {'bytes': binding.metadata_bytes, 'sha256': binding.metadata_sha256})
        receipt = strict_json(raw)
        if not isinstance(receipt, dict):
            raise RefreshError('metadata-object-required')
        if receipt.get('country') != binding.country or _pointer(receipt, binding.release_pointer) != binding.release_id:
            raise RefreshError('metadata-source-release-mismatch')
        for name, selector in binding.fields:
            value = _pointer(receipt, selector)
            data[name] = value
            for suffix in datum_pointers(value, ''):
                key = name.replace('~', '~0').replace('/', '~1')
                origins['/data/' + key + suffix] = {
                    'kind': 'source', 'sourceId': binding.source_id, 'releaseId': binding.release_id,
                    'inputPath': binding.metadata_path, 'inputSha256': binding.metadata_sha256,
                    'sourceRecordId': 'receipt:' + binding.metadata_sha256, 'sourceField': selector + suffix}
        if binding.acquired_pointer is not None:
            acquired = timestamp(_pointer(receipt, binding.acquired_pointer))
            age = (now - acquired).total_seconds()
            if age < 0:
                raise RefreshError('metadata-acquisition-in-future')
            cache.update(originalAcquiredAt=acquired.isoformat(),
                         decision='reuse' if age < MIN_TTL else 'stale-input')
            if age >= MIN_TTL:
                codes.add('metadata-cache-stale')
        else:
            codes.add('metadata-acquisition-time-missing')
        artifact = {'id': binding.source_id, 'kind': 'source-input-binding', 'schemaVersion': 'portfolio13-metadata/1',
                    'provenance': {'sourceId': binding.source_id, 'releaseId': binding.release_id,
                                   'fieldOrigins': origins, 'inputRole': 'receipt-metadata-not-body'},
                    'data': data, 'countries': [binding.country], 'dataTypes': list(binding.data_types),
                    'unknowns': list(binding.unknowns), 'scope': 'authored-fixture' if binding.fixture else 'retained-metadata-only',
                    'sourceBodyOperationPermitted': False, 'countryComplete': False, 'goldAdmission': False}
        codes.update(field_origin_errors(artifact, {binding.metadata_path: binding.metadata_sha256}))
    except FileNotFoundError:
        codes.add('metadata-input-missing')
    except (KeyError, IndexError):
        codes.add('metadata-field-missing')
    except RefreshError as error:
        codes.add(str(error))  # Shared helpers expose fixed codes, never values.
    except (ValueError, TypeError, UnicodeError, OSError, OverflowError, RecursionError):
        codes.add('metadata-input-malformed')
    if binding.holds:
        outcome, stage = 'held', StageResult('held', 'portfolio-source-held')
    elif not codes:
        outcome, stage = 'valid', StageResult('succeeded', evidence=(sha(canonical(artifact)),), observed_count=0)
    elif codes == {'metadata-cache-stale'}:
        outcome, stage = 'stale-input', StageResult('unsupported', 'metadata-cache-stale')
    elif codes <= {'metadata-input-missing', 'metadata-field-missing', 'metadata-acquisition-time-missing'}:
        outcome, stage = 'missing', StageResult('unsupported', 'metadata-input-incomplete')
    else:
        outcome, stage = 'malformed', StageResult('failed', 'metadata-contract-invalid')
    report = {'sourceId': binding.source_id, 'country': binding.country, 'outcome': outcome,
              'diagnostics': sorted(codes), 'holds': list(binding.holds), 'cache': cache,
              'stage': stage.receipt(), 'bindingSha256': sha(canonical(artifact)) if artifact else None,
              'acceptedSourceRecords': None, 'publication': 'not-written'}
    return report, artifact if outcome == 'valid' else None


def run(metadata_root, *, now, output=None, bindings=BINDINGS):
    """Independent per-binding outcomes; optional deterministic metadata replay.

The generic atomic exclusive report writer publishes metadata only. Identical
bytes are a no-op; a different existing artifact is never overwritten. No
network transport, body parser, dynamic handler or production admission exists.
"""
    reports = []
    for binding in bindings:
        report, artifact = bind_metadata(binding, metadata_root, now=now)
        if artifact is not None and output is not None:
            try:
                directory = safe_path(output)
                directory.mkdir(parents=True, exist_ok=True)
                target = safe_path(directory / (binding.source_id + '.json'))
                # Use the shared writer's serialization, including Unicode
                # escaping, rather than a second locally chosen encoding.
                expected, _ = stream_report(artifact)
                if target.exists():
                    existing = _read_regular(target)
                    if sha(existing) != expected:
                        raise RefreshError('metadata-output-conflict')
                    report['publication'] = 'no-op'
                else:
                    write_report(artifact, target)
                    report['publication'] = 'created'
            except (OSError, ValueError):
                report.update(outcome='malformed', publication='not-written')
                report['diagnostics'] = sorted(set(report['diagnostics']) | {'metadata-output-conflict'})
                report['stage'] = StageResult('failed', 'metadata-output-conflict').receipt()
        reports.append(report)
    return {'schemaVersion': 'portfolio13-binding-report/1', 'sources': reports,
            'networkRequests': 0, 'sourceBodyReads': 0, 'goldAdmissions': 0, 'countryCompletions': 0}


def verification_handler(binding, metadata_root, *, clock):
    """Existing StageContext -> StageResult interface, metadata verification only.

Caller owns the resource boundary and independent review/registration. This
does not install a GLOBAL Binding, an Admission or acquire/parse handlers.
"""
    def verify(context):
        if context.source_id != binding.source_id or context.stage != 'verify':
            return StageResult('failed', 'metadata-stage-context-mismatch')
        report, _ = bind_metadata(binding, metadata_root, now=clock())
        stage = report['stage']
        return StageResult(stage['status'], stage['code'], tuple(stage['evidence']), stage['observedCount'])
    return verify


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline MQ/MR/MS/MT receipt metadata only; never source bodies.')
    parser.add_argument('--metadata-root', type=Path)
    parser.add_argument('--now', help='UTC observation timestamp; never acquisition time')
    parser.add_argument('--output', type=Path, help='Private metadata artifact directory; existing differing bytes refused')
    parser.add_argument('--describe', action='store_true')
    args = parser.parse_args(argv)
    if args.describe:
        print(canonical([asdict(b) for b in BINDINGS]).decode(), end='')
        return 0
    if args.metadata_root is None:
        parser.error('--metadata-root required')
    try:
        now = timestamp(args.now) if args.now else datetime.now(timezone.utc)
        result = run(args.metadata_root, now=now, output=args.output)
    except (ValueError, TypeError):
        print(canonical({'errorCode': 'metadata-clock-invalid'}).decode(), end='')
        return 2
    print(canonical(result).decode(), end='')
    return 0 if all(r['outcome'] == 'valid' for r in result['sources']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
