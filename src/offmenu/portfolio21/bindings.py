"""Pinned MD/SJ/TD/UM metadata audit using shared staging contracts.

This module reads only the declared JSON metadata, never follows receipt paths,
never imports handlers from metadata, and never grants source permissions.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import os
import re
import stat
from pathlib import PurePosixPath

from offmenu.refresh.core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from offmenu.refresh.global_run import StageResult
from offmenu.refresh.product_adapters import MIN_CACHE_SECONDS
from offmenu.refresh.product_qualification import qualify_product_candidate

MAX_METADATA_BYTES = 1024 * 1024
BASE = 'abecb99ee1125730ccbc2824b6ec49ffc5cc4302'
TD_PREFIX = 'originals/country-followthrough-20261015/owner-21/TD/'


@dataclass(frozen=True)
class MetadataBinding:
    key: str
    country: str
    path: str
    pin: str
    classification: str
    selectors: tuple
    holds: tuple
    expected: tuple = ()


# Exact JSON pointers refer to retained metadata assertions, not source cells.
# Missing pointers remain missing: public access and a licence label grant nothing.
BINDINGS = (
    MetadataBinding('md-prices', 'MD', 'prices-2026-10-12/manifest.json',
        'a2b5502bcaad9489d9fef02c105f5656666d87f4765fc31c762c72a8028a48e5',
        'normalized-manifest-only',
        ('/sourceId', '/releaseId', '/license', '/attribution', '/scope', '/countries/MD', '/completedAt', '/acquiredAt'),
        ('original-acquisition-time-missing', 'raw-input-role-contract-missing', 'rights-scope-custody-review-required'),
        (('/sourceId', 'prices'), ('/releaseId', '2026-10-12'))),
    MetadataBinding('sj-ssb', 'SJ',
        'originals/country-acquisition-20261015/source-queue/owner-38/56443662b46fabfe9315/receipt.json',
        '745204f6e29cc1ee808897373c41c10e7368a31fa5186f83ff2f6eb4323eed5d',
        'metadata-only-no-original',
        ('/release', '/licence/acquisition', '/licence/redistribution', '/full_release_obtained', '/new_response_bytes'),
        ('exact-release-and-asset-missing', 'source-use-grant-missing', 'sj-applicability-review-required')),
    MetadataBinding('td-js-route', 'TD', TD_PREFIX + '192e6db8a8e35677d60a/receipt.json',
        '5c2737441fae9d8c8fb061bbd186d43f21a710710c83d7ce7ccf36107f4000d5',
        'metadata-route-only', ('/version', '/licence', '/rights', '/status'),
        ('original-dataset-missing', 'source-use-review-required')),
    MetadataBinding('td-package-rights', 'TD', TD_PREFIX + '30e4af2f7b78e81af9e9/receipt.json',
        'a9bec2c84ff5cb534fc15c2065332d3e9c7d93604a9c16e194a98b102241a386',
        'package-metadata-not-price-rows', ('/version', '/licence', '/rights', '/status'),
        ('exact-rights-intended-use-attribution-unresolved',)),
    MetadataBinding('td-inseed', 'TD', TD_PREFIX + '83683ca40b881efb6214/receipt.json',
        'a80539f40e62ca0de114e660b029f9fb3cd7b9d5c20b148a31f89b6a66953cdb',
        'html-response-not-advertised-pdf', ('/version', '/licence', '/rights', '/status'),
        ('original-dataset-missing', 'source-use-review-required')),
    MetadataBinding('td-markets', 'TD', TD_PREFIX + '83f3a08b8b6a45726bef/receipt.json',
        '2c0f1d625aed36526f671ef2ad5fac3701c7b1fbd92164044827cc1849eb0f02',
        'receipt-claims-complete-original-unparsed',
        ('/version', '/licence', '/rights_evidence', '/extent', '/row_count_excluding_header_and_HXL',
         '/advertised_bytes', '/source_admission', '/intended_use', '/attribution'),
        ('rights-evidence-unqualified', 'body-read-not-authorized', 'body-schema-and-field-origins-missing'),
        (('/version', 'WFP Chad Markets2026-09-06T21:46:46.658622'),)),
    MetadataBinding('td-menu-api', 'TD', TD_PREFIX + '9b0c09c7e721d2a1dfd1/receipt.json',
        '075e9b2b9aff04a6b3f1e8af747af52194ffedd86e47a516892c6a85523468ec',
        'menu-metadata-not-corpus', ('/version', '/licence', '/rights', '/status'),
        ('original-dataset-missing', 'source-use-review-required')),
    MetadataBinding('td-prices', 'TD', TD_PREFIX + 'c1d68ebfeab158fe624a/receipt.json',
        '3bef831b327ca72ef3d8d9b9dd0dc05e0fdc188103a6ee83964ec53a44b92638',
        'receipt-claims-complete-original-unparsed',
        ('/version', '/licence', '/rights_evidence', '/extent', '/row_count_excluding_header_and_HXL',
         '/advertised_bytes', '/source_admission', '/intended_use', '/attribution'),
        ('rights-evidence-unqualified', 'body-read-not-authorized', 'body-schema-and-field-origins-missing'),
        (('/version', 'WFP Chad Food Prices2026-10-11T20:52:48.633219'),)),
    MetadataBinding('um-dla', 'UM',
        'originals/country-followthrough-20261015/owner-45/UM/7e2e9784cba94bbe8cc6/receipt.json',
        'dbe5e3e6b11473fc5315284f379023fc43285a8e3cc6ec9abe5300d051e2c652',
        'failed-response-not-dataset',
        ('/version', '/rights', '/status', '/sourceRecordsAcquired', '/requests/0/status', '/requests/0/bytes'),
        ('access-denied-no-retry', 'source-use-unverified', 'um-applicability-missing')),
)

# Prospective Prices selectors match the shared product adapter, not the four
# retained MD observations' missing source cells. No package or basis inference.
PRICE_SELECTORS = {
    '/data/amount': ('prices', '/price', 'numeric-preserve-lexical'),
    '/data/sourceAmount': ('prices', '/price', 'identity'),
    '/data/currency': ('prices', '/currency', 'identity'),
    '/data/observedAt': ('prices', '/date', 'identity'),
    '/data/unitPrice': ('prices', '/price_per_unit', 'numeric-or-null'),
    '/data/sourceUnitPrice': ('prices', '/price_per_unit', 'identity-or-null'),
    '/data/unit': ('prices', '/price_per', 'identity-or-null'),
    '/data/regularAmount': ('prices', '/price_without_discount', 'numeric-or-null'),
    '/data/sourceRegularAmount': ('prices', '/price_without_discount', 'identity-or-null'),
    '/data/promotion': ('prices', '/price_is_discounted', 'boolean-or-null'),
    '/data/proofId': ('prices', '/proof_id', 'identity-or-null'),
    '/data/duplicateOf': ('prices', '/duplicate_of', 'identity-or-null'),
    '/data/identifiers/0/system': ('policy', 'barcode', 'constant'),
    '/data/identifiers/0/value': ('prices', '/product_code', 'string-if-present'),
    '/data/retailer/externalId': ('prices', '/location_id', 'string-or-empty'),
    '/data/retailer/location': ('locations', '/osm_display_name', 'join-price-location-id'),
    '/data/availability': ('policy', 'unknown', 'constant'),
    '/data/priceType': ('policy', 'dated-observation', 'constant'),
    '/data/retailer/name': ('locations', '/osm_name', 'join-price-location-id'),
}


def pointer(value, selector):
    """Resolve RFC6901 coordinates; missing and explicit null stay distinct."""
    if not isinstance(selector, str) or (selector and not selector.startswith('/')):
        return {'present': False}
    if selector == '':
        return {'present': True, 'value': value}
    try:
        for token in selector.split('/')[1:]:
            if re.search(r'~(?![01])', token):
                return {'present': False}
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not re.fullmatch(r'0|[1-9][0-9]*', token):
                    return {'present': False}
                value = value[int(token)]
            else:
                value = value[token]
        return {'present': True, 'value': value}
    except (KeyError, IndexError, TypeError, ValueError):
        return {'present': False}


@contextmanager
def _regular_fd(path, flags):
    """Open each component without following links; reject FIFOs before I/O.

    Directory descriptors pin traversal even when a path component is renamed.
    O_NONBLOCK also prevents a FIFO substitution from hanging before fstat.
    Every acquired descriptor is closed on every success/error path.
    """
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    fd = None
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                            | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(path.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     0o600, dir_fd=directory)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RefreshError('portfolio-file-not-regular')
        yield fd, directory, path.name
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_regular(path, budget, *, limit_code):
    with _regular_fd(path, os.O_RDONLY) as (fd, directory, name):
        before = os.fstat(fd)
        if before.st_size > MAX_METADATA_BYTES - budget[0]:
            raise RefreshError(limit_code)
        chunks, left = [], before.st_size
        while left:
            block = os.read(fd, min(left, 65536))
            if not block:
                raise RefreshError('portfolio-file-changed')
            budget[0] += len(block)  # Count reads even when later race checks fail.
            chunks.append(block)
            left -= len(block)
        after = os.fstat(fd)
        entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (not stat.S_ISREG(entry.st_mode) or _identity(before) != _identity(after)
                or _identity(after) != _identity(entry)):
            raise RefreshError('portfolio-file-changed')
        return b''.join(chunks)


def reuse_plan(acquired_at, validated_at, as_of):
    """No fetch decision: validation never resets acquisition or authorizes refresh."""
    now = timestamp(as_of)
    validated = timestamp(validated_at) if validated_at is not None else None
    acquired = timestamp(acquired_at) if acquired_at is not None else None
    if any(value > now for value in (acquired, validated) if value is not None):
        raise RefreshError('portfolio-clock-in-future')
    if acquired is not None and validated is not None and validated < acquired:
        raise RefreshError('portfolio-validation-before-acquisition')
    age = (now - acquired).total_seconds() if acquired is not None else None
    return {'originalAcquiredAt': acquired_at, 'validatedAt': validated_at,
            'acquisitionAgeSeconds': age,
            'validationAgeSeconds': (now - validated).total_seconds() if validated else None,
            'minimumReuseSeconds': MIN_CACHE_SECONDS,
            'withinMinimumReuseWindow': age < MIN_CACHE_SECONDS if age is not None else None,
            'decision': 'reuse-pinned-cache-no-fetch' if age is not None else 'acquisition-time-required',
            'refreshAuthorization': False, 'networkRequests': 0}


def audit_metadata(root, *, as_of, bindings=BINDINGS):
    """Isolated missing/malformed/stale/held results; pin/budget failure stops run.

    bindings is a trusted-code argument for authored fixtures, never a CLI input.
    A receipt's original_path/requests/rights links are not opened or hashed.
    """
    timestamp(as_of)
    root = safe_path(root)
    budget, rows = [0], []
    for binding in bindings:
        relative = PurePosixPath(binding.path)
        if (relative.is_absolute() or '..' in relative.parts or '\\' in binding.path
                or str(relative) != binding.path or relative.suffix != '.json'):
            raise RefreshError('portfolio-unsafe-metadata-path')
        path = safe_path(root / relative)
        base = {'key': binding.key, 'country': binding.country, 'metadataPath': binding.path,
                'metadataSha256': binding.pin, 'classification': binding.classification,
                'countryComplete': False, 'accepted': False}
        try:
            raw = _read_regular(path, budget, limit_code='portfolio-metadata-budget-exhausted')
        except (OSError, RefreshError) as error:
            if str(error) == 'portfolio-metadata-budget-exhausted':
                raise
            code = ('metadata-missing' if isinstance(error, FileNotFoundError) else
                    'metadata-not-regular' if str(error) == 'portfolio-file-not-regular' else
                    'metadata-changed' if str(error) == 'portfolio-file-changed' else
                    'metadata-unreadable')
            rows.append({**base, 'metadata': StageResult('failed', code).receipt(),
                         'staging': StageResult('held', code).receipt()})
            continue
        if sha(raw) != binding.pin:
            raise RefreshError('portfolio-metadata-pin-mismatch')
        try:
            value = strict_json(raw)
            if not isinstance(value, dict):
                raise ValueError()
        except (ValueError, UnicodeError, RecursionError):
            rows.append({**base, 'metadata': StageResult('failed', 'metadata-malformed', (binding.pin,)).receipt(),
                         'staging': StageResult('held', 'metadata-malformed').receipt()})
            continue
        stale = any(pointer(value, key) != {'present': True, 'value': expected}
                    for key, expected in binding.expected)
        metadata = StageResult('failed' if stale else 'succeeded',
                               'metadata-stale-release' if stale else 'metadata-pin-verified', (binding.pin,))
        rows.append({**base, 'metadata': metadata.receipt(),
            'staging': StageResult('held' if binding.holds or stale else 'unsupported',
                'metadata-stale-release' if stale else 'source-prerequisites-held' if binding.holds
                else 'production-contract-not-installed').receipt(),
            'selectedFields': {key: pointer(value, key) for key in binding.selectors},
            'holds': list(binding.holds),
            'metadataVerifiedAsOf': as_of,
            'cache': reuse_plan(None, None, as_of)})
    return {'schemaVersion': 'offmenu-portfolio21-metadata/1', 'baseCommit': BASE,
            'asOf': as_of, 'metadataBytesRead': budget[0], 'metadataBudgetBytes': MAX_METADATA_BYTES,
            'sourceBodiesRead': 0, 'networkRequests': 0, 'countryCompletions': 0,
            'goldAdmissions': 0,
            'sharedCapabilities': {'pureCachePlanner': 'absent-at-pinned-base',
                'productionSourceContract': 'not-installed',
                'pricesFieldOriginEmitter': 'not-installed'},
            'bindings': rows}


def stage_authored_prices(contract, bundle, roles, destination):
    """Exercise existing shared candidate/qualification engine on fixtures only.

    No real source contract is installed by this package. Trusted contracts must
    not be built from a receipt's licence label or this metadata audit's results.
    """
    if not contract.fixture or contract.source_id != 'prices':
        raise RefreshError('portfolio-authored-prices-fixture-required')
    return qualify_product_candidate(contract, bundle, roles, destination,
        license='authored fixture terms', attribution='Worker 21 authored fixture')


def write_report(report, destination):
    """Small immutable receipt: exact replay is a no-op; differences preserved."""
    destination = safe_path(destination)
    raw = canonical(report)
    if len(raw) > MAX_METADATA_BYTES:
        raise RefreshError('portfolio-report-too-large')
    try:
        with _regular_fd(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL) as (fd, directory, name):
            left = memoryview(raw)
            while left:
                written = os.write(fd, left)
                if written <= 0:
                    raise RefreshError('portfolio-report-write-failed')
                left = left[written:]
            current = os.fstat(fd)
            entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if not stat.S_ISREG(entry.st_mode) or _identity(current) != _identity(entry):
                raise RefreshError('portfolio-file-changed')
    except FileExistsError:
        try:
            existing = _read_regular(destination, [0], limit_code='portfolio-report-too-large')
        except OSError as error:
            raise RefreshError('portfolio-existing-report-unreadable') from error
        if existing != raw:
            raise RefreshError('portfolio-existing-report-differs')
        return 'reused'
    return 'written'
