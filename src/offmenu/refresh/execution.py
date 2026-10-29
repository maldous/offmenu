"""Reviewed historical parser protocol; parser support is not dataset admission.

No downloads or publication. Production admissions are deliberately code-owned and
empty until exact bundle, release, rights and qualification evidence is reviewed.
The same source adapter is reused across countries; country edges grant no rights.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from .capabilities import RELEASES
from .source_layout import CURRENT_HANDLERS, CURRENT_NATIONAL, SOURCE_LAYOUT_VERSION
from .acquisition import MIN_TTL
from .core import RefreshError

BASELINE = '5cfb4f7d4346b06d58b82ec7d3e2c8dd5d5fedb3'
NATIONAL = CURRENT_NATIONAL
# Fixed reviewed call targets. Never load a command or function from source data.
ADAPTERS = {
 'sweden-food': {'files': ('sweden-20260701.xlsx', 'acquisition.json'), 'mode': 'source-collect', 'function': 'collect', 'dependencies': (NATIONAL,)},
 'afcd': {'files': ('Food-Details.xlsx', 'Nutrient-profiles.xlsx', 'Nutrient-details.xlsx'), 'mode': 'records', 'function': 'records', 'dependencies': (NATIONAL,)},
 'mext': {'files': ('20260327-mxt_kagsei-mext-000029402_02.xlsx',), 'mode': 'collect', 'function': 'collect', 'dependencies': ()},
 'cofid': {'files': ('cofid2021.xlsx',), 'mode': 'records', 'function': 'cofid', 'dependencies': ()},
 'germany-bls': {'files': ('BLS_4_0_Daten_2025_DE.xlsx', 'BLS_4_0_Components_DE_EN.xlsx'), 'mode': 'records', 'function': 'bls', 'dependencies': ()},
}
from .national_tabular import ADAPTERS as TABULAR_ADAPTERS, valid_input_name, bundle_files
ADAPTERS.update(TABULAR_ADAPTERS)

# Review additions in code. Neither an arbitrary input-lock nor a CLI option can
# install an admission, waive a hold, or create an acquisition rights decision.
ADMISSIONS = {}
# Publisher links verified 2026-10-18; locators are not content pins or approval.
SOURCE_LOCATORS = {
 'afcd': {
  'Food-Details.xlsx': 'https://www.foodstandards.gov.au/sites/default/files/2025-12/AFCD%20Release%203%20-%20Food%20Details.xlsx',
  'Nutrient-profiles.xlsx': 'https://www.foodstandards.gov.au/sites/default/files/2025-12/AFCD%20Release%203%20-%20Nutrient%20profiles.xlsx',
  'Nutrient-details.xlsx': 'https://www.foodstandards.gov.au/sites/default/files/2025-12/AFCD%20Release%203%20-%20Nutrient%20details.xlsx'},
 'mext': {'20260327-mxt_kagsei-mext-000029402_02.xlsx': 'https://www.mext.go.jp/content/20260327-mxt_kagsei-mext-000029402_02.xlsx'},
}

MAX_INPUT = 64 * 1024**2
MAX_OUTPUT = 256 * 1024**2
MAX_MEMORY = 1024**3
MAX_WALL = 120

@dataclass(frozen=True)
class Admission:
    source_id: str
    release_id: str
    inputs: tuple  # (relative filename, bytes, sha256), including metadata assets
    acquired_at: str
    rights_evidence_sha256: str
    scope_evidence_sha256: str
    expected_records: int


def _release(source):
    historical = next((r for r in RELEASES if r['sourceId'] == source), None)
    if historical is None or source not in CURRENT_HANDLERS:
        return historical
    path, blob = CURRENT_HANDLERS[source]
    return {**historical, 'sourceLayoutVersion': SOURCE_LAYOUT_VERSION,
            'handler': {**historical['handler'], 'path': path, 'gitBlobSha': blob}}


def _safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RefreshError('execution-symlink-rejected')
    return path


def _pin(path, size, digest):
    if type(size) is not int or size < 0 or size > MAX_INPUT or not re.fullmatch('[0-9a-f]{64}', digest):
        raise RefreshError('invalid-execution-input-pin')
    path = _safe(path)
    if not path.is_file() or path.stat().st_size != size:
        raise RefreshError('execution-input-size-mismatch')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != digest:
        raise RefreshError('execution-input-hash-mismatch')


def verify_contract(entry, bundle):
    """Verify a code-reviewed admission; not a rights-approval constructor."""
    release = _release(entry.source_id)
    if entry.source_id not in ADAPTERS or release is None or entry.release_id != release['releaseId']:
        raise RefreshError('execution-release-not-supported')
    from datetime import datetime, timezone
    try:
        acquired = datetime.fromisoformat(entry.acquired_at.replace('Z', '+00:00'))
        if acquired.tzinfo is None:
            raise ValueError()
    except (AttributeError, ValueError):
        raise RefreshError('execution-acquisition-time-required') from None
    if acquired > datetime.now(timezone.utc):
        raise RefreshError('execution-acquisition-in-future')
    if any(not re.fullmatch('[0-9a-f]{64}', x) for x in (entry.rights_evidence_sha256, entry.scope_evidence_sha256)):
        raise RefreshError('execution-review-evidence-required')
    if type(entry.expected_records) is not int or entry.expected_records <= 0:
        raise RefreshError('execution-record-contract-required')
    names = [x[0] for x in entry.inputs]
    if len(names) != len(set(names)) or any(not valid_input_name(n) for n in names):
        raise RefreshError('execution-input-name-invalid')
    if not set(ADAPTERS[entry.source_id]['files']) <= set(names) or sum(x[1] for x in entry.inputs) > MAX_INPUT:
        raise RefreshError('execution-input-contract-incomplete')
    bundle = _safe(bundle)
    if bundle_files(bundle, names) != set(names):
        raise RefreshError('execution-bundle-set-mismatch')
    for name, size, digest in entry.inputs:
        _pin(bundle / name, size, digest)


def execute(source_id, bundle, destination, *, repository=None):
    """Normalize an admitted cache bundle in a resource-bounded offline process.

