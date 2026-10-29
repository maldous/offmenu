"""Retained OpenPrices cache prequalification; no IO, grants or acceptance.

The projection is the accepted JS offmenu-bulk/1 priceObservation shape, not
product_adapters' fresh-source shape. Callers own custody/resource/full-set checks.
This module deliberately constructs no SourceContract from a collection manifest.
"""
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import re

from .acceptance import Asset, canonical, fingerprint
from .core import strict_json

RELEASE = '2026-10-12'
MAX_MANIFEST = 1024*1024
MAX_LINE = 2*1024*1024
MAX_EXPANDED = 512*1024*1024
SHA = re.compile('[0-9a-f]{64}')
NOTICE = 'Original source terms govern reuse; normalization does not relicense the data.'


def _reject(code):
    raise ValueError(code)


def _sha(value):
    if type(value) is not str or SHA.fullmatch(value) is None:
        _reject('prices-pin-invalid')


def _count(value, maximum=1_000_000):
    if type(value) is not int or not 0 <= value <= maximum:
        _reject('prices-count-invalid')


@dataclass(frozen=True)
class Partition:
    key: str
    records: int
    bytes: int
    sha256: str


@dataclass(frozen=True)
class CacheSelection:
    manifest_sha256: str
    archive_sha256: str
    records: int
    raw_rows: int
    partitions: tuple

    def input_assets(self):
        """Declared compressed inputs only; no claim that bytes were checked."""
        return tuple(Asset(p.key,p.bytes,p.sha256) for p in self.partitions)


def select_manifest(raw, expected_sha256):
    """Verify a trusted external metadata pin; counts remain source declarations.

    No filesystem read, source rights decision or independent count/ID witness
    follows from this metadata check. Partition order is canonicalized, not data.
    """
    _sha(expected_sha256)
    if type(raw) is not bytes or len(raw)>MAX_MANIFEST:
        _reject('prices-manifest-bound')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        _reject('prices-manifest-pin-mismatch')
    try:
        obj=strict_json(raw.decode('utf-8'))
        if type(obj) is not dict or any(obj.get(k)!=v for k,v in {
            'schemaVersion':'offmenu-collection/1','sourceId':'prices',
            'releaseId':RELEASE,'status':'normalized','license':'ODbL',
            'attribution':'Open Prices','url':'https://prices.openfoodfacts.org',
            'publication':'local only; no production corpus storage enabled',
        }.items()):
            _reject('prices-manifest-identity')
        _sha(obj['archiveSha256'])
        counts=obj['counts']
        if type(counts) is not dict or set(counts)!={'raw','accepted','duplicates','quarantined','excluded','records'}:
            _reject('prices-manifest-counts')
        for value in counts.values():_count(value)
        if (not counts['records'] or counts['accepted']!=counts['records']
                or counts['duplicates'] or counts['quarantined']
                or counts['raw']!=sum(counts[k] for k in ('accepted','duplicates','quarantined','excluded'))
                or obj['kinds']!={'priceObservation':counts['records']}):
            _reject('prices-manifest-counts')
        parts=obj['partitions']
        if type(parts) is not list or len(parts)!=256:
            _reject('prices-partition-inventory')
        selected=[]
        for p in parts:
            if type(p) is not dict or set(p)!={'key','records','bytes','sha256'}:
                _reject('prices-partition-invalid')
            if type(p['key']) is not str or not re.fullmatch(r'[0-9a-f]{2}\.jsonl\.gz',p['key']):
                _reject('prices-partition-path')
            _count(p['records']);_count(p['bytes'],MAX_EXPANDED);_sha(p['sha256'])
            if not p['bytes'] or not p['records']:_reject('prices-partition-empty')
            selected.append(Partition(**p))
        if ({p.key for p in selected}!={f'{i:02x}.jsonl.gz' for i in range(256)}
                or sum(p.records for p in selected)!=counts['records']
                or sum(p.bytes for p in selected)>MAX_EXPANDED):
            _reject('prices-partition-inventory')
        return CacheSelection(expected_sha256,obj['archiveSha256'],counts['records'],
                              counts['raw'],tuple(sorted(selected,key=lambda p:p.key)))
    except ValueError:
        raise
    except (KeyError,TypeError,UnicodeError,RecursionError,OverflowError):
        _reject('prices-manifest-invalid')


def _object(properties):
    return {'type':'object','properties':properties,'required':list(properties),
            'additionalProperties':False}


