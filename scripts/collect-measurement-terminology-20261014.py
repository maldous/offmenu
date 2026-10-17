#!/usr/bin/env python3
"""Acquire a bounded, cited QUDT unit terminology graph for OffMenu."""
import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jsonschema_rs

RELEASE = "v3.5.2"
REPOSITORY = "https://github.com/qudt/qudt-public-repo"
RAW_BASE = f"https://raw.githubusercontent.com/qudt/qudt-public-repo/{RELEASE}/"
FILES = {
    "units": "src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl",
    "quantityKinds": "src/main/rdf/vocab/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl",
    "license": "LICENSE.md",
}
CORE_IDS = {
    "GM", "KiloGM", "MilliGM", "MicroGM", "LB", "OZ", "L", "MilliL",
    "SEC", "MIN", "HR", "DAY", "M", "CentiM", "IN", "FT", "DEG_C", "K",
    "J", "KiloJ",
    "CAL_15DEG_C", "CAL_15_DEG_C", "CAL_20DEG_C", "CAL_IT", "CAL_MEAN", "CAL_TH",
    "KiloCAL", "KiloCAL_IT", "KiloCAL_Mean", "KiloCAL_TH",
    "COUNT", "NUM", "ONE", "PERCENT",
}
# Explicitly selected source IDs.  Derived rates such as gallon-per-hour are
# deliberately outside this food-measurement handoff.
HOUSEHOLD_IDS = {
    "CUP", "CUP_US", "TBSP", "TSP", "OZ_VOL_UK", "OZ_VOL_US",
    "GAL_IMP", "GAL_UK", "GAL_US", "GAL_US_DRY",
    "PINT", "PINT_UK", "PINT_US", "PINT_US_DRY",
    "QT_UK", "QT_US", "QT_US_DRY",
    "BU_UK", "BU_US", "BU_US_DRY", "PK_UK", "PK_US_DRY",
}
PUBLIC = {
    "visibility": "public",
    "reuseScope": "QUDT v3.5.2 CC BY 4.0; attribution to QUDT.org required",
}


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def iri_for_unit(token):
    return f"http://qudt.org/vocab/unit/{token}"


def stable(kind, value):
    return f"urn:offmenu:{kind}:qudt:{hashlib.sha256(value.encode()).hexdigest()[:24]}"


