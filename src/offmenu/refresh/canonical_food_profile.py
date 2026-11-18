"""Optional public quantitative assertion profile. Never loads a provider or a private profile.

Compose this sidecar with common-data citations/assertions; do not rewrite the
existing source dataset. All units/derivations are exact until presentation.
The caller owns source-native field extraction, permission and trusted witness pins.
"""
from copy import deepcopy
from datetime import date
from fractions import Fraction
from hashlib import sha256
import ipaddress
import json
from re import fullmatch
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from .field_provenance import datum_pointers

PUBLIC = "offmenu-public-food-assertion-profile/1"
UNITS = {  # exact factors to g, mL, J or a count; no implicit mass-volume bridge
    "ug": ("mass", Fraction(1, 1000000)), "mg": ("mass", Fraction(1, 1000)),
    "g": ("mass", Fraction(1)), "kg": ("mass", Fraction(1000)),
    "[oz_av]": ("mass", Fraction("28.349523125")), "[lb_av]": ("mass", Fraction("453.59237")),
    "mL": ("volume", Fraction(1)), "L": ("volume", Fraction(1000)),
    "[foz_us]": ("volume", Fraction("29.5735295625")), "[foz_br]": ("volume", Fraction("28.4130625")),
    "kJ": ("energy", Fraction(1000)), "J": ("energy", Fraction(1)),
    "kcal_th": ("energy", Fraction(4184)), "1": ("count", Fraction(1)),
}
TEXT = {"type": "string", "minLength": 1, "maxLength": 512, "pattern": r"\S"}
ID = {"type":"string","maxLength":512,"pattern":r"^(urn:[A-Za-z0-9][A-Za-z0-9-]*:|https://)[^\s]+$"}
DIGEST = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
MAG = {"type": "string", "maxLength": 48, "pattern": "^(0|[1-9][0-9]*)([.][0-9]+)?$"}
UNIT = {"enum": sorted(UNITS)}
DATE = {"type": "string", "format": "date", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}


def obj(fields, optional=()):
    return {"type": "object", "properties": fields, "additionalProperties": False,
            "required": [k for k in fields if k not in optional]}


def seq(items, minimum=1, maximum=256):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


def ensure(ok, code):
    if not ok:
        raise ValueError(code)


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def validated(schema, value, code):
    ensure(Draft202012Validator(schema).is_valid(value), code)


def amount(text):
    ensure(type(text) is str and len(text) <= 48 and fullmatch(MAG["pattern"], text), "invalid-quantity")
    return Fraction(text)


def convert(value, source_unit, target_unit):
    ensure(source_unit in UNITS and target_unit in UNITS, "unknown-unit")
    a,b=UNITS[source_unit],UNITS[target_unit]
    ensure(a[0] == b[0], "incomparable-dimensions")
    return value*a[1]/b[1]


