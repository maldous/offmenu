"""Bounded selected USDA product origins; no full-stage wrapper or real factory.

All selection/derivation/review pins and the fresh database identity come from
reviewed application/runtime evidence. Hashing an observed cache here would not
establish that authority. This caller never hashes the full DB or opens a ZIP,
candidate, lookup artifact or original. The supplied records/manifest are bounded
buffers; only two indexed source-row reads per selected product are allowed.
"""
from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import threading
import time

from .acceptance import Asset, SourceContract, contract_fingerprint, ids_digest, _valid_asset
from .core import RefreshError, canonical, safe_path, strict_json
from .field_provenance import field_origin_errors
from .native_barcode_lookup import _binding
from .national_tabular import valid_input_name
from .product_adapters import ProductContext, ProductLimits, VERSION as PRODUCER_VERSION
from .product_field_origins import ProductOriginEmitter
from . import product_field_origins as origin_policy
from .off_partition_witness import _descriptor_snapshot

VERSION = 'offmenu-selected-usda-product-origins/1'


@dataclass(frozen=True)
class RowPin:
    ordinal: int
    body_sha256: str  # Exact UTF8 raw.body text, not a reconstructed CSV hash.


@dataclass(frozen=True)
class SelectedProduct:
    id: str
    source_record_id: str
    candidate_line: int
    record_sha256: str  # core canonical(record), including LF.
    food: RowPin
    branded_food: RowPin


@dataclass(frozen=True)
class SelectedOriginScope:
    scope_id: str
    context: ProductContext
    archive: Asset
    database: Asset
    normalization_manifest: Asset
    database_identity: tuple  # Independently qualified dev/ino/size/mtime_ns/ctime_ns.
    full_contract_sha256: str
    qualification_sha256: str
    candidate_sha256: str
    lookup_artifact_sha256: str
    lookup_review_sha256: str
    derivation_review_sha256: str
    custody_review_sha256: str
    operation_evidence_sha256: str
    emitter_policy_sha256: str
    caller_policy_sha256: str
    members: tuple  # Exact reviewed (table, ZIP member) pairs, no derivation here.
    products: tuple
    expected_ids_sha256: str  # Selected products only; never edits full SourceContract.


@dataclass(frozen=True)
class SelectedOriginLimits:
    max_records: int
    max_input_bytes: int
    max_manifest_bytes: int
    max_row_bytes: int
    max_source_row_bytes: int
    max_record_bytes: int
    max_output_bytes: int
    max_database_bytes: int
    max_sqlite_steps: int
    max_seconds: int


def _fail(code):
    raise RefreshError('selected-origin-' + code)


def _sha(value):
    return type(value) is str and bool(re.fullmatch('[0-9a-f]{64}', value))


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _guard(deadline):
    if time.monotonic() >= deadline:
        _fail('duration-bound')


