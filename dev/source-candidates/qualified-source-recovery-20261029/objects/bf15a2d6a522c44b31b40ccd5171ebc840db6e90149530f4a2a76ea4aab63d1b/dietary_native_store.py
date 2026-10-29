"""Opt-in LOCAL source-faithful Dietary importer. No source factory or service.

Trusted Python callers supply reviewed native contracts and execution selection.
Generated fixtures exercise this code; real-body execution belongs to runtime57.
The schema is an exact copy of sole DDL owner13's dietary-native-store-v1.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import threading
import time

from .acceptance import SourceContract
from .core import RefreshError, canonical
from .native_barcode_lookup import _binding, _identity
from .product_adapters import _safe
from .product_input_witness import _rename_noreplace
from .off_partition_witness import _descriptor_snapshot

VERSION = 'offmenu-native-dietary-sqlite/1'
SCHEMA_SHA256 = 'c37ac158bbd970e53616ae382c57227a0004d1fbfe902cbb8cf55c8610b260d3'
INTERFACE_SHA256 = '66da03eec5045fbf233d22f09d8f0ab9951a910649964be6f95824baf972a8eb'
ENTRY_ENCODING = 'sorted-UTF8-exact-decimal-JSON-no-LF/1'
DDL = "-- NEW PRIVATE source-faithful Dietary store. Never apply to identifier DB.\nCREATE TABLE dietary_load (\n load_id TEXT PRIMARY KEY NOT NULL,\n input_manifest_sha256 TEXT NOT NULL,\n parse_engine_id TEXT NOT NULL, parse_engine_version TEXT NOT NULL, parse_engine_sha256 TEXT NOT NULL,\n state TEXT NOT NULL CHECK(state IN ('loading','incomplete','completed','failed')),\n expected_packets INTEGER NOT NULL CHECK(expected_packets>=0),\n expected_profile_packets INTEGER NOT NULL CHECK(expected_profile_packets>=0),\n expected_other_packets INTEGER NOT NULL CHECK(expected_other_packets>=0),\n read_packets INTEGER CHECK(read_packets>=0), unread_packets INTEGER CHECK(unread_packets>=0),\n observation_entries INTEGER CHECK(observation_entries>=0),\n created_at TEXT NOT NULL, modified_at TEXT, removed_at TEXT, created_by TEXT,\n owner_actor_reference TEXT, access_policy_reference TEXT,\n CHECK(expected_packets=expected_profile_packets+expected_other_packets)\n);\nCREATE TABLE dietary_input (\n input_id TEXT PRIMARY KEY NOT NULL,\n load_id TEXT NOT NULL REFERENCES dietary_load(load_id),\n source_id TEXT NOT NULL, release_id TEXT NOT NULL,\n asset_id TEXT, citation_id TEXT, citation_state TEXT NOT NULL,\n candidate_sha256 TEXT NOT NULL, candidate_bytes INTEGER NOT NULL CHECK(candidate_bytes>=0),\n provenance_manifest_sha256 TEXT NOT NULL, operation_evidence_sha256 TEXT NOT NULL,\n qualification_sha256 TEXT NOT NULL,\n original_acquired_at TEXT, acquisition_clock_state TEXT NOT NULL\n);\nCREATE TABLE dietary_packet_audit (\n packet_id TEXT PRIMARY KEY NOT NULL,\n input_id TEXT NOT NULL REFERENCES dietary_input(input_id),\n packet_ordinal INTEGER NOT NULL CHECK(packet_ordinal>=1),\n native_kind TEXT, native_record_id TEXT, source_record_id TEXT,\n source_row_json TEXT,\n packet_sha256 TEXT NOT NULL, source_pointer TEXT NOT NULL,\n disposition TEXT NOT NULL CHECK(disposition IN ('profile-stored','other-kind','quarantined','failed')),\n reason_code TEXT,\n UNIQUE(input_id,packet_ordinal)\n);\nCREATE TABLE native_nutrient_profile (\n profile_id TEXT PRIMARY KEY NOT NULL,\n packet_id TEXT NOT NULL UNIQUE REFERENCES dietary_packet_audit(packet_id),\n original_food_name_json TEXT, original_language TEXT, language_state TEXT NOT NULL,\n native_packet_json TEXT NOT NULL,\n document_sha256 TEXT NOT NULL,\n identifiers_json TEXT, profile_basis_json TEXT,\n field_states_json TEXT NOT NULL,\n nutrients_state TEXT NOT NULL,\n observed_entry_count INTEGER NOT NULL CHECK(observed_entry_count>=0),\n canonical_food_id TEXT, canonical_ingredient_id TEXT,\n semantic_link_status TEXT NOT NULL,\n provenance_json TEXT NOT NULL\n);\nCREATE TABLE native_nutrient_observation (\n observation_id TEXT PRIMARY KEY NOT NULL,\n profile_id TEXT NOT NULL REFERENCES native_nutrient_profile(profile_id),\n entry_ordinal INTEGER NOT NULL CHECK(entry_ordinal>=1),\n original_entry_key TEXT COLLATE BINARY NOT NULL,\n entry_pointer TEXT NOT NULL, entry_sha256 TEXT NOT NULL,\n source_nutrient_id_json TEXT, source_row_id_json TEXT, source_name_json TEXT,\n source_amount_json TEXT, interpreted_value_json TEXT,\n source_unit_json TEXT, unit_json TEXT, basis_json TEXT, method_json TEXT,\n field_states_json TEXT NOT NULL,\n source_disposition TEXT NOT NULL CHECK(source_disposition IN ('stored','unresolved','quarantined')),\n canonical_nutrient_id TEXT, canonical_unit_id TEXT,\n normalization_status TEXT NOT NULL,\n UNIQUE(profile_id,entry_ordinal)\n);\nCREATE TABLE dietary_exception (\n load_id TEXT NOT NULL REFERENCES dietary_load(load_id),\n exception_ordinal INTEGER NOT NULL CHECK(exception_ordinal>=1),\n packet_id TEXT REFERENCES dietary_packet_audit(packet_id),\n observation_id TEXT REFERENCES native_nutrient_observation(observation_id),\n source_pointer TEXT NOT NULL, reason_code TEXT NOT NULL,\n disposition TEXT NOT NULL,\n PRIMARY KEY(load_id,exception_ordinal)\n);\nCREATE INDEX dietary_profile_record ON dietary_packet_audit(input_id,native_record_id,packet_ordinal);\nCREATE INDEX dietary_packet_disposition ON dietary_packet_audit(input_id,disposition,packet_ordinal);\nCREATE INDEX dietary_observation_profile ON native_nutrient_observation(profile_id,entry_ordinal);\nCREATE INDEX dietary_observation_source_key ON native_nutrient_observation(original_entry_key,observation_id);\nCREATE VIEW v_dietary_profile_inspection AS\nSELECT p.profile_id,a.native_record_id,a.source_record_id,a.packet_ordinal,\n i.source_id,i.release_id,p.original_food_name_json,p.original_language,p.language_state,\n p.profile_basis_json,p.nutrients_state,p.observed_entry_count,p.semantic_link_status,\n i.citation_id,i.citation_state,a.source_pointer,p.provenance_json\nFROM native_nutrient_profile p\nJOIN dietary_packet_audit a USING(packet_id)\nJOIN dietary_input i USING(input_id);\nCREATE VIEW v_dietary_observation_inspection AS\nSELECT o.*,a.native_record_id,a.source_record_id,i.source_id,i.release_id,\n i.citation_id,i.citation_state\nFROM native_nutrient_observation o\nJOIN native_nutrient_profile p USING(profile_id)\nJOIN dietary_packet_audit a USING(packet_id)\nJOIN dietary_input i USING(input_id);\n"


@dataclass(frozen=True)
class DietaryInput:
    candidate: str
    candidate_bytes: int
    identity: tuple
    contract: SourceContract
    qualification: dict
    qualification_sha256: str
    expected_profiles: int
    expected_products: int
    provenance_manifest_sha256: str
    operation_evidence_sha256: str
    asset_id: str | None = None
    citation_id: str | None = None
    citation_state: str = 'pending'


@dataclass(frozen=True)
class DietaryLimits:
    max_scan_bytes: int
    max_packets: int
    max_line_bytes: int
    max_observations: int
    max_entries_per_profile: int
    max_exceptions: int
    max_database_bytes: int
    max_storage_bytes: int
    max_seconds: int
    commit_every_packets: int = 1000


def _fail(code):
    raise RefreshError('dietary-' + code)


def _sha(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def _json(value):
    """Exact decimal numeric JSON columns; original spelling remains in document.

    This is also the named entry digest encoding, not an input span hash.
    """
    if value is None: return 'null'
    if type(value) is bool: return 'true' if value else 'false'
    if type(value) is int: return str(value)
    if type(value) is Decimal:
        if not value.is_finite(): _fail('nonfinite-number')
        return str(value)
    if type(value) is str: return json.dumps(value, ensure_ascii=False)
    if type(value) is list: return '[' + ','.join(_json(v) for v in value) + ']'
    if type(value) is dict:
        return '{' + ','.join(_json(k) + ':' + _json(value[k]) for k in sorted(value)) + '}'
    _fail('unsupported-json-value')


def _parse(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result: _fail('duplicate-json-key')
            result[key] = value
        return result
    def nonfinite(_): _fail('nonfinite-number')
    return json.loads(raw, parse_float=Decimal, parse_constant=nonfinite, object_pairs_hook=pairs)


def prepare_dietary_manifest(spec):
    """Snapshot trusted metadata only; never open/stat the candidate body."""
    if type(spec) is not DietaryInput: _fail('input-type')
    q = _binding(spec.contract, spec.qualification, spec.qualification_sha256)
    if (type(spec.candidate) is not str or not spec.candidate
            or type(spec.candidate_bytes) is not int or not 0 < spec.candidate_bytes < 2**63
            or type(spec.identity) is not tuple or len(spec.identity) != 5
            or any(type(n) is not int or n < 0 for n in spec.identity)
            or spec.identity[2] != spec.candidate_bytes
            or any(type(n) is not int or n < 0 for n in (spec.expected_profiles, spec.expected_products))
            or spec.expected_profiles + spec.expected_products != q['normalizedRecords']
            or any(not _sha(v) for v in (spec.provenance_manifest_sha256, spec.operation_evidence_sha256))
            or spec.citation_state not in ('pending', 'unresolved-backfill', 'fetch-bound')
            or any(v is not None and (type(v) is not str or not 0 < len(v) <= 1024)
                   for v in (spec.asset_id, spec.citation_id))
            or (spec.citation_state == 'fetch-bound' and spec.citation_id is None)):
        _fail('input-metadata')
    return {'schemaVersion': VERSION, 'candidate': spec.candidate,
            'candidateBytes': spec.candidate_bytes, 'candidateSha256': q['candidateSha256'],
            'identity': list(spec.identity), 'sourceId': q['sourceId'], 'releaseId': q['releaseId'],
            'expectedPackets': q['normalizedRecords'], 'expectedProfiles': spec.expected_profiles,
            'expectedProducts': spec.expected_products, 'qualificationSha256': spec.qualification_sha256,
            'contractSha256': q['contractSha256'], 'fixture': q['fixture'],
            'provenanceManifestSha256': spec.provenance_manifest_sha256,
            'operationEvidenceSha256': spec.operation_evidence_sha256,
            'assetId': spec.asset_id, 'citationId': spec.citation_id, 'citationState': spec.citation_state,
            'acquiredAt': spec.contract.acquired_at, 'acquisitionClockState': spec.contract.acquisition_clock_status,
            'schemaSha256': SCHEMA_SHA256, 'interfaceSha256': INTERFACE_SHA256,
            'entryEncoding': ENTRY_ENCODING}


def _insert(db, table, values):
    # Table/column names below are exclusively this module's fixed schema names.
    names = ','.join(values)
    marks = ','.join('?' for _ in values)
    db.execute(f'INSERT INTO {table}({names}) VALUES({marks})', tuple(values.values()))


def _state(obj, key, valid):
    if key not in obj: return 'missing'
    if obj[key] is None: return 'null'
    return 'present' if valid(obj[key]) else 'invalid'


def _column(obj, key):
    return _json(obj[key]) if key in obj else None


def _text(v): return type(v) is str and bool(v)
def _number(v): return type(v) in (int, Decimal)
def _id(v): return type(v) in (str, int) and v != ''


OBSERVATION_FIELDS = {
    'sourceNutrientId': ('source_nutrient_id_json', _id),
    'sourceRowId': ('source_row_id_json', _id),
    'sourceName': ('source_name_json', _text),
    'sourceAmount': ('source_amount_json', lambda v: type(v) in (str, int, Decimal)),
    'value': ('interpreted_value_json', _number),
    'sourceUnit': ('source_unit_json', _text), 'unit': ('unit_json', _text),
    'basis': ('basis_json', lambda v: type(v) is dict), 'method': ('method_json', _text),
    'rawFields': (None, lambda v: type(v) is dict),
}
PROFILE_FIELDS = {'foodName': lambda v: type(v) is str,
                  'language': _text, 'identifiers': lambda v: type(v) is list,
                  'basis': lambda v: type(v) is dict, 'nutrients': lambda v: type(v) is dict}


def _exception(db, load_id, packet_id, observation_id, pointer, reason, disposition, stats, limits):
    if stats['exceptions'] >= limits.max_exceptions: _fail('exception-bound')
    stats['exceptions'] += 1
    _insert(db, 'dietary_exception', dict(load_id=load_id, exception_ordinal=stats['exceptions'],
            packet_id=packet_id, observation_id=observation_id, source_pointer=pointer,
            reason_code=reason, disposition=disposition))


def _field_counts(stats, scope, states):
    for field, state in states.items():
        counts = stats[scope].setdefault(field, {})
        counts[state] = counts.get(state, 0) + 1


def _packet(db, raw, ordinal, m, load_id, stats, limits, check):
    packet_id = 'packet:' + m['candidateSha256'] + ':' + str(ordinal)
    packet_sha = hashlib.sha256(raw).hexdigest()
    audit = dict(packet_id=packet_id, input_id=m['candidateSha256'], packet_ordinal=ordinal,
                 native_kind=None, native_record_id=None, source_record_id=None,
                 source_row_json=None, packet_sha256=packet_sha, source_pointer='/0',
                 disposition='quarantined', reason_code='malformed-or-wrong-scope')
    row = None
    try:
        document = raw.decode('utf-8')
        value = _parse(document)
        # Encoding also rejects unpaired surrogates, nonfinite values and excessive recursion.
        _json(value).encode('utf-8')
        if type(value) is list and len(value) == 1 and type(value[0]) is dict:
            candidate = value[0]; provenance = candidate.get('provenance')
            if (type(provenance) is dict
                    and (provenance.get('sourceId'), provenance.get('releaseId')) == (m['sourceId'], m['releaseId'])
                    and provenance.get('visibility') == 'private-candidate'
                    and _text(candidate.get('id')) and _text(provenance.get('recordId'))
                    and candidate.get('kind') in ('product', 'nutrientProfile')):
                row = candidate
    except (ValueError, TypeError, UnicodeError, RecursionError, ArithmeticError):
        pass
    if row is None:
        _insert(db, 'dietary_packet_audit', audit)
        _exception(db, load_id, packet_id, None, '/0', audit['reason_code'], 'quarantined', stats, limits)
        stats['quarantinedPackets'] += 1
        return
    provenance = row['provenance']; kind = row['kind']
    audit.update(native_kind=kind, native_record_id=row['id'], source_record_id=provenance['recordId'],
                 source_row_json=_column(provenance, 'sourceRow'),
                 disposition='other-kind' if kind == 'product' else 'profile-stored', reason_code=None)
    _insert(db, 'dietary_packet_audit', audit)
    if kind == 'product':
        stats['products'] += 1
        return
    stats['profiles'] += 1
    data = row.get('data'); data_valid = type(data) is dict
    if not data_valid: data = {}
    states = {k: _state(data, k, valid) for k, valid in PROFILE_FIELDS.items()}
    states['data'] = _state(row, 'data', lambda v: type(v) is dict)
    nutrients = data.get('nutrients')
    nutrient_state = states['nutrients']
    if nutrient_state == 'present': nutrient_state = 'object' if nutrients else 'empty'
    entries = nutrients if type(nutrients) is dict else {}
    if len(entries) > limits.max_entries_per_profile: _fail('profile-entry-bound')
    if stats['observations'] + len(entries) > limits.max_observations: _fail('observation-bound')
    profile_id = packet_id + ':profile'
    _insert(db, 'native_nutrient_profile', dict(profile_id=profile_id, packet_id=packet_id,
        original_food_name_json=_column(data, 'foodName'),
        original_language=data.get('language') if states['language'] == 'present' else None,
        language_state='source-explicit' if states['language'] == 'present' else 'unknown',
        native_packet_json=document, document_sha256=packet_sha,
        identifiers_json=_column(data, 'identifiers'), profile_basis_json=_column(data, 'basis'),
        field_states_json=_json(states), nutrients_state=nutrient_state, observed_entry_count=len(entries),
        canonical_food_id=None, canonical_ingredient_id=None, semantic_link_status='pending',
        provenance_json=_json(provenance)))
    _field_counts(stats, 'profileFields', states)
    if not data_valid or nutrient_state in ('missing', 'null', 'invalid'):
        _exception(db, load_id, packet_id, None, '/0/data/nutrients',
                   'profile-data-or-nutrient-container-' + nutrient_state, 'unresolved', stats, limits)
    stats['nutrientsStates'][nutrient_state] = stats['nutrientsStates'].get(nutrient_state, 0) + 1
    for index, (key, value) in enumerate(entries.items(), 1):
        check()
        pointer = '/0/data/nutrients/' + key.replace('~', '~0').replace('/', '~1')
        observation_id = 'observation:' + hashlib.sha256(canonical([profile_id, key, index])).hexdigest()
        entry = value if type(value) is dict else {}
        fields = {k: _state(entry, k, valid) for k, (_, valid) in OBSERVATION_FIELDS.items()}
        fields['entry'] = 'present' if type(value) is dict else 'invalid'
        disposition = ('quarantined' if 'invalid' in fields.values() else
                       'unresolved' if any(v in ('null', 'missing') for v in fields.values()) else 'stored')
        columns = {col: _column(entry, field) for field, (col, _) in OBSERVATION_FIELDS.items() if col}
        _insert(db, 'native_nutrient_observation', dict(observation_id=observation_id, profile_id=profile_id,
                entry_ordinal=index, original_entry_key=key, entry_pointer=pointer,
                entry_sha256=hashlib.sha256(_json(value).encode('utf-8')).hexdigest(),
                **columns, field_states_json=_json(fields), source_disposition=disposition,
                canonical_nutrient_id=None, canonical_unit_id=None, normalization_status='pending'))
        stats['observations'] += 1
        stats['observationDispositions'][disposition] += 1
        _field_counts(stats, 'observationFields', fields)
        if disposition != 'stored':
            _exception(db, load_id, packet_id, observation_id, pointer,
                       'observation-fields-' + disposition, disposition, stats, limits)


def _checkpoint(db, load_id, expected, state, counts=None):
    # Running checkpoints use bounded scalar counters, avoiding repeated full
    # scans of the growing observation table. Terminal/failure reconciliation
    # reads actual SQL counts once.
    if counts is None:
        read = db.execute('SELECT count(*) FROM dietary_packet_audit').fetchone()[0]
        observations = db.execute('SELECT count(*) FROM native_nutrient_observation').fetchone()[0]
    else:
        read, observations = counts
    db.execute('UPDATE dietary_load SET state=?,read_packets=?,unread_packets=?,observation_entries=?,modified_at=? WHERE load_id=?',
               (state, read, max(0, expected-read), observations, datetime.now(timezone.utc).isoformat(), load_id))
    db.commit()


def build_dietary_database(spec, destination, *, limits, load_id, input_manifest_sha256,
                           selection_receipt_sha256):
    """Create one exclusive private DB; failed stages retained, never auto-resumed.

    This callable is not an authority factory, OS sandbox, or real-data admission.
    An exact independently selected manifest/operation and57 runtime are required.
    Input hash, EOF, counts and held-FD identity are verified in the parsing pass.
    """
    m = prepare_dietary_manifest(spec)
    if (type(limits) is not DietaryLimits
            or any(type(v) is not int or not 0 < v < 2**63 for v in limits.__dict__.values())
            or limits.max_line_bytes > 8*1024**2
            or not _text(load_id) or len(load_id) > 256
            or not _sha(input_manifest_sha256) or not _sha(selection_receipt_sha256)):
        _fail('limits-or-selection')
    manifest_sha = hashlib.sha256(canonical(m)).hexdigest()
    if manifest_sha != input_manifest_sha256: _fail('selected-manifest-mismatch')
    if (hashlib.sha256(DDL.encode()).hexdigest() != SCHEMA_SHA256
            or m['candidateBytes'] > min(limits.max_scan_bytes, spec.contract.max_output_bytes)
            or m['expectedPackets'] > limits.max_packets): _fail('scope-or-schema-bound')
    target = Path(destination)
    if target.suffix != '.sqlite': _fail('destination')
    parent = _safe(target.parent)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    stage_fd = file_fd = input_fd = held = None
    db = None; stage = None; published = False; start = time.monotonic()
    stats = {'profiles': 0, 'products': 0, 'quarantinedPackets': 0, 'observations': 0,
             'exceptions': 0, 'profileFields': {}, 'observationFields': {}, 'nutrientsStates': {},
             'observationDispositions': dict.fromkeys(('stored', 'unresolved', 'quarantined'), 0)}
    observed = {'bytes': 0, 'packets': 0, 'eofVerified': False}
    try:
        if stat.S_IMODE(os.fstat(parent_fd).st_mode) != 0o700: _fail('private-parent-required')
        parent_identity = (os.fstat(parent_fd).st_dev, os.fstat(parent_fd).st_ino)
        try: os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError: pass
        else: _fail('destination-exists')
        stage = '.dietary-load-' + secrets.token_hex(16)
        os.mkdir(stage, 0o700, dir_fd=parent_fd)
        stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        stage_identity = (os.fstat(stage_fd).st_dev, os.fstat(stage_fd).st_ino)
        file_fd = os.open('data.sqlite', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=stage_fd)
        inode = (os.fstat(file_fd).st_dev, os.fstat(file_fd).st_ino)
        checks = [0]
        def check(force=False):
            if time.monotonic() - start >= limits.max_seconds: _fail('time-bound')
            checks[0] += 1
            if not force and checks[0] % 128: return
            if ((os.stat(parent).st_dev, os.stat(parent).st_ino) != parent_identity
                    or (os.stat(stage, dir_fd=parent_fd, follow_symlinks=False).st_dev,
                        os.stat(stage, dir_fd=parent_fd, follow_symlinks=False).st_ino) != stage_identity):
                _fail('output-custody')
            if not published:
                info = os.stat('data.sqlite', dir_fd=stage_fd, follow_symlinks=False)
                if (info.st_dev, info.st_ino) != inode or not stat.S_ISREG(info.st_mode): _fail('output-custody')
            total = 0
            for name in os.listdir(stage_fd):
                info = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
                if name not in ('data.sqlite', 'data.sqlite-journal') or not stat.S_ISREG(info.st_mode):
                    _fail('unexpected-stage-entry')
                total += info.st_blocks * 512
            if total > limits.max_storage_bytes or os.fstat(file_fd).st_size > limits.max_database_bytes:
                _fail('storage-bound')
        if threading.active_count() != 1 or len(os.listdir('/proc/self/task')) != 1:
            _fail('serialized-default-sqlite-required')
        before = _descriptor_snapshot()
        db = sqlite3.connect(f'/proc/self/fd/{stage_fd}/data.sqlite')
        after = _descriptor_snapshot()
        new = [fd for fd, i in after.items() if fd not in before or (i.st_dev, i.st_ino) != (before[fd].st_dev, before[fd].st_ino)]
        if len(new) != 1 or (after[new[0]].st_dev, after[new[0]].st_ino) != inode:
            _fail('sqlite-descriptor-ambiguous')
        held = os.dup(new[0])
        for statement in ('PRAGMA foreign_keys=ON', 'PRAGMA journal_mode=DELETE', 'PRAGMA temp_store=MEMORY',
                          'PRAGMA cache_size=-8192', 'PRAGMA mmap_size=0', 'PRAGMA synchronous=FULL'):
            db.execute(statement)
        page = db.execute('PRAGMA page_size').fetchone()[0]
        db.execute('PRAGMA max_page_count=' + str(max(1, limits.max_database_bytes // page)))
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, min(2**31-1, limits.max_line_bytes*4))
        db.set_progress_handler(lambda: int(time.monotonic() - start >= limits.max_seconds), 1000)
        db.executescript(DDL)
        _insert(db, 'dietary_load', dict(load_id=load_id, input_manifest_sha256=manifest_sha,
            parse_engine_id='deterministic-native-dietary-import', parse_engine_version=VERSION,
            parse_engine_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), state='loading',
            expected_packets=m['expectedPackets'], expected_profile_packets=m['expectedProfiles'],
            expected_other_packets=m['expectedProducts'], created_at=datetime.now(timezone.utc).isoformat()))
        _insert(db, 'dietary_input', dict(input_id=m['candidateSha256'], load_id=load_id,
            source_id=m['sourceId'], release_id=m['releaseId'], asset_id=m['assetId'],
            citation_id=m['citationId'], citation_state=m['citationState'], candidate_sha256=m['candidateSha256'],
            candidate_bytes=m['candidateBytes'], provenance_manifest_sha256=m['provenanceManifestSha256'],
            operation_evidence_sha256=m['operationEvidenceSha256'], qualification_sha256=m['qualificationSha256'],
            original_acquired_at=m['acquiredAt'], acquisition_clock_state=m['acquisitionClockState']))
        _checkpoint(db, load_id, m['expectedPackets'], 'loading')
        path = _safe(Path(m['candidate']))
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or _identity(info) != spec.identity: _fail('input-custody')
        input_fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        if _identity(os.fstat(input_fd)) != spec.identity: _fail('input-custody')
        digest = hashlib.sha256()
        with os.fdopen(os.dup(input_fd), 'rb') as stream:
            while True:
                check()
                raw = stream.readline(limits.max_line_bytes + 1)
                if not raw:
                    observed['eofVerified'] = True
                    break
                observed['bytes'] += len(raw); observed['packets'] += 1
                if (len(raw) > limits.max_line_bytes or not raw.endswith(b'\n')
                        or observed['bytes'] > m['candidateBytes']
                        or observed['packets'] > m['expectedPackets']): _fail('input-line-or-count-bound')
                digest.update(raw)
                # One packet is the checkpoint unit: no partial observation set survives an error.
                if not db.in_transaction: db.execute('BEGIN')
                db.execute('SAVEPOINT packet')
                try:
                    _packet(db, raw, observed['packets'], m, load_id, stats, limits, check)
                    db.execute('RELEASE packet')
                except BaseException:
                    db.execute('ROLLBACK TO packet'); db.execute('RELEASE packet')
                    raise
                check(True)
                if observed['packets'] % limits.commit_every_packets == 0:
                    _checkpoint(db, load_id, m['expectedPackets'], 'loading',
                                (observed['packets'], stats['observations']))
                    check(True)
        if (_identity(os.fstat(input_fd)) != spec.identity or _identity(_safe(path).stat()) != spec.identity):
            _fail('input-custody')
        if observed['bytes'] != m['candidateBytes'] or digest.hexdigest() != m['candidateSha256']:
            _fail('input-hash-or-size')
        if (observed['packets'] != m['expectedPackets'] or stats['profiles'] != m['expectedProfiles']
                or stats['products'] != m['expectedProducts'] or stats['quarantinedPackets']):
            _fail('input-partition-incomplete')
        counts = {t: db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in
                  ('dietary_packet_audit', 'native_nutrient_profile', 'native_nutrient_observation', 'dietary_exception')}
        if (counts['dietary_packet_audit'] != observed['packets']
                or counts['native_nutrient_profile'] != stats['profiles']
                or counts['native_nutrient_observation'] != stats['observations']
                or counts['dietary_exception'] != stats['exceptions']
                or db.execute('SELECT coalesce(sum(observed_entry_count),0) FROM native_nutrient_profile').fetchone()[0] != stats['observations']
                or db.execute('PRAGMA foreign_key_check').fetchone()
                or db.execute('PRAGMA quick_check').fetchone() != ('ok',)):
            _fail('database-reconciliation')
        _checkpoint(db, load_id, m['expectedPackets'], 'completed')
        db.close(); db = None; check(True); os.fsync(file_fd)
        before_hash = _identity(os.fstat(file_fd)); output_digest = hashlib.sha256(); offset = 0
        while True:
            check(True); block = os.pread(file_fd, 1024**2, offset)
            if not block: break
            output_digest.update(block); offset += len(block)
        hashed_signature = _identity(os.fstat(file_fd))
        if hashed_signature != before_hash or offset != hashed_signature[2]: _fail('database-hash-custody')
        check(True)
        if _identity(os.fstat(file_fd)) != hashed_signature: _fail('database-hash-custody')
        _rename_noreplace(stage_fd, 'data.sqlite', parent_fd, target.name); published = True
        # Rename can change ctime, but must preserve the hashed inode, extent and
        # mtime. Never replace this hash binding with a newly observed signature.
        signature = _identity(os.fstat(file_fd))
        if signature[:4] != hashed_signature[:4] or signature[2] != offset:
            _fail('published-hash-custody')
        os.fsync(file_fd); os.fsync(parent_fd)
        check(True)
        named = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        if (not stat.S_ISREG(named.st_mode) or _identity(named) != signature
                or _identity(os.fstat(file_fd)) != signature):
            _fail('published-final-custody')
        return {'schemaVersion': VERSION, 'database': str(parent/target.name),
                'databaseSha256': output_digest.hexdigest(), 'databaseBytes': offset,
                'databaseIdentity': signature, 'loadId': load_id, 'loadComplete': True,
                'inputManifestSha256': manifest_sha, 'selectionReceiptSha256': selection_receipt_sha256,
                'schemaSha256': SCHEMA_SHA256, 'interfaceSha256': INTERFACE_SHA256,
                'entryEncoding': ENTRY_ENCODING, 'observedInput': observed, 'counts': counts, 'summary': stats,
                'fixture': m['fixture'], 'accepted': False, 'goldAdmitted': False,
                'countryComplete': False, 'runtimeOrResourcesAdmitted': False,
                'retainedStage': str(parent/stage), 'automaticDeletion': False}
    except BaseException as error:
        # Only successful packet units are retained. Receipt counts on failure come
        # from SQLite, never speculative in-memory counters for a rolled-back packet.
        if db is not None:
            try:
                db.rollback(); db.set_progress_handler(None, 0)
                _checkpoint(db, load_id, m['expectedPackets'], 'incomplete')
            except sqlite3.Error:
                pass  # External terminal inspection must reconcile this retained stage.
        error.dietary_retained_state = {'destination': str(target),
            'stage': str(parent/stage) if stage else None, 'published': published,
            'completeReceiptReturned': False, 'observedInput': observed, 'automaticDeletion': False,
            'nextAction': 'Retain stage/database/journal; reconcile durable SQL counts and source scope. No automatic retry/overwrite.'}
        raise
    finally:
        if db is not None: db.close()
        for fd in (input_fd, held, file_fd, stage_fd, parent_fd):
            if fd is not None: os.close(fd)
