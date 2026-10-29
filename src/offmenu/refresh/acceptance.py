"""Bounded offline qualification and scope-specific local acceptance.

Contracts/callbacks are reviewed application code, never source manifests or CLI
plugins. This module neither activates rights nor publishes/updates pointers.
Native, curated and common outputs require separate contracts; a native pass is
not a claim that a public projection, graph or country is complete.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import tempfile

DIGEST = re.compile(r'[0-9a-f]{64}')
MAX_BYTES = 256 * 1024**2
MAX_LINE = 8 * 1024**2
MAX_ROWS = 1_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Asset:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceContract:
    source_id: str
    release_id: str
    scope_id: str
    acquired_at: str | None
    inputs: tuple
    expected_records: int
    expected_ids_sha256: str  # SHA256 of sorted unique IDs, each JSON encoded + LF
    schemas: dict            # kind -> full JSON Schema; no remote references
    schemas_sha256: str
    semantic_validator: object  # reviewed callable(row) -> iterable of fixed codes
    policy_sha256: str       # reviewed semantic/projection policy identity
    rights_evidence: Asset  # evidence file in bundle, included in exact input set
    scope_evidence: Asset   # independent inventory/scope evidence, also in bundle
    permitted_operations: frozenset
    required_operations: frozenset = frozenset(('retain', 'parse', 'transform'))
    holds: tuple = ()
    fixture: bool = False
    output_scope: str = 'native'
    output_visibility: str = 'private'
    max_input_bytes: int = MAX_BYTES
    max_output_bytes: int = MAX_BYTES
    max_records: int = MAX_ROWS
    acquisition_clock_status: str = 'known'
    clock_evidence: Asset | None = None


def contract_fingerprint(contract):
    from dataclasses import fields
    values = {}
    for field in fields(contract):
        if field.name == 'semantic_validator':
            continue  # Its reviewed identity is policy_sha256, never callable repr.
        value = getattr(contract, field.name)
        if field.name == 'inputs':
            value = sorted((vars(a) for a in value), key=lambda a: a['path'])
        elif isinstance(value, Asset):
            value = vars(value)
        elif isinstance(value, frozenset):
            value = sorted(value)
        values[field.name] = value
    return fingerprint(values)


def _safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink-rejected')
    return path


def _valid_asset(asset):
    p = PurePosixPath(asset.path)
    return (isinstance(asset.path, str) and asset.path == p.as_posix()
            and not p.is_absolute() and bool(p.parts)
            and all(x not in ('', '.', '..') for x in p.parts)
            and '\\' not in asset.path and type(asset.bytes) is int
            and 0 <= asset.bytes <= 1024**4
            and isinstance(asset.sha256, str) and DIGEST.fullmatch(asset.sha256))


def _hash_file(path, limit=MAX_BYTES):
    path = _safe(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('file-bound-or-type-invalid')
    h, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(block)
            if size > limit:
                raise ValueError('file-bound-exceeded')
            h.update(block)
    return size, h.hexdigest()


def _input_paths(contract, bundle, input_root=None):
    """Route pinned private product inputs without materializing a new bundle.

    The evidence directory stays exact. Only explicitly pinned non-evidence
    paths are resolved under input_root; unrelated originals are not inventoried.
    Callers validate the contract/pins before using this routing helper.
    """
    root = _safe(bundle)
    if input_root is None:
        return ({a.path: _safe(root / a.path) for a in contract.inputs},
                {a.path for a in contract.inputs})
    if (contract.source_id not in ('off', 'usda-files')
            or contract.output_scope != 'native' or contract.output_visibility != 'private'
            or contract.holds
            or not {'retain', 'parse', 'transform'} <= set(contract.required_operations)
            or not set(contract.required_operations) <= set(contract.permitted_operations)):
        raise ValueError('separate-input-root-private-product-contract-required')
    evidence = [contract.rights_evidence, contract.scope_evidence]
    if contract.clock_evidence is not None:
        evidence.append(contract.clock_evidence)
    names = {a.path for a in evidence}
    if (len(names) != len(evidence) or any(a not in contract.inputs for a in evidence)
            or not names < {a.path for a in contract.inputs}):
        raise ValueError('separate-input-root-evidence-invalid')
    originals = _safe(input_root)
    if root == originals or root in originals.parents or originals in root.parents:
        raise ValueError('separate-input-roots-overlap')
    return {a.path: _safe((root if a.path in names else originals) / a.path)
            for a in contract.inputs}, names


def ids_digest(ids):
    """Small reviewed inventories/tests; qualification itself uses disk-backed IDs."""
    h = hashlib.sha256()
    for identity in sorted(set(ids)):
        h.update(canonical(identity) + b'\n')
    return h.hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate-json-key')
        result[key] = value
    return result


def _local_schema(schema):
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key in ('$ref', '$dynamicRef') and (not isinstance(value, str) or not value.startswith('#')):
                return False
            if not _local_schema(value):
                return False
    elif isinstance(schema, list):
        return all(_local_schema(x) for x in schema)
    return True


def qualify(contract, bundle, candidate, manifest, *, scratch_root=None, input_root=None):
    """Inspect all bounded rows; return deterministic diagnostics, never mutate data.