def _validate(scope, limits, contract, qualification, manifest, binding_evidence):
    if (type(scope) is not SelectedOriginScope or type(limits) is not SelectedOriginLimits
            or type(contract) is not SourceContract or contract.source_id != 'usda-files'
            or type(scope.context) is not ProductContext
            or scope.context.source_id != 'usda-files'
            or any(type(v) is not int or not 0 < v < 2**63 for v in asdict(limits).values())
            or limits.max_records > 1000 or type(scope.products) is not tuple
            or not 1 <= len(scope.products) <= limits.max_records
            or type(scope.scope_id) is not str or not scope.scope_id
            or type(scope.database_identity) is not tuple or len(scope.database_identity) != 5
            or any(type(n) is not int or n < 0 for n in scope.database_identity)):
        _fail('bound-selection-required')
    pins = (scope.full_contract_sha256, scope.qualification_sha256, scope.candidate_sha256,
        scope.lookup_artifact_sha256, scope.lookup_review_sha256, scope.derivation_review_sha256,
        scope.custody_review_sha256, scope.operation_evidence_sha256, scope.emitter_policy_sha256,
        scope.caller_policy_sha256, scope.expected_ids_sha256)
    if (any(not _sha(p) for p in pins)
            or any(type(a) is not Asset or not _valid_asset(a) or not valid_input_name(a.path)
                   or a.bytes <= 0 for a in (scope.archive, scope.database, scope.normalization_manifest))
            or scope.database.bytes > limits.max_database_bytes
            or scope.database_identity[2] != scope.database.bytes
            or scope.archive not in contract.inputs
            or scope.normalization_manifest.bytes > limits.max_manifest_bytes
            or type(manifest) is not bytes or len(manifest) != scope.normalization_manifest.bytes
            or hashlib.sha256(manifest).hexdigest() != scope.normalization_manifest.sha256):
        _fail('derivation-binding-required')
    if (type(binding_evidence) is not bytes or not 0 < len(binding_evidence) <= limits.max_manifest_bytes
            or hashlib.sha256(binding_evidence).hexdigest() != scope.operation_evidence_sha256):
        _fail('selected-operation-evidence-required')
    bound = asdict(scope)
    del bound['operation_evidence_sha256']  # Independently selected root, never self-referential.
    if canonical(strict_json(binding_evidence)) != canonical({
            'schemaVersion': 'offmenu-selected-origin-binding/1', 'scope': bound, 'limits': asdict(limits)}):
        _fail('selected-operation-binding-mismatch')
    q = _binding(contract, qualification, scope.qualification_sha256)  # Metadata only.
    context = scope.context
    context.validate()
    if (contract_fingerprint(contract) != scope.full_contract_sha256
            or q['candidateSha256'] != scope.candidate_sha256
            or (context.release_id, context.acquired_at) != (contract.release_id, contract.acquired_at)
            or context.rights_evidence_sha256 != contract.rights_evidence.sha256
            or context.scope_evidence_sha256 != contract.scope_evidence.sha256
            or context.acquisition_clock_status != contract.acquisition_clock_status
            or context.clock_evidence_sha256 != (contract.clock_evidence.sha256 if contract.clock_evidence else None)):
        _fail('qualified-context-mismatch')
    if type(scope.members) is not tuple or len(scope.members) != 2:
        _fail('exact-members-required')
    try:
        members = dict(scope.members)
        if set(members) != {'food', 'branded_food'}:
            raise ValueError()
        for table, member in scope.members:
            if (not valid_input_name(member) or PurePosixPath(member).stem != table
                    or PurePosixPath(member).suffix.lower() != '.csv'):
                raise ValueError()
    except (TypeError, ValueError):
        _fail('exact-members-required')
    ids = set(); keys = set(); previous = 0
    for item in scope.products:
        if (type(item) is not SelectedProduct or not _sha(item.record_sha256)
                or type(item.source_record_id) is not str or not item.source_record_id
                or type(item.id) is not str or item.id != 'usda-files:product:' + item.source_record_id
                or item.id in ids or item.source_record_id in keys
                or type(item.candidate_line) is not int or item.candidate_line <= previous
                or item.candidate_line > contract.expected_records
                or any(type(row) is not RowPin or type(row.ordinal) is not int
                       or row.ordinal <= 0 or not _sha(row.body_sha256)
                       for row in (item.food, item.branded_food))):
            _fail('selected-membership-or-row-binding')
        ids.add(item.id); keys.add(item.source_record_id); previous = item.candidate_line
    if ids_digest(ids) != scope.expected_ids_sha256:
        _fail('selected-id-digest')
    value = strict_json(manifest)
    raw_pin = {**asdict(scope.archive), 'path': Path(scope.archive.path).name, 'role': 'archive'}
    if (type(value) is not dict or value.get('schemaVersion') != 'offmenu-product-candidate/2'
            or value.get('status') != 'normalized-candidate'
            or (value.get('sourceId'), value.get('releaseId')) != ('usda-files', context.release_id)
            or value.get('normalizedRecords') != contract.expected_records
            or value.get('candidateSha256') != scope.candidate_sha256
            or value.get('outputHashes') != {'source.sqlite': scope.database.sha256,
                                             'candidate.jsonl': scope.candidate_sha256}
            or value.get('inputFiles') != [raw_pin]
            or value.get('contract', {}).get('inputFiles') != [raw_pin]
            or value.get('contract', {}).get('adapterVersion') != PRODUCER_VERSION
            or canonical(value.get('contract', {}).get('context')) != canonical(asdict(context))):
        _fail('normalization-derivation-mismatch')
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != scope.caller_policy_sha256:
        _fail('caller-policy-mismatch')
    if (hashlib.sha256(Path(origin_policy.__file__).read_bytes()).hexdigest() != scope.emitter_policy_sha256
            or hashlib.sha256(Path(origin_policy.adapters.__file__).read_bytes()).hexdigest() != origin_policy.ADAPTER_SHA256):
        _fail('emitter-policy-mismatch')
    return members


def _check_database(path, scope, fd=None):
    info = safe_path(path).lstat()
    if (not stat.S_ISREG(info.st_mode) or _signature(info) != scope.database_identity
            or (fd is not None and _signature(os.fstat(fd)) != scope.database_identity)):
        _fail('database-custody-changed')
    for suffix in ('-wal', '-shm', '-journal'):
        try: path.with_name(path.name+suffix).lstat()
        except FileNotFoundError: continue
        _fail('database-sidecar-present')


