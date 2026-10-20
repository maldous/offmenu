"""OFF native schemas and pure source-row semantics, without real admission.

Reuses the accepted Python projector. No source IO, SourceContract constructor,
count/ID witness, runtime binding, resource selection or permission factory.
"""
from dataclasses import dataclass
from functools import lru_cache
import re

from .acceptance import Asset, canonical, fingerprint
from . import product_adapters as adapters

RELEASE = '2026-10-12'
SOURCE = Asset('off-2026-10-12.jsonl.gz',13132516914,
    '11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e')
LICENSE = 'ODbL / DbCL (retained data only)'
ATTRIBUTION = 'Open Food Facts'
VERSION = 'offmenu-off-native-policy/1'


def _object(properties):
    return {'type':'object','required':list(properties),'properties':properties,
            'additionalProperties':False}


def native_schemas():
    """Closed existing Python projector shapes; raw source values stay native.

    No fieldOrigins extension: it needs its own reviewed enrichment binding.
    SourceRow has no invented maximum; the actual witness must supply that bound.
    """
    text={'type':'string'}
    nullable_text={'type':['string','null']}
    code={'type':'string','pattern':'^[0-9]{4,32}$'}
    sha={'type':'string','pattern':'^[0-9a-f]{64}$'}
    scalar={'type':['string','number','boolean','null']}
    ids={'type':'array','minItems':1,'maxItems':1,'items':_object({
        'system':{'const':'barcode'},'value':code})}
    basis=_object({'amount':{'const':100},'unit':{'enum':['g','ml']},
        'state':{'const':'as-sold'},'qualificationStatus':{'const':'unverified-source-assertions'}})
    nutrients={}
    for field,(name,unit) in adapters._OFF_NUTRIENTS.items():
        nutrients[name]=_object({'value':{'type':['number','null']},
            'unit':{'const':unit},'basis':basis,
            'sourceAmount':{'type':['string','number','null']},
            'sourceField':{'const':field},'method':{'const':'source'}})
    data={
        'product':_object({'name':{'type':'string','minLength':1},'identifiers':ids,
            'brand':nullable_text,'ingredientsText':nullable_text,
            'sourceCountryTags':{'type':['array','null'],'items':text},
            'rawNutriments':{'type':'object','additionalProperties':{'$ref':'#/$defs/json'}},
            'nutritionSourceBasis':nullable_text,
            'qualificationStatus':{'const':'unverified-source-assertions'},
            'nutritionId':{'type':'string','pattern':'^off:nutrientProfile:[0-9]{4,32}$'}}),
        'nutrientProfile':_object({'foodName':{'type':'string','minLength':1},
            'identifiers':ids,'basis':basis,'nutrients':{
                'type':'object','properties':nutrients,'additionalProperties':False}}),
    }
    provenance=_object({'sourceId':{'const':'off'},'releaseId':{'const':RELEASE},
        'recordId':code,'fetchedAt':{'type':'null'},'sourceDate':{'type':'null'},
        'acquisitionClock':_object({'status':{'const':'unknown-retained'},'evidenceSha256':sha}),
        'license':{'const':LICENSE},'attribution':{'const':ATTRIBUTION},
        'rightsEvidenceSha256':sha,'scopeEvidenceSha256':sha,
        'transform':{'const':adapters.VERSION},'visibility':{'const':'private-candidate'},
        'rights':{'const':'Original source terms govern reuse; normalization does not relicense data.'},
        'sourceRow':{'type':'integer','minimum':1},
        # Preserved source claims, not inferred acquisition/freshness timestamps.
        'sourceRevision':scalar,'sourceLastModified':scalar,'sourceLastUpdated':scalar,
        'inputSha256':{'const':{'products':SOURCE.sha256}}})
    json_value={'anyOf':[scalar,{'type':'array','items':{'$ref':'#/$defs/json'}},
                            {'type':'object','additionalProperties':{'$ref':'#/$defs/json'}}]}
    return {kind:{'$schema':'https://json-schema.org/draft/2020-12/schema',
        '$defs':{'json':json_value},**_object({'schemaVersion':{'const':'1.0'},
        'kind':{'const':kind},'id':{'type':'string','pattern':'^off:'+kind+':[0-9]{4,32}$'},
        'countries':{'const':[]},'data':shape,'provenance':provenance})}
        for kind,shape in data.items()}