Only ADMISSIONS supplies the contract. No accept/curate/graph claims are made.
Caller owns private Foo staging storage; output must not already exist.
"""
    if source_id not in ADMISSIONS:
        raise RefreshError('execution-admission-missing')
    entry = ADMISSIONS[source_id]
    if entry.source_id != source_id:
        raise RefreshError('execution-admission-source-mismatch')
    verify_contract(entry, bundle)
    repository = _safe(repository or Path(__file__).resolve().parents[3])
    release = _release(source_id)
    deps = ((release['handler']['path'], release['handler']['gitBlobSha']),) + ADAPTERS[source_id]['dependencies']
    for name, digest in deps:
        path = _safe(repository / name)
        data = path.read_bytes()
        if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != digest:
            raise RefreshError('execution-handler-pin-mismatch')
    destination = _safe(destination)
    if destination.exists():
        raise RefreshError('execution-output-already-exists')
    import dataclasses
    request = {'entry': dataclasses.asdict(entry), 'bundle': str(_safe(bundle)),
               'destination': str(destination), 'repository': str(repository)}
    worker = Path(__file__).with_name('execution_worker.py')
    try:
        result = subprocess.run([sys.executable, '-I', str(worker)], input=json.dumps(request).encode(),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=MAX_WALL, check=False, env={'PYTHONHASHSEED': '0', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'})
    except subprocess.TimeoutExpired:
        raise RefreshError('execution-wall-limit-exceeded') from None
    if result.returncode:
        raise RefreshError('execution-worker-failed')
    receipt = json.loads((destination / 'execution-receipt.json').read_text())
    return receipt


def execution_plan(coverage):
    """One exhaustive plan row per discovered source, no guessed URLs or rights."""
    rows = []
    for source in sorted(coverage['sources'], key=lambda r: r['sourceId']):
        historical = source.get('historicalCapability') or {}
        family = historical.get('sourceId')
        adapter = ADAPTERS.get(family)
        held = source.get('holds', [])
        if source.get('status') == 'held' and not held:
            held = ['source-held']
        errors = list(held)
        if not historical.get('handler'):
            errors.append('reviewed-source-handler-missing')
        elif not adapter:
            errors.append('offline-adapter-contract-missing')
        if historical.get('releaseMatch') == 'different-release':
            errors.append('discovery-release-mismatch')
        if family not in ADMISSIONS:
            errors += ['exact-cache-bundle-pins-and-custody-required', 'release-rights-review-required',
                       'acquisition-time-required', 'qualification-and-acceptance-contract-required']
        rows.append({'sourceId': source['sourceId'], 'family': family,
                     'releaseId': historical.get('releaseId'), 'parserImplemented': bool(adapter),
                     'admitted': family in ADMISSIONS and not held, 'held': bool(held),
                     'inputFiles': list(adapter['files']) if adapter else [],
                     'ttlSeconds': MIN_TTL, 'defaultPolicy': 'reuse',
                     'budgets': {'inputBytes': MAX_INPUT, 'outputBytes': MAX_OUTPUT,
                                 'memoryBytes': MAX_MEMORY, 'wallSeconds': MAX_WALL},
                     'errors': sorted(set(errors)), 'countries': source.get('countries', []),
                     'reviewedFileLocators': SOURCE_LOCATORS.get(family, {}),
                     'landingEvidence': source.get('historicalLandingEvidence'),
                     'credentials': 'not-configured',
                     'cacheRoot': 'runner-owned-Foo-storage-required',
                     'acceptedCount': None})
    return {'schemaVersion': 'offmenu-source-execution-plan/1', 'baseline': BASELINE,
            'sourceCount': len(rows), 'sources': rows,
            'parserFamilies': sorted(ADAPTERS), 'productionAdmissions': len(ADMISSIONS),
            'accepted': False, 'crossCountryReuse': 'one adapter per family; no inferred country coverage'}


def reviewed_bindings(locations, *, repository=None, clock=None):
    """Build global-run stages only for code-admitted, explicitly located bundles.