def price_schema(selection):
    """Closed source-specific shape, preserving missing/unknown native values."""
    nullable_text={'type':['string','null'],'maxLength':65536}
    nullable_number={'type':['number','null']}
    identifier=_object({'system':{'const':'barcode'},'value':{'type':'string','minLength':1,'maxLength':300}})
    data=_object({
        'identifiers':{'type':'array','maxItems':1,'items':identifier},
        'amount':{'type':['number','null'],'minimum':0},
        'currency':nullable_text,'observedAt':nullable_text,
        'retailer':_object({'name':nullable_text,'externalId':{'type':'string','maxLength':300},'location':nullable_text}),
        'unitPrice':nullable_number,'unit':nullable_text,
        'promotion':{'type':['boolean','null']},'discountType':nullable_text,
        'regularAmount':nullable_number,'duplicateOf':{'type':'null'},
        'proofId':{'type':['string','integer','null'],'maxLength':300},
        'availability':{'const':'unknown'},'priceType':{'const':'dated-observation'},
    })
    provenance=_object({
        'sourceId':{'const':'prices'},'recordId':{'type':'string','minLength':1,'maxLength':276},
        'url':{'const':'https://prices.openfoodfacts.org/'},'license':{'const':'ODbL'},
        'attribution':{'const':'Open Prices'},'fetchedAt':{'type':'string','maxLength':64},
        'sourceDate':nullable_text,'visibility':{'const':'public'},
        'transform':{'const':'offmenu-bulk/1'},'rights':{'const':NOTICE},
        'releaseId':{'const':RELEASE},'archiveSha256':{'const':selection.archive_sha256},
        'sourceRow':{'type':'integer','minimum':1,'maximum':selection.raw_rows},
    })
    return {'$schema':'https://json-schema.org/draft/2020-12/schema',**_object({
        'schemaVersion':{'const':'1.0'},'kind':{'const':'priceObservation'},
        'id':{'type':'string','minLength':1,'maxLength':300},
        'countries':{'type':'array','maxItems':1,'items':{'type':'string','pattern':'^[A-Z]{2}$'}},
        'provenance':provenance,'data':data,
    })}


class PriceValidator:
    """Per-packet prequalification only, designed for an owner's existing stream.

    A successful row check is NOT a qualified source/family or relationship.
    This object neither reads cache files nor collects/exports identity assertions.
    """
    def __init__(self, selection):
        if type(selection) is not CacheSelection:
            _reject('prices-selection-required')
        self.selection=selection
        self.partitions={p.key:p for p in selection.partitions}
        from jsonschema import Draft202012Validator
        schema=price_schema(selection)
        Draft202012Validator.check_schema(schema)
        self.schema_sha256=fingerprint(schema)
        self.validator=Draft202012Validator(schema)

    def validate_line(self, raw, *, partition, line):
        """Fixed codes; exact UTF-8 LF singleton packets, no mutation or output."""
        if type(partition) is not str or partition not in self.partitions:
            return ('prices-partition-unknown',)
        if type(line) is not int or not 1<=line<=self.partitions[partition].records:
            return ('prices-partition-line-bound',)
        if type(raw) is not bytes or not raw.endswith(b'\n') or len(raw)>MAX_LINE:
            return ('prices-line-bound',)
        try:
            packet=strict_json(raw.decode('utf-8'))
            if type(packet) is not list or len(packet)!=1 or type(packet[0]) is not dict:
                return ('prices-packet-invalid',)
            row=packet[0]
            canonical(row)  # Reject nonfinite/overflow numbers throughout.
            if not self.validator.is_valid(row):
                return ('prices-record-schema',)
            p,d=row['provenance'],row['data']
            errors=set()
            if row['id']!='prices:priceObservation:'+p['recordId']:
                errors.add('prices-record-identity')
            if hashlib.sha256(p['recordId'].encode('utf-8')).hexdigest()[:2]+'.jsonl.gz'!=partition:
                errors.add('prices-record-shard')
            if p['sourceDate']!=d['observedAt']:
                errors.add('prices-source-date-mismatch')
            stamp=datetime.fromisoformat(p['fetchedAt'].replace('Z','+00:00'))
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                errors.add('prices-cache-clock-invalid')
            if d['observedAt'] is not None:
                if not re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',d['observedAt']):
                    errors.add('prices-observation-date-invalid')
                else:date.fromisoformat(d['observedAt'])
            return tuple(sorted(errors))
        except Exception:
            return ('prices-record-invalid',)


def qualification_gaps():
    """Accepted c670 API fit, not a request for blanket new source approval."""
    return {
        'sourceContractConstructed':False,'familyQualified':False,
        'relationshipInputReady':False,'executionAdmitted':False,
        'missingBindings':[
            'independent-current-cache-unique-id-digest-and-all-record-accounting',
            'reviewed-cache-processing-clock-distinct-from-unknown-original-acquisition',
            'reviewed-gzip-partition-custody-to-singleton-candidate-bridge',
            'exact-standing-private-use-evidence-bound-to-reviewed-contract',
        ],
        'acceptedApiLimits':[
            'SourceContract.unknown-retained-clock-allows-only-off-and-usda-files',
            'SourceContract.input_root-allows-only-private-native-off-and-usda-files',
            'qualify-requires-one-uncompressed-singleton-JSONL-candidate-and-full-manifest',
        ],
        'separateRelationshipDependencies':[
            'existing-source-to-reviewed-graph-IRI-role-context-resolver',
            'actual-source-supported-relationship-witnesses',
        ],
    }
