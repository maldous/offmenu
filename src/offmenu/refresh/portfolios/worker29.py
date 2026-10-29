"""FO/ET/FK/FM retained-metadata staging bindings, with no I/O or admission.

Input is explicitly supplied metadata bytes, never a source body. Contracts are
trusted code; a supplied document cannot grant rights or change selectors/pins.
The result is a diagnostic metadata projection, NOT an acceptance candidate.
"""
from dataclasses import dataclass, asdict
import re

from ..core import canonical, sha, strict_json, timestamp, RefreshError
from ..field_provenance import field_origin_errors


@dataclass(frozen=True)
class Binding:
    key: str
    country: str
    domain: str
    source_id: str
    release_id: str  # Local retained snapshot identity; not a publisher release claim.
    manifest_path: str
    manifest_sha256: str
    body_sha256_declared: str | None
    selectors: tuple[tuple[str, str], ...]
    original_acquired_at: str | None = None
    stage_holds: tuple[str, ...] = ()
    downstream_holds: tuple[str, ...] = ()
    unit_basis_scope: str = 'No quantities projected; units and basis not established by this binding.'


ROOT = '/home/user/Documents/Codex/2026-10-13/task-3/reports'
OWNER = ROOT + '/country249-fixed64-priority/deliverables/owner-29'
BINDINGS = {
    'fo-ip02006': Binding(
        'fo-ip02006', 'FO', 'price-index-literal-metadata', 'hagstova-ip02006',
        'retained-8856d1d20b41333a',
        '/home/user/src/offmenu-data/owner29/fo-ip02006-whole-snapshot-cut3034-proposed/author-receipt.json',
        '5ba2d276b052b4e9be1b2c27712e166c105967dfa3f5c94f9aaf3cf618bcd949',
        '8856d1d20b41333a47524eec95b35a582d0aeda9737e1d761eee60971626a89a',
        (('slots', '/counts/observationSlots'), ('nativeUnit', '/counts/perMeasure/0/explicitUnitField'),
         ('nativeBase', '/counts/perMeasure/0/indexBase')),
        '2026-10-14T22:15:18.707027+00:00',
        downstream_holds=('unit-base-unknown', 'frequency-not-inferred', 'not-retailer-prices')),
    'et-table1': Binding(
        'et-table1', 'ET', 'label-profile-metadata', 'plos-0294068-table1',
        'retained-d12f14cd9793e6f6',
        ROOT + '/country-delivery-priority-20261017/owner-29/ET-primary0294068-table1-literal-v1/manifest.json',
        '169a4ac1d4f48c86cc670f488584cff48e9e326e573bc6da4ba8474680e87936',
        'd12f14cd9793e6f6488dbc503995dedc09a978c39bebf5314273ae7f93cfb58b',
        (('profiles', '/actualMeasuredCounts/dataRows'), ('dashCells', '/actualMeasuredCounts/printedDashCells'),
         ('blankCells', '/actualMeasuredCounts/blankCells')),
        downstream_holds=('label-profiles-not-nutrient-measurements', 'sample-date-unknown', 'release-date-conflict')),
    'fk-menu': Binding(
        'fk-menu', 'FK', 'venue-menu-metadata', 'malvina-menu', 'retained-e91c557f0ec5d575',
        OWNER + '/B02-W29/returned-FK49-B03-W49/binding.json',
        '66ceecbe31b02b9bba5af5481755edbc303b8b650e8a53ddedc27b0459dea3e4',
        'e91c557f0ec5d575f80cae6fa9102879d62e9cb27615aa8000a00cd8caa677f8',
        (('currency', '/fieldDispositions/currency/value'), ('feesOrTax', '/fieldDispositions/feesOrTax/value'),
         ('printedEffectiveDate', '/fieldDispositions/printedEffectiveDate/value')),
        downstream_holds=('derivative-use-unqualified', 'currency-unknown', 'fees-unknown-not-zero', 'current-offer-unverified')),
    'fm-menu': Binding(
        'fm-menu', 'FM', 'institutional-menu-locator-metadata', 'com-fsm-dining',
        'retained-ec60068337d3cfbd', OWNER + '/FM/institutional-menu-date-locators.json',
        'e184825d8442c0f7c04b029db2ad8feecd42d5fb168f6897b0a39b6ab99337ee',
        'ec60068337d3cfbdb53c67e6bea40e0155896ec0a6c865df75915a47b139df68',
        (('dateSelector', '/dateHeading/selector'), ('menuTables', '/menuTableCount')),
        downstream_holds=('custodian50-retains-ownership', 'menu-text-use-unqualified', 'actual-service-unverified')),
}
# Other retained portfolio lanes remain unbound, not silently omitted as complete.
UNBOUND = {
    'FO-recipes': 'Retained parser4292/4569 evidence only; literal-text use not selected.',
    'ET-efct2025': 'One food010145/40-field candidate; scientific semantics and method inputs unresolved.',
    'FK-recipes': 'Edition and literal derivative use unresolved.',
    'FM-composition': '13-row locator; provitamin-A unit/basis unresolved.',
    'FM-recipes': 'Retained original absent; acquisition denial holds; no retry.',
}