locations maps family IDs to (bundle, new candidate destination). No download
fallback, credential lookup, rights waiver, acceptance or country promotion.
"""
    from .global_run import Binding, StageResult
    from datetime import datetime, timezone
    clock = clock or (lambda: datetime.now(timezone.utc))
    result = {}
    for family, entry in ADMISSIONS.items():
        if family not in locations:
            continue
        release = _release(family)
        if release is None or family not in ADAPTERS:
            continue
        bundle, destination = locations[family]
        state = {}

        def acquire(context, entry=entry, bundle=bundle):
            if context.fetch_policy != 'reuse':
                return StageResult('unsupported', 'historical-cache-only-policy')
            verify_contract(entry, bundle)
            now = clock()
            if not isinstance(now, datetime) or now.tzinfo is None:
                return StageResult('failed', 'historical-cache-clock-invalid')
            acquired = datetime.fromisoformat(entry.acquired_at.replace('Z', '+00:00'))
            age = (now - acquired).total_seconds()
            if age < 0:
                return StageResult('failed', 'historical-cache-acquisition-in-future')
            if age >= MIN_TTL:
                return StageResult('failed', 'historical-cache-expired')
            evidence = hashlib.sha256(json.dumps(entry.inputs, sort_keys=True).encode()).hexdigest()
            return StageResult('reused', evidence=(evidence,))

        def verify(context, entry=entry, bundle=bundle):
            verify_contract(entry, bundle)
            return StageResult('succeeded', evidence=(entry.rights_evidence_sha256, entry.scope_evidence_sha256))

        def parse(context, family=family, bundle=bundle, destination=destination, state=state):
            limits = context.limits
            if (limits.job_memory_bytes < MAX_MEMORY or limits.input_bytes < MAX_INPUT
                    or limits.output_bytes < MAX_OUTPUT or limits.wall_seconds < MAX_WALL):
                return StageResult('unsupported', 'historical-parser-budget-insufficient')
            receipt = execute(family, bundle, destination, repository=repository)
            state['receipt'] = receipt
            return StageResult('succeeded', evidence=(receipt['candidateSha256'],), observed_count=receipt['normalizedRecords'])

        def normalized(context, state=state):
            receipt = state.get('receipt')
            if receipt is None:
                return StageResult('failed', 'historical-candidate-receipt-missing')
            return StageResult('succeeded', evidence=(receipt['candidateSha256'],), observed_count=receipt['normalizedRecords'])

        binding = Binding(handlers={'acquire': acquire, 'verify': verify, 'parse': parse,
                                    'normalize': normalized, 'validate': normalized},
                          admission='reviewed', resource_boundary_verified=True)
        # A family can have several discovery aliases. The caller must deduplicate
        # jobs through the source execution plan before scheduling such aliases.
        # Current implemented families each have one exact discovery ID.
        if len(release['discoveryIds']) != 1:
            raise RefreshError('execution-discovery-alias-deduplication-required')
        result[release['discoveryIds'][0]] = binding
    return result