The supplied contract is trusted code configuration, not a rights constructor.
Schema validators and semantic callbacks must cover source-specific units, bases,
qualifiers, joins and provenance required by the selected scope. Unknown semantics
remain held. IDs/count expectations come from independently reviewed scope evidence.
For private native OFF/USDA, input_root optionally holds the pinned originals;
bundle then contains exactly the distinct rights/scope/optional clock evidence.
"""
    errors = set()
    def error(code):
        errors.add(code)
    result = {'schemaVersion': 'offmenu-source-qualification/1',
              'sourceId': contract.source_id, 'releaseId': contract.release_id,
              'scopeId': contract.scope_id, 'outputScope': contract.output_scope,
              'outputVisibility': contract.output_visibility,
              'fixture': contract.fixture, 'normalizedRecords': 0,
              'candidateSha256': None, 'manifestSha256': None,
              'policySha256': contract.policy_sha256, 'contractSha256': None,
              'rightsEvidenceSha256': contract.rights_evidence.sha256,
              'scopeEvidenceSha256': contract.scope_evidence.sha256,
              'qualified': False, 'errors': []}
    try:
        if (not all(isinstance(x, str) and x for x in
                    (contract.source_id, contract.release_id, contract.scope_id))
                or type(contract.expected_records) is not int
                or any(type(x) is not int or not 0 < x <= 1024**4 for x in
                       (contract.max_input_bytes, contract.max_output_bytes))
                or type(contract.max_records) is not int or not 0 < contract.max_records <= 1_000_000_000
                or not 0 < contract.expected_records <= contract.max_records
                or type(contract.fixture) is not bool
                or contract.output_scope not in ('native', 'curated', 'common')
                or contract.output_visibility not in ('private', 'public')
                or not callable(contract.semantic_validator)
                or not contract.schemas
                or any(not isinstance(x, str) or not DIGEST.fullmatch(x) for x in
                       (contract.expected_ids_sha256, contract.schemas_sha256, contract.policy_sha256))
                or fingerprint(contract.schemas) != contract.schemas_sha256
                or not _local_schema(contract.schemas)):
            raise ValueError('contract-invalid')
        result['contractSha256'] = contract_fingerprint(contract)
        from .product_clock import clock_marker, validate_contract_clock
        validate_contract_clock(contract)
        if not contract.required_operations or not contract.required_operations <= contract.permitted_operations:
            error('operation-rights-missing')
        if not frozenset(('retain', 'parse', 'transform')) <= contract.required_operations:
            error('operation-contract-incomplete')
        if contract.output_visibility == 'public' and not frozenset(('serve', 'redistribute')) <= contract.required_operations:
            error('publication-operation-rights-required')
        if contract.holds:
            error('source-held')
        assets = contract.inputs
        if (not assets or any(not isinstance(a, Asset) or not _valid_asset(a) for a in assets)
                or len({a.path for a in assets}) != len(assets)
                or sum(a.bytes for a in assets) > contract.max_input_bytes
                or contract.rights_evidence not in assets or contract.scope_evidence not in assets):
            raise ValueError('input-contract-invalid')
        root = _safe(bundle)
        paths, bundle_names = _input_paths(contract, root, input_root)
        if input_root is not None:
            for output in (candidate, scratch_root):
                if output is not None:
                    output = _safe(output)
                    for source_root in (root, _safe(input_root)):
                        if output == source_root or output in source_root.parents or source_root in output.parents:
                            raise ValueError('separate-input-output-overlap')
        from .national_tabular import bundle_files
        try:
            actual = bundle_files(root, bundle_names)
            if actual != bundle_names:
                error('input-inventory-mismatch')
        except ValueError:
            error('input-inventory-mismatch')
        for asset in assets:
            try:
                if _hash_file(paths[asset.path], contract.max_input_bytes) != (asset.bytes, asset.sha256):
                    error('input-custody-mismatch')
            except (OSError, ValueError):
                error('input-custody-mismatch')
        validate_contract_clock(contract, root)
        from jsonschema import Draft202012Validator
        validators = {}
        for kind, schema in contract.schemas.items():
            Draft202012Validator.check_schema(schema)
            validators[kind] = Draft202012Validator(schema)
        if not isinstance(manifest, dict):
            raise ValueError('manifest-invalid')
        result['manifestSha256'] = fingerprint(manifest)
        expected_manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                             'acquiredAt': contract.acquired_at,
                             'rightsEvidenceSha256': contract.rights_evidence.sha256,
                             'scopeEvidenceSha256': contract.scope_evidence.sha256,
                             'normalizedRecords': contract.expected_records}
        if any(key not in manifest or manifest[key] != value for key, value in expected_manifest.items()):
            error('manifest-contract-mismatch')
        marker = clock_marker(contract.acquisition_clock_status,
                              contract.clock_evidence.sha256 if contract.clock_evidence else None)
        if ((marker is None and 'acquisitionClock' in manifest)
                or (marker is not None and manifest.get('acquisitionClock') != marker)):
            error('manifest-clock-mismatch')
        expected_inputs = [{'path': a.path, 'bytes': a.bytes, 'sha256': a.sha256} for a in assets]
        supplied_inputs = manifest.get('inputFiles')
        if (not isinstance(supplied_inputs, list)
                or any(set(a) - {'path', 'bytes', 'sha256', 'role'} for a in supplied_inputs)
                or sorted(({k: a[k] for k in ('path', 'bytes', 'sha256')} for a in supplied_inputs), key=lambda a: a['path']) != sorted(expected_inputs, key=lambda a: a['path'])):
            error('manifest-inputs-mismatch')
        size, digest = _hash_file(candidate, contract.max_output_bytes)
        result['candidateSha256'] = digest
        if manifest.get('candidateBytes') != size or manifest.get('candidateSha256') != digest:
            error('candidate-custody-mismatch')
        # Temporary disk-backed IDs bound resident memory independently of row count.
        with tempfile.TemporaryDirectory(prefix='offmenu-qualify-',
                                         dir=_safe(scratch_root) if scratch_root is not None else None) as temporary:
            with sqlite3.connect(str(Path(temporary) / 'ids.sqlite')) as db:
                db.execute('CREATE TABLE ids (id TEXT PRIMARY KEY)')
                parsed_digest, parsed_size = hashlib.sha256(), 0
                with _safe(candidate).open('rb') as stream:
                    while True:
                        raw = stream.readline(MAX_LINE + 1)
                        if not raw:
                            break
                        parsed_size += len(raw)
                        parsed_digest.update(raw)
                        if parsed_size > contract.max_output_bytes:
                            error('candidate-byte-bound-exceeded')
                            break
                        result['normalizedRecords'] += 1
                        if len(raw) > MAX_LINE or not raw.endswith(b'\n'):
                            error('record-line-invalid')
                            if len(raw) > MAX_LINE:
                                break
                            continue
                        if result['normalizedRecords'] > contract.max_records:
                            error('record-count-bound-exceeded')
                            break
                        try:
                            packet = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                            if not isinstance(packet, list) or len(packet) != 1 or not isinstance(packet[0], dict):
                                raise ValueError()
                            row = packet[0]
                            canonical(row)  # Reject overflowed JSON numbers as well as NaN.
                            identity = row.get('id')
                            if not isinstance(identity, str) or not identity:
                                raise ValueError()
                            try:
                                db.execute('INSERT INTO ids VALUES (?)', (identity,))
                            except sqlite3.IntegrityError:
                                error('record-identity-duplicate')
                            provenance = row.get('provenance', {})
                            if not isinstance(provenance, dict) or any(provenance.get(key) != value for key, value in
                                    (('sourceId', contract.source_id), ('releaseId', contract.release_id), ('fetchedAt', contract.acquired_at))):
                                error('record-provenance-mismatch')
                            if (not isinstance(provenance, dict) or 'fetchedAt' not in provenance
                                    or (marker is None and 'acquisitionClock' in provenance)
                                    or (marker is not None and provenance.get('acquisitionClock') != marker)):
                                error('record-clock-mismatch')
                            validator = validators.get(row.get('kind'))
                            if validator is None or not validator.is_valid(row):
                                error('record-schema-invalid')
                            issues = contract.semantic_validator(row)
                            for issue in issues:
                                if not isinstance(issue, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,95}', issue):
                                    error('semantic-validator-invalid')
                                else:
                                    error(issue)
                        except Exception:
                            # Never echo source values, paths or callback exception text.
                            error('record-invalid')
                if (parsed_size, parsed_digest.hexdigest()) != (size, digest):
                    error('candidate-parsed-bytes-mismatch')
                h = hashlib.sha256()
                for (identity,) in db.execute('SELECT id FROM ids ORDER BY id COLLATE BINARY'):
                    h.update(canonical(identity) + b'\n')
                if h.hexdigest() != contract.expected_ids_sha256:
                    error('expected-record-identities-mismatch')
        for asset in assets:
            try:
                if _hash_file(paths[asset.path], contract.max_input_bytes) != (asset.bytes, asset.sha256):
                    error('input-custody-changed-during-qualification')
            except (OSError, ValueError):
                error('input-custody-changed-during-qualification')
        if _hash_file(candidate, contract.max_output_bytes) != (size, digest):
            error('candidate-changed-during-qualification')
        if result['normalizedRecords'] != contract.expected_records:
            error('expected-record-count-mismatch')
    except Exception:
        error('qualification-contract-or-input-invalid')
    result['errors'] = sorted(errors)
    result['qualified'] = not errors
    result['status'] = 'qualified' if not errors else 'held'
    result['qualificationSha256'] = fingerprint(result)
    return result


def accept(contract, bundle, candidate, manifest, *, scratch_root=None, input_root=None):
    """Revalidate current bytes and issue a separate receipt, not a mutable pointer."""
    qualification = qualify(contract, bundle, candidate, manifest, scratch_root=scratch_root,
                            input_root=input_root)
    accepted = qualification['qualified']
    return {**qualification,
            'schemaVersion': 'offmenu-source-acceptance/1',
            'status': ('accepted-fixture-scope' if contract.fixture else 'accepted-source-scope') if accepted else 'held',
            'accepted': accepted, 'acceptedCount': qualification['normalizedRecords'] if accepted else None,
            'productionAccepted': accepted and not contract.fixture,
            'countryCoverageComplete': False, 'publication': 'not-enabled'}


@dataclass(frozen=True)
class CellRequirement:
    country: str
    domain: str
    # Every selected source requirement is mandatory, including exact scope/release.
    sources: tuple  # (sourceId, releaseId, scopeId, qualificationSha256)
    applicability_evidence_sha256: str
    completeness_evidence_sha256: str


def _valid_acceptance_receipt(receipt):
    keys = ('sourceId', 'releaseId', 'scopeId', 'outputScope', 'outputVisibility',
            'fixture', 'normalizedRecords', 'candidateSha256', 'manifestSha256',
            'policySha256', 'contractSha256', 'rightsEvidenceSha256', 'scopeEvidenceSha256',
            'qualified', 'errors')
    try:
        original = {key: receipt[key] for key in keys}
        original.update(schemaVersion='offmenu-source-qualification/1', status='qualified')
        return (receipt['schemaVersion'] == 'offmenu-source-acceptance/1'
                and type(receipt['fixture']) is bool
                and receipt['status'] == ('accepted-fixture-scope' if receipt['fixture'] else 'accepted-source-scope')
                and receipt['accepted'] is True
                and receipt['productionAccepted'] is (not receipt['fixture'])
                and receipt['qualified'] is True
                and type(receipt['acceptedCount']) is int
                and receipt['acceptedCount'] == receipt['normalizedRecords']
                and receipt['acceptedCount'] > 0
                and fingerprint(original) == receipt['qualificationSha256'])
    except (KeyError, TypeError, ValueError):
        return False


def assess_cells(requirements, acceptances, *, countries, domains):
    """Explicit full-cell contracts; global routes and language never imply scope."""
    requirements = tuple(requirements)
    valid_keys = {(c, d) for c in countries for d in domains}
    by_key = {}
    for req in requirements:
        key = (req.country, req.domain)
        if key not in valid_keys or key in by_key:
            raise ValueError('country-domain-contract-invalid')
        by_key[key] = req
    cells = []
    for country, domain in sorted(valid_keys):
        req = by_key.get((country, domain))
        errors = []
        if req is None:
            errors.append('country-domain-contract-missing')
        else:
            if not req.sources or len(set(req.sources)) != len(req.sources):
                errors.append('country-domain-source-contract-invalid')
            if any(not isinstance(x, str) or not DIGEST.fullmatch(x) for x in
                   (req.applicability_evidence_sha256, req.completeness_evidence_sha256)):
                errors.append('country-domain-evidence-missing')
            for source, release, scope, qualification in req.sources:
                matches = [r for r in acceptances if
                           (r.get('sourceId'), r.get('releaseId'), r.get('scopeId'), r.get('qualificationSha256'))
                           == (source, release, scope, qualification)]
                if (len(matches) != 1 or matches[0].get('productionAccepted') is not True
                        or matches[0].get('accepted') is not True or matches[0].get('fixture') is not False
                        or matches[0].get('errors') != [] or not _valid_acceptance_receipt(matches[0])):
                    errors.append('required-source-scope-not-accepted')
        cells.append({'country': country, 'domain': domain,
                      'status': 'accepted-scope' if not errors else 'unassessed',
                      'errors': sorted(set(errors))})
    accepted = sum(r['status'] == 'accepted-scope' for r in cells)
    return {'cells': cells, 'acceptedCountryDomainCells': accepted,
            'requiredCountryDomainCells': len(cells),
            'countryCoverageComplete': bool(cells) and accepted == len(cells)}


@dataclass(frozen=True)
class CandidateArtifact:
    contract: SourceContract
    bundle: object
    candidate: object
    manifest: dict
    scratch_root: object = None


def endstate_handlers(native, curate, graph, receipts, *, discovery_id=None):
    """Build real validate/curate/graph/qualify/accept handlers for GLOBAL.

