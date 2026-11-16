import hashlib,json,math,re
from urllib.parse import quote
SCHEMA_VERSION="offmenu-common/1"
PUBLIC_SCOPE={"visibility":"public","reuseScope":"source-licensed"}
TYPE_SITE="urn:offmenu:type:Site"
TYPE_ORGANIZATION="urn:offmenu:type:Organization"
PROPERTY_SOURCE="urn:offmenu:property:source-field:"
PROPERTY_ORIGINAL_RECORD="urn:offmenu:property:originalSourceRecord"
def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def stable_id(kind, *parts):
    """A short valid IRI, stable even where source strings contain Unicode."""
    digest = sha256_bytes("\x1f".join(str(p) for p in parts).encode("utf-8"))
    return f"urn:offmenu:places:{kind}:{digest}"


def source_property(path):
    return PROPERTY_SOURCE + quote(path, safe="-._~")


def text_value(value, assertion_id):
    encoded = value.encode("utf-8")
    return {
        "kind": "text",
        "id": assertion_id + ":text",
        "language": "und",
        "value": value,
        "sourceTextSha256": sha256_bytes(encoded),
        "status": "source-asserted",
        "citationIds": [],
    }


# This is intentionally a small, explicit vocabulary.  It covers machine controls
# present in the public normalized projection.  Human descriptions such as
# countryBasis, attribution, copyright, licence strings and provider names do not
# belong here: they remain cited, language-undetermined source text.
FIXED_IDENTIFIER_KEYS = {
    "schemaVersion", "kind", "sourceId", "recordId", "releaseId", "transform",
    "system", "sourceVersion", "country", "countries", "sourceCountryTags",
    "countryMappingStatus", "status", "policyVersion", "schema",
    "sourceRecordReference", "archiveSha256", "contentSha256", "visibility",
    "geometryType", "geometryTypes", "unit", "units", "language", "languages",
    "languageCode", "languageCodes", "locale", "locales", "region",
    "role", "roles", "taxonomy", "primary", "hierarchy", "alternates",
    "basicCategory", "sourceReportedOperatingStatus", "inventoryAvailability",
    "dietQualification", "reviewStatus",
}
URI_KEYS = {"url", "licenseUrl", "website", "websites", "licenseNotices", "sourceUrl", "sourceUrls", "uri", "uris", "iri", "iris"}
DATE_TIME_KEYS = {"sourceDate", "fetchedAt", "retrievedAt", "createdAt", "updatedAt", "publishedAt"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def typed_value(value, assertion_id, field_name="", identifier_context=False):
    """Represent every JSON source value without coercing its semantics."""
    if value is None:
        return {"kind": "null", "value": None}
    if isinstance(value, bool):
        return {"kind": "boolean", "value": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"kind": "number", "value": value}
    if isinstance(value, float):
        if not math.isfinite(value):
            # JSON sources should not contain these, but preserve the lexical fact
            # rather than emit an invalid common-data number.
            return text_value(str(value), assertion_id)
        return {"kind": "number", "value": value}
    if isinstance(value, str):
        # These lexical forms are identities regardless of the enclosing field
        # name.  This prevents a valid URL, IRI or ISO timestamp in a provider
        # extension from becoming localizable display text.
        if value.startswith(("http://", "https://", "urn:")):
            return {"kind": "uri", "value": value}
        if DATE_RE.fullmatch(value):
            return {"kind": "date", "value": value}
        if DATETIME_RE.fullmatch(value):
            return {"kind": "datetime", "value": value}
        if identifier_context or field_name in FIXED_IDENTIFIER_KEYS:
            return {"kind": "identifier", "value": value}
        return text_value(value, assertion_id)
    if isinstance(value, list):
        return {
            "kind": "list",
            "items": [typed_value(item, f"{assertion_id}:item:{index}", field_name, identifier_context) for index, item in enumerate(value)],
        }
    if isinstance(value, dict):
        # Only explicit identifier objects give their ``value`` a machine-code
        # interpretation.  Do not infer that interpretation from a generic
        # ancestor or from a field merely named ``value``.
        child_identifier_context = identifier_context or field_name in {"identifier", "identifiers"}
        return {
            "kind": "structure",
            "fields": {
                str(key): typed_value(item, f"{assertion_id}:field:{quote(str(key), safe='-._~')}", str(key), child_identifier_context)
                for key, item in sorted(value.items(), key=lambda item: str(item[0]))
            },
        }
    return text_value(str(value), assertion_id)


def assertion(resource_id, citation_id, source_id, record_id, path, value, property_id=None):
    property_id = property_id or source_property(path)
    assertion_id = stable_id("assertion", source_id, record_id, path, property_id)
    leaf = path.rsplit(".", 1)[-1].lstrip("$")
    typed = typed_value(value, assertion_id, leaf, identifier_context=(path == "$.id"))
    # Text fields refer to their own source citation as required by the schema.
    def attach_citation(node):
        if isinstance(node, dict):
            if node.get("kind") == "text":
                node["citationIds"] = [citation_id]
            for child in node.values():
                attach_citation(child)
        elif isinstance(node, list):
            for child in node:
                attach_citation(child)
    attach_citation(typed)
    return {
        "id": assertion_id,
        "subjectId": resource_id,
        "propertyId": property_id,
        "value": typed,
        "status": "source-asserted",
        "citationIds": [citation_id],
        "sourcePath": path,
        "scope": PUBLIC_SCOPE,
    }


def citation_for(row):
    provenance = row["provenance"]
    source_id = provenance["sourceId"]
    record_id = provenance["recordId"]
    citation_id = stable_id("citation", source_id, record_id)
    return citation_id, {
        "id": citation_id,
        "sourceId": source_id,
        "originalRecordId": record_id,
        "originalUrl": provenance["url"],
        "revisionId": provenance.get("releaseId"),
        "sourceDate": provenance.get("sourceDate"),
        "contentSha256": provenance.get("archiveSha256"),
        "license": provenance["license"],
        "attribution": provenance["attribution"],
        "rightsEvidenceUrl": provenance.get("licenseUrl") or provenance["url"],
        "sourcePath": "$",
        "scope": PUBLIC_SCOPE,
    }


def resource_for(row, citation_id):
    provenance = row["provenance"]
    source_id = provenance["sourceId"]
    record_id = provenance["recordId"]
    # Overture has place/location records.  A category such as grocery store is
    # evidence about the site only, not evidence for a separately identified actor.
    common_type = TYPE_SITE if source_id == "overture-food-places" else TYPE_ORGANIZATION
    resource_id = f"urn:offmenu:source:{quote(source_id, safe='-._~')}:{'site' if common_type == TYPE_SITE else 'organization'}:{quote(record_id, safe='-._~')}"
    name = row.get("data", {}).get("name")
    names = []
    if isinstance(name, str):
        text_id = stable_id("resource-name", source_id, record_id)
        names.append({
            "kind": "text", "id": text_id, "language": "und", "value": name,
            "sourceTextSha256": sha256_bytes(name.encode("utf-8")),
            "status": "source-asserted", "citationIds": [citation_id],
        })
    return resource_id, {
        "id": resource_id,
        "type": common_type,
        "identityStatus": "source-scoped",
        "names": names,
        "citationIds": [citation_id],
        "scope": PUBLIC_SCOPE,
    }


def packet_record(row):
    citation_id, citation = citation_for(row)
    resource_id, resource = resource_for(row, citation_id)
    provenance = row["provenance"]
    source_id, record_id = provenance["sourceId"], provenance["recordId"]
    # Keep one complete typed source-record structure rather than expanding every
    # nested taxonomy/location/provider value into redundant facts.  The fields
    # remain individually typed and addressable within this cited structure.
    source_record = {
        "schemaVersion": row["schemaVersion"],
        "kind": row["kind"],
        "countries": row.get("countries", []),
        "provenance": provenance,
        "curation": row.get("curation", {}),
        "data": row.get("data", {}),
    }
    assertions = [
        assertion(resource_id, citation_id, source_id, record_id, "$.id", row["id"], PROPERTY_ORIGINAL_RECORD),
        assertion(resource_id, citation_id, source_id, record_id, "$.sourceRecord", source_record),
    ]
    return resource, assertions, citation