def _open_database(path, scope):
    # Same qualified serialized Linux/defaultSQLite FD-attribution contract as
    # the accepted partition core. No basename-only inode agreement inference.
    if threading.active_count() != 1 or len(os.listdir('/proc/self/task')) != 1:
        _fail('serialized-database-setup-required')
    _check_database(path, scope)
    before = _descriptor_snapshot(); db = None; held = None
    try:
        db = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)
        db.execute('PRAGMA user_version').fetchone()
        after = _descriptor_snapshot()
        opened = [fd for fd, info in after.items() if fd not in before
                  or (info.st_dev, info.st_ino) != (before[fd].st_dev, before[fd].st_ino)]
        if (threading.active_count() != 1 or len(os.listdir('/proc/self/task')) != 1
                or len(opened) != 1 or not stat.S_ISREG(after[opened[0]].st_mode)):
            _fail('database-descriptor-ambiguous')
        held = os.dup(opened[0]); _check_database(path, scope, held)
        return db, held
    except BaseException:
        if db is not None: db.close()
        if held is not None: os.close(held)
        raise


class _SelectedRows:
    """Emitter's existing query surface -> explicit selected ordinal point reads."""
    def __init__(self, db, scope, limits, deadline):
        self.db, self.scope, self.limits, self.deadline = db, scope, limits, deadline
        self.products = {p.source_record_id: p for p in scope.products}
        self.cache = {}; self.rows = self.bytes = 0

    def row(self, table, key):
        _guard(self.deadline)
        if table not in ('food', 'branded_food') or key not in self.products:
            _fail('unselected-source-query')
        token = table, key
        if token not in self.cache:
            pin = getattr(self.products[key], table)
            sql = 'SELECT ordinal,identity,body FROM raw WHERE tab=? AND ordinal=? LIMIT 2'
            plan = self.db.execute('EXPLAIN QUERY PLAN '+sql, (table, pin.ordinal)).fetchall()
            if not plan or any(re.match(r'^\s*(?:SCAN\b|USE\s+TEMP\s+B-TREE\b)', str(p[3]), re.I) for p in plan):
                _fail('unbounded-source-query')
            point_search = False
            for step in plan:
                detail = str(step[3])
                terms = re.search(r'\(([^()]*)\)\s*$', detail)
                if re.match(r'^SEARCH\s+raw\b', detail, re.I) and terms:
                    constraints = {re.sub(r'\s+', '', term).lower()
                                   for term in re.split(r'\s+AND\s+', terms[1], flags=re.I)}
                    point_search |= {'tab=?', 'ordinal=?'} <= constraints
            if not point_search:
                _fail('composite-point-index-required')
            cursor = self.db.execute(sql, (table, pin.ordinal))
            try: found = cursor.fetchmany(2)
            finally: cursor.close()
            _guard(self.deadline)
            if len(found) != 1:
                _fail('source-row-missing-or-ambiguous')
            ordinal, identity, body = found[0]
            if type(body) is not str:
                _fail('source-row-invalid')
            raw = body.encode('utf-8'); self.rows += 1; self.bytes += len(raw)
            if len(raw) > self.limits.max_row_bytes or self.bytes > self.limits.max_source_row_bytes:
                _fail('source-row-byte-bound')
            if (ordinal != pin.ordinal or identity != key or hashlib.sha256(raw).hexdigest() != pin.body_sha256):
                _fail('source-row-derivation-mismatch')
            value = strict_json(raw)
            if type(value) is not dict or value.get('fdc_id') != key:
                _fail('source-row-key-mismatch')
            self.cache[token] = ordinal, body
        return self.cache[token]

    def execute(self, sql, parameters):
        if sql == 'SELECT ordinal,body FROM raw WHERE tab=? AND identity=?':
            return _One(self.row(*parameters))
        if sql == 'SELECT 1 FROM raw WHERE tab="branded_food" AND identity=?':
            self.row('branded_food', parameters[0]); return _One((1,))
        _fail('unselected-source-query')


class _One:
    def __init__(self, value): self.value = value
    def fetchone(self): return self.value