Factories are trusted code: native(context) returns CandidateArtifact;
curate(context, native_artifact) and graph(context, curated_artifact) execute the
reviewed transformations and return their own independently contracted artifacts.
A missing factory is unsupported, never silently treated as a successful stage.
The caller supplies the existing isolation/resource boundary; callbacks must not
perform network operations. receipts is private per-run output for assess_cells.
No production factory, rights or schema mapping is installed by this helper.
"""
    from .global_run import StageResult
    state = {}

    def checked(context, artifact, scope):
        if not isinstance(artifact, CandidateArtifact) or artifact.contract.output_scope != scope:
            return None, StageResult('failed', 'artifact-scope-contract-invalid')
        if context.source_id != (discovery_id or artifact.contract.source_id):
            return None, StageResult('failed', 'artifact-source-binding-mismatch')
        # Respect the caller's tighter byte budget, rather than just module caps.
        if (sum(a.bytes for a in artifact.contract.inputs) > context.limits.input_bytes
                or _safe(artifact.candidate).stat().st_size > context.limits.output_bytes):
            return None, StageResult('failed', 'artifact-byte-budget-exceeded')
        result = qualify(artifact.contract, artifact.bundle, artifact.candidate, artifact.manifest,
                         scratch_root=artifact.scratch_root)
        state.setdefault('qualifications', {})[context.stage] = result
        if not result['qualified']:
            return None, StageResult('held', 'artifact-qualification-failed',
                                     (result['qualificationSha256'],), result['normalizedRecords'])
        return result, StageResult('succeeded', evidence=(result['qualificationSha256'],),
                                   observed_count=result['normalizedRecords'])

    def validate(context):
        if native is None:
            return StageResult('unsupported', 'native-artifact-factory-missing')
        artifact = native(context)
        result, stage = checked(context, artifact, 'native')
        if result is not None:
            state['native'] = artifact
        return stage

    def transform(context, factory, previous, output):
        if factory is None:
            return StageResult('unsupported', output + '-artifact-factory-missing')
        if previous not in state:
            return StageResult('failed', 'prior-qualified-artifact-missing')
        artifact = factory(context, state[previous])
        # Source/release cannot change silently between stages.
        prior = state[previous].contract
        if (not isinstance(artifact, CandidateArtifact)
                or (artifact.contract.source_id, artifact.contract.release_id, artifact.contract.fixture)
                   != (prior.source_id, prior.release_id, prior.fixture)):
            return StageResult('failed', 'artifact-source-identity-changed')
        result, stage = checked(context, artifact, output)
        if result is not None:
            state[output] = artifact
        return stage

    def qualification(context):
        if 'common' not in state:
            return StageResult('failed', 'common-artifact-missing')
        return checked(context, state['common'], 'common')[1]

    def acceptance(context):
        artifact = state.get('common')
        if artifact is None:
            return StageResult('failed', 'common-artifact-missing')
        # Recheck budgets/current bytes even if accept was invoked independently.
        result, stage = checked(context, artifact, 'common')
        if result is None:
            return stage
        receipt = accept(artifact.contract, artifact.bundle, artifact.candidate, artifact.manifest,
                         scratch_root=artifact.scratch_root)
        key = (receipt['sourceId'], receipt['releaseId'], receipt['scopeId'])
        receipts[key] = receipt
        state['acceptance'] = receipt
        return StageResult('succeeded' if receipt['accepted'] else 'held',
                           'none' if receipt['accepted'] else 'source-acceptance-failed',
                           (fingerprint(receipt),), receipt['acceptedCount'])

    return {'validate': validate,
            'curate': lambda context: transform(context, curate, 'native', 'curated'),
            'graph': lambda context: transform(context, graph, 'curated', 'common'),
            'qualify': qualification, 'accept': acceptance}, state