def fetch(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "OffMenu-data-acquisition/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    destination.write_bytes(data)
    return {"url": url, "bytes": len(data), "sha256": digest_bytes(data)}


def ttl_blocks(text):
    """Return named unit Turtle subjects without attempting ontology reasoning."""
    pattern = re.compile(r"(?ms)^unit:([A-Za-z0-9_-]+)\s+(.*?)(?=^unit:[A-Za-z0-9_-]+\s|\Z)")
    return [(match.group(1), match.group(2)) for match in pattern.finditer(text)]


def strings(block, predicate):
    pattern = re.compile(
        rf'{re.escape(predicate)}\s+"((?:[^"\\]|\\.)*)"(?:@([A-Za-z0-9-]+))?(?:\^\^[^\s;]+)?\s*[;.]',
        re.MULTILINE,
    )
    return [(value, language or "und") for value, language in pattern.findall(block)]


def objects(block, predicate, prefix):
    return re.findall(
        rf"{re.escape(predicate)}\s+{re.escape(prefix)}:([A-Za-z0-9_-]+)\s*[;.]",
        block,
    )


def number(block, predicate):
    match = re.search(
        rf"{re.escape(predicate)}\s+([-+]?(?:\d+\.?(?:\d*)?|\.\d+)(?:[Ee][-+]?\d+)?)\s*[;.]",
        block,
    )
    return float(match.group(1)) if match else None


def one_string(block, predicate):
    values = strings(block, predicate)
    return values[0][0] if values else None


def selected(token, block):
    return token in CORE_IDS or token in HOUSEHOLD_IDS


def text_value(identifier, value, language, citation_id):
    return {
        "kind": "text", "id": identifier, "language": language, "value": value,
        "sourceTextSha256": digest_text(value), "status": "source-asserted",
        "citationIds": [citation_id],
    }


def packet_for_unit(token, block, citation_id):
    unit_id = iri_for_unit(token)
    labels = strings(block, "rdfs:label")
    names = [
        text_value(stable("text", f"{unit_id}:label:{index}:{label}"), label, language, citation_id)
        for index, (label, language) in enumerate(labels)
    ]
    assertions = []

    def fact(property_id, value, path):
        assertions.append({
            "id": stable("assertion", f"{unit_id}:{property_id}:{path}:{json.dumps(value, sort_keys=True, ensure_ascii=False)}"),
            "subjectId": unit_id, "propertyId": property_id, "value": value,
            "status": "source-asserted", "citationIds": [citation_id],
            "sourcePath": path, "scope": PUBLIC,
        })

    multiplier = number(block, "qudt:conversionMultiplier")
    if multiplier is not None:
        fact("urn:offmenu:property:qudtConversionMultiplier", {"kind": "number", "value": multiplier}, "qudt:conversionMultiplier")
    offset = number(block, "qudt:conversionOffset")
    if offset is not None:
        fact("urn:offmenu:property:qudtConversionOffset", {"kind": "number", "value": offset}, "qudt:conversionOffset")
    for property_name, property_id in [
        ("qudt:symbol", "urn:offmenu:property:unitSymbol"),
        ("qudt:ucumCode", "urn:offmenu:property:ucumCode"),
        ("qudt:uneceCommonCode", "urn:offmenu:property:uneceCommonCode"),
    ]:
        value = one_string(block, property_name)
        if value:
            fact(property_id, text_value(stable("text", f"{unit_id}:{property_name}:{value}"), value, "und", citation_id), property_name)
    for quantity_kind in (
        objects(block, "qudt:hasQuantityKind", "quantitykind")
        + objects(block, "qudt:unitForQuantityKind", "quantitykind")
    ):
        fact("urn:offmenu:property:qudtQuantityKind", {"kind": "uri", "value": f"http://qudt.org/vocab/quantitykind/{quantity_kind}"}, "qudt:hasQuantityKind|unitForQuantityKind")
    for vector in objects(block, "qudt:hasDimensionVector", "qkdv"):
        fact("urn:offmenu:property:qudtDimensionVector", {"kind": "uri", "value": f"http://qudt.org/vocab/dimensionvector/{vector}"}, "qudt:hasDimensionVector")
    resource = {
        "id": unit_id, "type": "urn:offmenu:type:UnitDefinition",
        "identityStatus": "identified", "names": names, "citationIds": [citation_id],
        "scope": PUBLIC,
    }
    return {
        "schemaVersion": "offmenu-common/1", "resources": [resource],
        "assertions": assertions, "relations": [], "citations": [], "translations": [],
    }


def validate_packets(graph, schema):
    validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
    seen = {"resource": set(), "assertion": set()}
    counts = Counter()
    with gzip.open(graph, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            packet = json.loads(line)
            validator.validate(packet)
            for resource in packet["resources"]:
                if resource["id"] in seen["resource"]:
                    raise ValueError(f"duplicate resource ID at line {line_number}: {resource['id']}")
                seen["resource"].add(resource["id"]); counts["resources"] += 1
            for assertion in packet["assertions"]:
                if assertion["id"] in seen["assertion"]:
                    raise ValueError(f"duplicate assertion ID at line {line_number}: {assertion['id']}")
                seen["assertion"].add(assertion["id"]); counts["assertions"] += 1
            counts["packets"] += 1
    return counts


def admission_check(output, expected_counts):
    """Check the written release manifest and every public delivery file."""
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = ["complete", "limit", "releaseId", "expectedCounts", "observedCounts",
                "counts", "expectedSourceRecords", "observedSourceRecords",
                "sourceCounts", "partitionCoverage", "files"]
    missing = [key for key in required if key not in manifest]
    if missing:
        raise ValueError(f"manifest missing admission fields: {missing}")
    if manifest["complete"] is not True or manifest["limit"] is not None:
        raise ValueError("measurement release is not complete and unbounded")
    if manifest["expectedCounts"] != expected_counts or manifest["observedCounts"] != expected_counts:
        raise ValueError("manifest count expectations do not equal observed graph counts")
    if manifest["expectedSourceRecords"] != expected_counts["resources"] or manifest["observedSourceRecords"] != expected_counts["resources"]:
        raise ValueError("source-record definition count is inconsistent")
    if manifest["sourceCounts"] != {"qudt-measurement-definitions": expected_counts["resources"]}:
        raise ValueError("source count is inconsistent")
    coverage = manifest["partitionCoverage"]
    expected_coverage = {
        "complete": True, "expectedFiles": 1, "observedFiles": 1,
        "expectedPackets": expected_counts["packets"], "observedPackets": expected_counts["packets"],
    }
    if coverage != expected_coverage:
        raise ValueError("partition coverage is not the complete canonical one-file coverage")
    for entry in manifest["files"]:
        file_path = output / entry["key"]
        if not file_path.is_file() or file_path.stat().st_size != entry["bytes"]:
            raise ValueError(f"manifest file missing or wrong size: {entry['key']}")
        if digest_bytes(file_path.read_bytes()) != entry["sha256"]:
            raise ValueError(f"manifest file hash mismatch: {entry['key']}")
    return {"passed": True, "checkedFiles": len(manifest["files"]), "checkedCounts": expected_counts}


def collect(output, schema_path, refresh=False):
    if output.exists():
        if not refresh:
            raise ValueError(f"immutable output already exists: {output}")
        shutil.rmtree(output)
    raw = output / "raw"
    raw.mkdir(parents=True)
    fetched = {key: fetch(RAW_BASE + path, raw / Path(path).name) for key, path in FILES.items()}
    units = (raw / Path(FILES["units"]).name).read_text(encoding="utf-8")
    citation_id = "urn:offmenu:citation:qudt-v3.5.2-unit-vocabulary"
    citation = {
        "id": citation_id, "sourceId": "qudt", "originalRecordId": "QUDT unit vocabulary v3.5.2",
        "originalUrl": fetched["units"]["url"], "revisionId": RELEASE,
        "contentSha256": fetched["units"]["sha256"], "license": "CC-BY-4.0",
        "attribution": "QUDT.org", "rightsEvidenceUrl": fetched["license"]["url"],
        "sourcePath": FILES["units"], "scope": PUBLIC,
        "historyUrl": f"{REPOSITORY}/releases/tag/{RELEASE}",
    }
    graph = output / "measurement-units.jsonl.gz"
    selected_units = []
    with gzip.GzipFile(graph, "wb", mtime=0) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8") as target:
            for token, block in ttl_blocks(units):
                if not selected(token, block):
                    continue
                packet = packet_for_unit(token, block, citation_id)
                packet["citations"] = [citation]
                target.write(json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n")
                selected_units.append(token)
    counts = validate_packets(graph, json.loads(schema_path.read_text(encoding="utf-8")))
    expected_counts = {
        "packets": counts["packets"], "resources": counts["resources"],
        "assertions": counts["assertions"], "relations": 0, "translations": 0,
    }
    notice = output / "LICENSE-NOTICE.txt"
    notice.write_text(
        "QUDT measurement definitions are licensed under CC BY 4.0.\n"
        "Attribution: QUDT.org\n"
        "License: https://creativecommons.org/licenses/by/4.0/\n"
        f"Pinned source release: {RELEASE}; source license digest: {fetched['license']['sha256']}\n",
        encoding="utf-8",
    )
    files = [
        {"key": graph.name, "bytes": graph.stat().st_size, "sha256": digest_bytes(graph.read_bytes()), "packets": counts["packets"]},
        {"key": notice.name, "bytes": notice.stat().st_size, "sha256": digest_bytes(notice.read_bytes())},
    ]
    manifest = {
        "schemaVersion": "offmenu-measurement-terminology/1", "status": "accepted-schema-validated",
        "releaseId": "qudt-measurement-definitions-3.5.2-20261014",
        "complete": True, "limit": None,
        "source": {"id": "qudt-measurement-definitions", "version": "3.5.2",
                   "repository": REPOSITORY, "release": RELEASE, "publishedAt": "2026-09-22T13:13:30Z", "licence": "CC-BY-4.0",
                   "attribution": "QUDT.org", "rightsEvidence": fetched["license"]["url"]},
        "scope": "Pinned QUDT unit/quantity-kind terminology projected as identified registered UnitDefinition resources. Exact QUDT unit conversions are retained only within their declared dimensional model. No food density, yield, portion, ingredient equivalence, regional recipe-cup default, or historical-measure conversion is asserted.",
        "rawFilesLocalOnly": fetched, "selectedUnitTokens": selected_units,
        "expectedSourceRecords": counts["resources"], "observedSourceRecords": counts["resources"],
        "sourceCounts": {"qudt-measurement-definitions": counts["resources"]},
        "expectedCounts": expected_counts, "observedCounts": expected_counts, "counts": expected_counts,
        "partitionCoverage": {
            "complete": True,
            "expectedFiles": 1,
            "observedFiles": 1,
            "expectedPackets": counts["packets"],
            "observedPackets": counts["packets"],
        },
        "files": files,
        "validation": {"schema": str(schema_path), "validator": "jsonschema-rs Draft 2020-12 with IRI format validation",
                       "checks": ["every packet schema-valid", "unique resource IDs", "unique assertion IDs", "public scope", "citation attached to every projected source assertion"]},
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["admissionCheck"] = admission_check(output, expected_counts)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("corpus/common-data.schema.json"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    result = collect(args.output, args.schema, args.refresh)
    print(json.dumps({"status": result["status"], "counts": result["counts"], "units": len(result["selectedUnitTokens"]), "files": result["files"], "admissionCheck": result["admissionCheck"]}, indent=2))