def emit_selected_usda_product_origins(records, *, scope, limits, contract, qualification,
                                       normalization_manifest, binding_evidence, database_root):
    """Emit complete scalar origins for the exact independently selected products.

    Supplied records are already bounded selected native values, not a candidate
    path to scan. Fresh database identity/hash/custody review must be qualified
    OUTSIDE this caller and bound in trusted application scope before any access.
    This function checks actual open-file agreement but does not manufacture that
    review by hashing its own observations. No real scope factory is installed.
    """
    if type(limits) is not SelectedOriginLimits or type(limits.max_seconds) is not int or limits.max_seconds <= 0:
        _fail('explicit-limits-required')
    deadline = time.monotonic()+limits.max_seconds
    members = _validate(scope, limits, contract, qualification, normalization_manifest, binding_evidence)
    _guard(deadline)
    if type(records) is not tuple or len(records) != len(scope.products):
        _fail('bounded-selected-buffer-required')
    selected = []; size = 0
    for index, record in enumerate(records):
        _guard(deadline)
        if index >= len(scope.products): _fail('unselected-record')
        raw = canonical(record); size += len(raw); item = scope.products[index]
        if len(raw) > limits.max_record_bytes or size > limits.max_input_bytes:
            _fail('selected-input-bound')
        record = strict_json(raw)  # Check and emit the same private byte snapshot.
        p = record.get('provenance', {}) if type(record) is dict else {}
        if (type(record) is not dict or type(p) is not dict
                or record.get('kind') != 'product' or record.get('id') != item.id
                or hashlib.sha256(raw).hexdigest() != item.record_sha256
                or p.get('recordId') != item.source_record_id or p.get('sourceRow') != item.food.ordinal
                or (p.get('sourceId'), p.get('releaseId'), p.get('fetchedAt')) !=
                   ('usda-files', scope.context.release_id, scope.context.acquired_at)
                or p.get('inputSha256') != {'archive': scope.archive.sha256}
                or p.get('visibility') != 'private-candidate' or 'fieldOrigins' in p):
            _fail('selected-record-binding-mismatch')
        selected.append(record)
    if len(selected) != len(scope.products): _fail('selected-record-count')
    path = safe_path(Path(database_root)/scope.database.path)
    db, held = _open_database(path, scope)
    try:
        steps = [0]
        def progress():
            steps[0] += 1
            return int(steps[0] > limits.max_sqlite_steps or time.monotonic() >= deadline)
        db.set_progress_handler(progress, 1)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, max(limits.max_row_bytes, 4096))
        view = _SelectedRows(db, scope, limits, deadline)
        emitter_limits = ProductLimits(max_input_bytes=limits.max_input_bytes,
            max_expanded_bytes=limits.max_source_row_bytes, max_line_bytes=limits.max_record_bytes,
            max_rows=limits.max_records, max_output_bytes=limits.max_output_bytes,
            max_database_bytes=limits.max_database_bytes, max_archive_members=2, max_nutrients_per_food=1)
        emitter = ProductOriginEmitter(scope.context, view,
            {'archive': {'path': scope.archive.path, 'sha256': scope.archive.sha256}},
            members=members, limits=emitter_limits)
        if emitter.policy != scope.emitter_policy_sha256: _fail('emitter-policy-mismatch')
        output = []; output_bytes = 0
        for record in selected:
            _guard(deadline)
            enriched = emitter.emit(record)  # usda/SourceRow.leaf/full field_origin_errors.
            if field_origin_errors(enriched, emitter.pins, policy_pins=[scope.emitter_policy_sha256]):
                _fail('complete-origin-inventory-required')
            raw = canonical(enriched); output_bytes += len(raw)
            if output_bytes > limits.max_output_bytes: _fail('output-bound')
            output.append(enriched)
        db.close(); db = None
        _check_database(path, scope, held)
        if (hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != scope.caller_policy_sha256
                or hashlib.sha256(Path(origin_policy.__file__).read_bytes()).hexdigest()
                   != scope.emitter_policy_sha256):
            _fail('implementation-changed')
        _guard(deadline)
        result = {'schemaVersion': VERSION, 'selectedScopeId': scope.scope_id,
            'fullContractSha256': scope.full_contract_sha256, 'qualificationSha256': scope.qualification_sha256,
            'lookupArtifactSha256': scope.lookup_artifact_sha256, 'lookupReviewSha256': scope.lookup_review_sha256,
            'derivationReviewSha256': scope.derivation_review_sha256, 'custodyReviewSha256': scope.custody_review_sha256,
            'operationEvidenceSha256': scope.operation_evidence_sha256,
            'normalizationManifestSha256': scope.normalization_manifest.sha256,
            'databaseSha256': scope.database.sha256, 'databaseIdentity': scope.database_identity,
            'archive': asdict(scope.archive), 'archiveMembers': members,
            'emitterPolicySha256': scope.emitter_policy_sha256, 'callerPolicySha256': scope.caller_policy_sha256,
            'selectedCount': len(output), 'selectedIdsSha256': scope.expected_ids_sha256,
            'originCoverage': 'complete-data-scalars', 'records': output,
            'measurements': {'pointRowsRead': view.rows, 'sourceRowBytes': view.bytes,
                             'selectedInputBytes': size, 'recordOutputBytes': output_bytes,
                             'sqliteProgressStepsObserved': steps[0]}, 'limits': asdict(limits),
            'fixture': contract.fixture, 'accepted': False, 'qualified': False,
            'originalArchiveRead': False, 'fullDatabaseHashPerformed': False,
            'candidateScanPerformed': False, 'identityOrIngredientEdges': 0,
            'runtimeOrResourcesAdmitted': False}
        if len(canonical(result)) > limits.max_output_bytes: _fail('output-bound')
        return result
    finally:
        try:
            if db is not None: db.close()
        finally: os.close(held)