@lru_cache(maxsize=1)
def _validators():
    from jsonschema import Draft202012Validator
    schemas=native_schemas()
    for schema in schemas.values():Draft202012Validator.check_schema(schema)
    return {kind:Draft202012Validator(schema) for kind,schema in schemas.items()}


def _context_errors(context):
    if type(context) is not adapters.ProductContext:
        return ['off-native-context-required']
    try:
        context.validate()
        if (context.source_id!='off' or context.release_id!=RELEASE
                or context.license!=LICENSE or context.attribution!=ATTRIBUTION
                or context.acquired_at is not None or context.acquisition_clock_status!='unknown-retained'):
            return ['off-native-context-mismatch']
    except Exception:
        return ['off-native-context-invalid']
    return []


def native_semantic_errors(record, context, *, source_record=None, source_ordinal=None):
    """Check one record against its trusted SAME-input raw row and ordinal.

    Pure application API, not a JSON-loaded authority. Caller must obtain the row
    and ordinal from a separately verified normalization/witness binding. Passing
    arbitrary caller data proves only a comparison; it establishes no custody.
    Missing authority rejects BOTH product and profile, even valid-shaped rows.
    """
    errors=set(_context_errors(context))
    if source_record is None or source_ordinal is None:
        errors.add('off-native-source-authority-required')
    if errors:return sorted(errors)
    try:
        if (type(source_record) is not dict or type(source_ordinal) is not int
                or source_ordinal<1 or type(source_record.get('code')) is not str
                or not re.fullmatch('[0-9]{4,32}',source_record['code'])):
            return ['off-native-source-row-invalid']
        canonical(source_record)  # Finite, serializable source assertions only.
        canonical(record)
        if type(record) is not dict or record.get('kind') not in ('product','nutrientProfile'):
            return ['off-native-record-invalid']
        if not _validators()[record['kind']].is_valid(record):
            return ['off-native-schema-invalid']
        # The existing projector owns fallback/numeric/basis/native-field rules.
        # Reuse it, rather than inventing another OFF normalizer or JS projection.
        expected=next(row for row in adapters._off(context,source_record)
                      if row['kind']==record['kind'])
        p=expected['provenance']
        p.update(sourceRow=source_ordinal,sourceRevision=source_record.get('rev'),
                 sourceLastModified=source_record.get('last_modified_t'),
                 sourceLastUpdated=source_record.get('last_updated_t'),
                 inputSha256={'products':SOURCE.sha256})
        if canonical(record['data'])!=canonical(expected['data']):
            errors.add('off-native-source-projection-mismatch')
        if canonical(record['provenance'])!=canonical(p):
            errors.add('off-native-source-provenance-mismatch')
        if record['id']!=expected['id'] or record['countries']!=expected['countries']:
            errors.add('off-native-source-identity-mismatch')
    except ImportError:
        errors.add('off-native-schema-runtime-unavailable')
    except Exception:
        # Never echo source values or parser exception strings.
        errors.add('off-native-record-or-source-invalid')
    return sorted(errors)


@dataclass(frozen=True)
class UnboundOffSemantics:
    """Fail-closed callback until a reviewed verified source binding is selected."""
    context: adapters.ProductContext

    def __call__(self, record):
        return native_semantic_errors(record,self.context)


def policy_descriptor():
    """Review identity and open bindings; no SourceContract or resource defaults."""
    return {'version':VERSION,'sourceId':'off','releaseId':RELEASE,
        'source':vars(SOURCE),'schemasSha256':fingerprint(native_schemas()),
        'projection':{'module':'offmenu.refresh.product_adapters','symbol':'_off',
                      'version':adapters.VERSION},
        'sourceRecordMode':'exact raw product row and physical logical-row ordinal',
        'scope':'private native source assertions only, lexical barcode not verified GTIN',
        'realContractConstructed':False,'realDataQualified':False,
        'pendingBindings':[
            'actual-eligible-complete-OFF-terminal-witness-and-independent-review-pins',
            'expected-record-count-and-sorted-unique-ID-digest-from-that-witness',
            'actual-raw-row-extent-and-duplicate-invalid-quarantine-disposition',
            'reviewed-product-specific-rights-scope-clock-evidence-assets-and-purpose',
            'source-code-identity-to-SAME-verified-normalization-source-sqlite-row-ordinal-binding',
            'explicit-real-ProductLimits-and-SourceContract-limits-no-default-envelope',
            'runtime-destination-capacity-commitments-and-selected-once-only-operation',
        ]}