def _pointer(value, pointer):
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(pointer)
    if isinstance(value, (dict, list)):
        raise ValueError('scalar-selector-required')
    return value


def stage_metadata(binding, metadata, *, now, validation_at=None,
                   previous_receipt=None, holds=()):
    """Pure bounded interface. metadata: bytes or None; no files/network/cache reads.

    Caller-owned review supplies Binding and any additional holds. previous_receipt
    is the prior successful receipt digest, not an arbitrary source build key.
    Age is observation only: no acquisition TTL or fetch decision is implemented.
    """
    errors = set()
    data, origins = {}, {}
    policy_pin = sha(canonical(asdict(binding)))
    input_alias = 'retained-metadata.json'
    base = {'schemaVersion': 'offmenu-worker29-staging-metadata/1',
            'binding': binding.key, 'country': binding.country, 'domain': binding.domain,
            'contractSha256': policy_pin, 'manifest': {'path': binding.manifest_path,
            'sha256': binding.manifest_sha256},
            'declaredSourceBodySha256': binding.body_sha256_declared,
            'downstreamHolds': sorted(set(binding.downstream_holds)),
            'nativeUnit': None, 'nativeBasis': None, 'unitBasisScope': binding.unit_basis_scope,
            'networkRequests': 0, 'bodyOperations': 0, 'admittedRecords': 0,
            'cacheDecision': 'shared-pure-planner-required',
            'revalidationResetsAcquisitionAge': False}
    if not re.fullmatch('[0-9a-f]{64}', binding.manifest_sha256):
        errors.add('invalid-trusted-manifest-pin')
    age, validation_age = None, None
    try:
        clock = timestamp(now)
        original = timestamp(binding.original_acquired_at) if binding.original_acquired_at else None
        checked = timestamp(validation_at) if validation_at is not None else None
        if original is not None:
            age = (clock - original).total_seconds()
            if age < 0:
                errors.add('acquisition-in-future')
        if checked is not None:
            validation_age = (clock - checked).total_seconds()
            if validation_age < 0 or (original is not None and checked < original):
                errors.add('invalid-validation-time')
    except RefreshError:
        errors.add('invalid-time-metadata')
    active_holds = sorted(set(binding.stage_holds) | set(holds))
    if metadata is None:
        errors.add('metadata-missing')
    elif not isinstance(metadata, bytes) or len(metadata) > 1024 * 1024:
        errors.add('metadata-invalid-or-too-large')
    else:
        try:
            document = strict_json(metadata)
            if sha(metadata) != binding.manifest_sha256:
                errors.add('stale-input-pin-mismatch')
            if not isinstance(document, dict):
                errors.add('metadata-object-required')
            if not errors and not active_holds:
                for name, pointer in binding.selectors:
                    try:
                        data[name] = _pointer(document, pointer)
                    except (KeyError, IndexError, ValueError, TypeError):
                        errors.add('metadata-selector-missing')
                        continue
                    origins['/data/' + name] = {'kind': 'source',
                        'sourceId': binding.source_id, 'releaseId': binding.release_id,
                        'inputPath': input_alias, 'inputSha256': binding.manifest_sha256,
                        'sourceRecordId': binding.key, 'sourceField': pointer}
        except (ValueError, UnicodeError, RecursionError):
            errors.add('malformed-metadata')
    row = {'data': data, 'provenance': {'sourceId': binding.source_id,
           'releaseId': binding.release_id, 'fieldOrigins': origins}}
    if data:
        errors.update(field_origin_errors(row, {input_alias: binding.manifest_sha256}))
    # Never emit a partial projection after any diagnostic or hold.
    if errors or active_holds:
        row = None
    fingerprint = sha(canonical({'contract': policy_pin, 'row': row})) if row else None
    status = ('held' if active_holds else 'invalid' if errors else
              'no-op' if previous_receipt == fingerprint else 'ready-metadata')
    return {**base, 'status': status, 'diagnostics': sorted(errors), 'stageHolds': active_holds,
            'originalAcquiredAt': binding.original_acquired_at, 'validationAt': validation_at,
            'acquisitionAgeSeconds': age, 'validationAgeSeconds': validation_age,
            'projection': row, 'receiptSha256': fingerprint}
