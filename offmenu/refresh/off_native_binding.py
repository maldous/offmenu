"""OFF authority from the same pinned normalization manifest and read-only DB.

No real contract/count/rights/resource factory. Only reviewed application
SourceContracts carrying the accepted UnboundOffSemantics select this context.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
import hashlib
from pathlib import Path
import re
import sqlite3
import stat

from .acceptance import SourceContract, _hash_file, _valid_asset, canonical, fingerprint
from .core import RefreshError, strict_json
from . import off_native_policy as policy
from . import product_adapters as adapters
from . import product_clock


@dataclass(frozen=True)
class DerivationPins:
    """Reviewed application constants, NEVER populated from a reusable cache.

    The independent evidence must establish derivation from the exact original,
    context and producer, not merely repeat output self-consistency checks.
    No real pin or evidence constructor is supplied by this module.
    """
    normalization_manifest_sha256: str
    database_sha256: str
    candidate_sha256: str
    independent_review_sha256: str


@dataclass(frozen=True)
class PinnedOffSemantics(policy.UnboundOffSemantics):
    derivation: DerivationPins


def derivation_policy_sha256(semantic):
    """Bind independently selected pins into the trusted SourceContract identity.

    Computing this digest does not make supplied pins independently trustworthy.
    A reviewed application factory must select them from accepted evidence.
    """
    if type(semantic) is not PinnedOffSemantics or type(semantic.derivation) is not DerivationPins:
        _fail('off-source-derivation-required')
    values=asdict(semantic.derivation)
    if any(type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v) for v in values.values()):
        _fail('off-source-derivation-pin-invalid')
    return fingerprint({'version':'off-reviewed-original-derivation/1',
        'policy':policy.policy_descriptor(),'context':asdict(semantic.context),'derivation':values})


def _fail(code):
    raise RefreshError(code)


def _identity(path):
    info=adapters._safe(path).lstat()
    if not stat.S_ISREG(info.st_mode):
        _fail('off-source-authority-file-type')
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def _snapshot(path, maximum, expected):
    before=_identity(path)
    if type(expected) is not str or not re.fullmatch('[0-9a-f]{64}',expected):
        _fail('off-source-authority-pin')
    size,pin=_hash_file(path,maximum)
    after=_identity(path)
    if before!=after or size!=before[2] or pin!=expected:
        _fail('off-source-authority-pin')
    return before


def _sidecars_absent(path):
    for suffix in ('-wal','-shm','-journal'):
        other=path.with_name(path.name+suffix)
        try:other.lstat()
        except FileNotFoundError:continue
        _fail('off-source-authority-sidecar')


def _check_contract(contract, manifest, limits):
    p=contract.semantic_validator
    if type(p) is not PinnedOffSemantics:
        _fail('off-source-derivation-required')
    if contract.policy_sha256!=derivation_policy_sha256(p):
        _fail('off-source-derivation-policy-pin')
    if (type(contract) is not SourceContract
            or policy._context_errors(p.context) or contract.holds
            or contract.source_id!='off' or contract.release_id!=policy.RELEASE
            or contract.output_scope!='native' or contract.output_visibility!='private'
            or not {'retain','parse','transform'}<=set(contract.required_operations)
            or not set(contract.required_operations)<=set(contract.permitted_operations)
            or contract.acquired_at is not None or contract.acquisition_clock_status!='unknown-retained'
            or contract.clock_evidence is None
            or contract.rights_evidence.sha256!=p.context.rights_evidence_sha256
            or contract.scope_evidence.sha256!=p.context.scope_evidence_sha256
            or contract.clock_evidence.sha256!=p.context.clock_evidence_sha256
            or type(contract.expected_records) is not int or contract.expected_records<2
            or contract.expected_records%2 or contract.expected_records>contract.max_records
            or canonical(contract.schemas)!=canonical(policy.native_schemas())
            or contract.schemas_sha256!=fingerprint(contract.schemas)):
        _fail('off-source-authority-contract')
    evidence=(contract.rights_evidence,contract.scope_evidence,contract.clock_evidence)
    if (len(contract.inputs)!=4 or any(not _valid_asset(a) for a in contract.inputs)
            or len({a.path for a in contract.inputs})!=4
            or set(contract.inputs)!={policy.SOURCE,*evidence}
            or sum(a.bytes for a in contract.inputs)>limits.max_input_bytes):
        _fail('off-source-authority-inputs')
    raw_pin={**asdict(policy.SOURCE),'path':Path(policy.SOURCE.path).name,'role':'products'}
    expected={'context':asdict(p.context),'limits':asdict(limits),'inputFiles':[raw_pin],
              'adapterVersion':adapters.VERSION,
              'clockPolicySha256':hashlib.sha256(Path(product_clock.__file__).read_bytes()).hexdigest()}
    if (type(manifest) is not dict or canonical(manifest.get('contract'))!=canonical(expected)
            or manifest.get('sourceId')!='off' or manifest.get('releaseId')!=policy.RELEASE
            or manifest.get('inputRoleMap')!={'products':policy.SOURCE.path}
            or manifest.get('inputFiles')!=[asdict(a) for a in sorted(contract.inputs,key=lambda a:a.path)]):
        _fail('off-source-authority-manifest-context')
    return expected,raw_pin


@contextmanager
def bind_normalized_semantics(contract, normalized, manifest, limits):
    """Lifetime-scoped OFF semantic callback; generic qualify/accept owns inputs.

    The trusted caller passes the direct verified-normalizer result plus its
    normalizationManifestSha256. Source JSON/provenance is not an authority
    constructor. The existing bridge and qualify/accept check original/evidence
    bytes before/after; this context additionally checks their exact manifest
    binding and pins/identities of the normalization metadata and source.sqlite.
    """
    if not isinstance(contract.semantic_validator,policy.UnboundOffSemantics):
        yield contract
        return
    try:
        if type(limits) is not adapters.ProductLimits:_fail('off-source-authority-limits')
        limits.validate()
        expected,raw_pin=_check_contract(contract,manifest,limits)
        root=adapters._safe(normalized)
        manifest_path=adapters._safe(root/'manifest.json')
        db_path=adapters._safe(root/'source.sqlite')
        manifest_pin=manifest.get('normalizationManifestSha256')
        trusted=contract.semantic_validator.derivation
        if (manifest_pin!=trusted.normalization_manifest_sha256
                or manifest.get('outputHashes',{}).get('source.sqlite')!=trusted.database_sha256
                or manifest.get('outputHashes',{}).get('candidate.jsonl')!=trusted.candidate_sha256
                or manifest.get('candidateSha256')!=trusted.candidate_sha256):
            _fail('off-source-derivation-mismatch')
        manifest_identity=_snapshot(manifest_path,1024**2,manifest_pin)
        with manifest_path.open('rb') as stream:
            raw=stream.read(1024**2+1)
        if len(raw)>1024**2:_fail('off-source-authority-normalization-bound')
        if hashlib.sha256(raw).hexdigest()!=manifest_pin or _identity(manifest_path)!=manifest_identity:
            _fail('off-source-authority-normalization-changed')
        original=strict_json(raw)
        if (type(original) is not dict or canonical(original.get('contract'))!=canonical(expected)
                or original.get('inputFiles')!=[raw_pin]
                or original.get('schemaVersion')!='offmenu-product-candidate/2'
                or original.get('status')!='normalized-candidate'
                or original.get('sharedSourceKey')!=hashlib.sha256(adapters.canonical(expected)).hexdigest()
                or set(original.get('outputHashes',{}))!={'source.sqlite','candidate.jsonl'}
                or original.get('rawStorage')!={'path':'source.sqlite','visibility':'private','publishable':False}
                or any(canonical(manifest.get(k))!=canonical(v)
                       for k,v in original.items() if k!='inputFiles')):
            _fail('off-source-authority-normalization-manifest')
        rows=original.get('rawRows')
        if (type(rows) is not int or not 1<=rows<=limits.max_rows
                or original.get('normalizedRecords')!=2*rows
                or original['normalizedRecords']!=contract.expected_records
                or original.get('kinds')!={'product':rows,'nutrientProfile':rows}
                or original.get('candidateSha256')!=original['outputHashes']['candidate.jsonl']):
            _fail('off-source-authority-counts')
        expected_db=original['outputHashes']['source.sqlite']
        _sidecars_absent(db_path)
        db_identity=_snapshot(db_path,limits.max_database_bytes,expected_db)
    except RefreshError:
        raise
    except Exception:
        _fail('off-source-authority-invalid')

    db=None
    active=False
    def semantic(record):
        if not active:return ['off-native-source-authority-expired']
        try:
            key=record['provenance']['recordId']
            if type(key) is not str or not re.fullmatch('[0-9]{4,32}',key):
                return ['off-native-source-identity-invalid']
            cursor=db.execute('SELECT ordinal,identity,body FROM raw WHERE tab=? AND identity=? LIMIT 2',
                              ('products',key))
            try:found=cursor.fetchmany(2)
            finally:cursor.close()
            if len(found)!=1:return ['off-native-source-row-required']
            ordinal,identity,body=found[0]
            if (type(ordinal) is not int or not 1<=ordinal<=rows or identity!=key
                    or type(body) is not str or len(body.encode('utf-8'))>limits.max_line_bytes):
                return ['off-native-source-row-invalid']
            source=strict_json(body)
            if type(source) is not dict or source.get('code')!=identity:
                return ['off-native-source-identity-invalid']
            return policy.native_semantic_errors(record,contract.semantic_validator.context,
                source_record=source,source_ordinal=ordinal)
        except Exception:
            return ['off-native-source-row-invalid']
    try:
        db=sqlite3.connect(db_path.as_uri()+'?mode=ro&immutable=1',uri=True)
        # Enforce the supplied per-row bound inside SQLite before a forged TEXT
        # cell can be materialized in Python; allow fixed row framing overhead.
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,min(2**31-1,limits.max_line_bytes+1024))
        db.execute('PRAGMA query_only=ON')
        table=db.execute('SELECT type FROM sqlite_master WHERE name=?',('raw',)).fetchall()
        columns=[r[1] for r in db.execute('PRAGMA table_info(raw)')]
        if table!=[('table',)] or columns!=['tab','ordinal','identity','parent','body']:
            _fail('off-source-authority-db-schema')
        if _identity(db_path)!=db_identity:_fail('off-source-authority-changed')
        active=True
        yield replace(contract,semantic_validator=semantic)
    except sqlite3.Error:
        _fail('off-source-authority-db')
    finally:
        active=False
        if db is not None:db.close()
        try:
            _sidecars_absent(db_path)
            if (_snapshot(db_path,limits.max_database_bytes,expected_db)!=db_identity
                    or _snapshot(manifest_path,1024**2,manifest_pin)!=manifest_identity):
                _fail('off-source-authority-changed')
        except Exception:
            _fail('off-source-authority-changed')