def exact(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


# Use separate axes: identical nutrient names or compatible units do not prove
# identical nutrient form, preparation, reference type, or measurement basis.
AXES = ("measureId","nutrientForm","jurisdiction","issuer","population","ageBand","sex",
        "lifeStage","edition","referenceType","period","basis","foodState","measurementMethod")
CONTEXT = obj({**{k:TEXT for k in AXES}, "measureId":ID, "effectiveFrom":DATE, "effectiveThrough":DATE})
ORIGIN = obj({"citationId":TEXT,"sourceId":TEXT,"releaseId":TEXT,"sourceRecordId":TEXT,
              "sourceField":TEXT,"upstreamOccurrenceId":TEXT,"upstreamUrl":TEXT,
              "assetSha256":DIGEST,"sourceFieldSha256":DIGEST,"license":TEXT,"attribution":TEXT})
MEASUREMENT = obj({"magnitude":MAG,"unit":UNIT,"originalLexeme":TEXT})
FIELD_BINDING = {"oneOf":[
    obj({"kind":{"const":"source"},"citationIds":seq(TEXT,1,32)}),
    obj({"kind":{"const":"derived"},"citationIds":seq(TEXT,1,32),"methodId":ID,"policySha256":DIGEST})
]}
FIELD_MAP = {"type":"object","maxProperties":128,"additionalProperties":FIELD_BINDING}
PUBLIC_SCHEMA = {"$schema":"https://json-schema.org/draft/2020-12/schema",
    "$id":"urn:offmenu:canonical-public-food-assertion-profile:1",
    "description":"Numeric sidecar to a cited public common-data assertion, not source authority or a mirror.",
    **obj({"profileVersion":{"const":PUBLIC},"assertionId":ID,"subjectId":ID,
           "propertyId":ID,"fieldPointer":{"type":"string","minLength":2,"maxLength":512,
                                          "pattern":"^/([^~]|~[01])+$"},
           "context":CONTEXT,"measurement":MEASUREMENT,"origins":seq(ORIGIN,1,32),"fieldOrigins":FIELD_MAP})}


def origin_key(origin):
    return tuple(origin[k] for k in ("sourceId","releaseId","sourceRecordId","sourceField"))


def source_witness(assertion, origin):
    """For a separately verified source adapter, not a way for a payload to authorize itself."""
    return fingerprint({k:assertion[k] for k in ("assertionId","subjectId","propertyId","fieldPointer",
                       "context","measurement","fieldOrigins")} | {"origin":origin})


def validate_assertion(assertion, *, registry, purpose="reference", trusted_transform_pins=()):
    """registry: trusted {origin_key: {witnesses, upstreamUrl, allowedPurposes}}; never use the input as registry."""
    validated(PUBLIC_SCHEMA,assertion,"invalid-public-assertion")
    ensure(purpose=="reference" or purpose.startswith("aggregate:"),"unbound-purpose")
    # Reuse common per-scalar pointer convention, but permit a separately
    # reviewed join across several releases rather than smuggling it through
    # the single-source staging validator.
    fields={k:assertion[k] for k in ("subjectId","propertyId","fieldPointer","context","measurement")}
    origins=assertion["fieldOrigins"]
    ensure(set(origins)==set(datum_pointers(fields,prefix="")),"incomplete-field-origin-map")
    citations=[o["citationId"] for o in assertion["origins"]]
    ensure(len(set(citations))==len(citations),"duplicate-citation")
    used=set()
    for item in origins.values():
        ids=set(item["citationIds"])
        ensure(len(ids)==len(item["citationIds"]) and ids<=set(citations),"unbound-field-citation")
        if item["kind"]=="derived":
            ensure(item["policySha256"] in trusted_transform_pins,"unverified-field-transformation")
        used.update(ids)
    ensure(used==set(citations),"unused-source-citation")
    c=assertion["context"]
    ensure(date.fromisoformat(c["effectiveFrom"])<=date.fromisoformat(c["effectiveThrough"]),"invalid-date-span")
    seen=set()
    for o in assertion["origins"]:
        ensure(matches_digest(o["sourceFieldSha256"]) and matches_digest(o["assetSha256"]),"invalid-origin-digest")
        key=origin_key(o)
        ensure(key not in seen,"duplicate-origin")
        seen.add(key)
        grant=registry.get(key)
        ensure(isinstance(grant,dict) and isinstance(grant.get("allowedPurposes"),(set,frozenset))
               and purpose in grant["allowedPurposes"] and isinstance(grant.get("witnesses"),(set,frozenset))
               and source_witness(assertion,o) in grant["witnesses"],"source-evidence-or-permission-missing")
        u=urlsplit(o["upstreamUrl"])
        ensure(u.scheme=="https" and u.hostname and u.hostname!= "localhost" and "." in u.hostname
               and not u.username and not u.password and not u.fragment and grant.get("upstreamUrl")==o["upstreamUrl"]
               and isinstance(grant.get("originHosts"),(set,frozenset)) and u.hostname in grant["originHosts"],
               "not-qualified-external-original")
        # No credentials, temporary download tokens, provider API keys or private endpoints.
        ensure(not u.query and not u.hostname.endswith((".local",".localhost",".internal")),"not-qualified-external-original")
        try:
            ipaddress.ip_address(u.hostname)
        except ValueError:
            pass
        else:
            raise ValueError("not-qualified-external-original")
    return assertion


def aggregate(assertions, *, registry, method, target_unit, method_pin, trusted_transform_pins=()):
    """Unweighted mean or median of commensurate, independently sourced numeric observations only."""
    ensure(method in ("unweighted-mean","median") and matches_digest(method_pin),"unqualified-method")
    ensure(isinstance(assertions,(tuple,list)) and 2<=len(assertions)<=256,"aggregate-cardinality")
    used,ids,values,lineage=set(),set(),[],[]
    comparison=None
    for a in assertions:
        validate_assertion(a,registry=registry,purpose="aggregate:"+method+":"+method_pin,
                           trusted_transform_pins=trusted_transform_pins)
        axes=(a["subjectId"],a["propertyId"],a["fieldPointer"],tuple(sorted(a["context"].items())))
        ensure(all(v.strip().casefold() not in ("unknown","unresolved","unspecified","") for v in a["context"].values()),
               "unknown-comparability-axis")
        ensure(comparison is None or comparison==axes,"incompatible-scope-basis-or-edition")
        comparison=axes
        quantitatives=set(a["fieldOrigins"]["/measurement/magnitude"]["citationIds"])
        observations=[o for o in a["origins"] if o["citationId"] in quantitatives]
        # Re-labelling a coordinate or re-packaging the identical source bytes
        # does not create an independent observation. Shared non-numeric method
        # citations are retained but do not count as new measurements.
        occurrences=set()
        for o in observations:
            occurrences.update({("occurrence",o["upstreamOccurrenceId"]),
                ("coordinate",*origin_key(o)),
                ("asset",o["assetSha256"],o["sourceRecordId"],o["sourceField"]),
                ("original",o["upstreamUrl"],o["sourceRecordId"],o["sourceField"])})
        ensure(not used.intersection(occurrences) and a["assertionId"] not in ids,"overlapping-observations")
        used.update(occurrences);ids.add(a["assertionId"])
        m=a["measurement"];numeric=convert(amount(m["magnitude"]),m["unit"],target_unit)
        values.append(numeric)
        lineage.append({"assertionId":a["assertionId"],"assertionSha256":fingerprint(a),
                        "citationIds":sorted(x["citationId"] for x in a["origins"]),
                        "fieldOrigins":[{"sourceId":x["sourceId"],"releaseId":x["releaseId"],
                                         "sourceRecordId":x["sourceRecordId"],"sourceField":x["sourceField"],
                                         "sourceFieldSha256":x["sourceFieldSha256"]} for x in a["origins"]],
                        "fieldMap":deepcopy(a["fieldOrigins"]),
                        "sourceUnit":m["unit"],"targetUnit":target_unit,
                        "factor":exact(convert(Fraction(1),m["unit"],target_unit))})
    values.sort();n=len(values)
    result=sum(values,Fraction())/n if method=="unweighted-mean" else (values[(n-1)//2]+values[n//2])/2
    return {"subjectId":comparison[0],"propertyId":comparison[1],"fieldPointer":comparison[2],
            "context":dict(comparison[3]),"targetUnit":target_unit,"value":exact(result),"n":n,
            "method":method,"methodSha256":method_pin,"inputs":sorted(lineage,key=lambda x:x["assertionId"]),
            "reviewStatus":"candidate","publish":False}


def matches_digest(x):
    return type(x) is str and fullmatch(r"[0-9a-f]{64}",x) is not None
