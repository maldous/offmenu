#!/usr/bin/env python3
"""Stream the normalized Overture and Wikidata place references into common-data packets.

The source datasets intentionally describe different things: Overture rows describe
physical places, while the Wikidata query describes organizations.  This alignment
does not turn a place category into an ownership, producer, retailer, availability,
or inventory claim.  It retains every normalized source field as a typed assertion
and uses a citation for the complete per-record acquisition/provenance envelope.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
import time
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from places_checkpoint import Checkpoint, atomic_bytes, digest, writer_lock, sink_state, restore_sink

import jsonschema_rs


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "offmenu-common/1"
PUBLIC_SCOPE = {"visibility": "public", "reuseScope": "source-licensed"}
TYPE_SITE = "urn:offmenu:type:Site"
TYPE_ORGANIZATION = "urn:offmenu:type:Organization"
PROPERTY_SOURCE = "urn:offmenu:property:source-field:"
PROPERTY_ORIGINAL_RECORD = "urn:offmenu:property:originalSourceRecord"


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


class PacketSink:
    def __init__(self, root, validator, packets_per_file, max_asset_bytes):
        self.root = root
        self.validator = validator
        self.packets_per_file = packets_per_file
        self.max_asset_bytes = max_asset_bytes
        self.file_index = 0
        self.current = []
        self.files = []
        self.counts = Counter()
        self.buffer = b""
        self.file_packets = 0

    def add(self, row):
        resource, assertions, citation = packet_record(row)
        self.current.append((resource, assertions, citation))

    def flush_packet(self):
        if not self.current:
            return
        packet = {
            "schemaVersion": SCHEMA_VERSION,
            "resources": [entry[0] for entry in self.current],
            "assertions": [item for entry in self.current for item in entry[1]],
            "relations": [],
            "citations": [entry[2] for entry in self.current],
            "translations": [],
        }
        self.validator.validate(packet)
        self.counts["packets"] += 1
        self.counts["resources"] += len(packet["resources"])
        self.counts["assertions"] += len(packet["assertions"])
        self.counts["citations"] += len(packet["citations"])
        self._append_packet(packet)
        self.current.clear()

    def _append_packet(self, packet):
        encoded = gzip.compress(
            (json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
            compresslevel=1,
            mtime=0,
        )
        if len(encoded) > self.max_asset_bytes:
            raise ValueError(
                f"single packet exceeds {self.max_asset_bytes} byte limit before writing ({len(encoded)})"
            )
        if self.file_packets >= self.packets_per_file or len(self.buffer) + len(encoded) > self.max_asset_bytes:
            self._close_file()
        self.buffer += encoded
        self.file_packets += 1

    def _close_file(self):
        if not self.buffer:
            return
        path = self.root / f"part-{self.file_index:05d}.jsonl.gz"
        if path.exists():
            if path.read_bytes() != self.buffer:
                raise ValueError(f"uncheckpointed output mismatch: {path}")
        else:
            atomic_bytes(path, self.buffer)
        self.files.append({"key": str(path.relative_to(self.root.parent)),
                           "bytes": len(self.buffer), "sha256": sha256_bytes(self.buffer),
                           "packets": self.file_packets})
        self.file_index += 1
        self.buffer = b""
        self.file_packets = 0

    def close(self):
        self._close_file()


def curated_rows(root, source_id, expected_assets=None, cursor=None, with_cursor=False):
    record_dir = root / "records" / source_id
    for path in sorted(record_dir.glob("*.jsonl.gz")):
        relative_key = str(path.relative_to(root))
        if cursor and relative_key < cursor["file"]:
            continue
        if expected_assets is not None:
            expected = expected_assets.get(relative_key)
            if expected is None:
                raise ValueError(f"{relative_key}: missing input asset manifest entry")
            raw = path.read_bytes()
            if len(raw) != expected["bytes"] or sha256_bytes(raw) != expected["sha256"]:
                raise ValueError(f"{relative_key}: input bytes or SHA-256 does not match accepted curated manifest")
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if cursor and relative_key == cursor["file"] and line_number <= cursor["line"]:
                    continue
                if not line.strip():
                    continue
                entry = json.loads(line)
                if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[1], list) or len(entry[1]) != 1:
                    raise ValueError(f"{path}:{line_number}: expected curated [public-id,[record]]")
                row = entry[1][0]
                yield (row, {"source": source_id, "file": relative_key, "line": line_number}) if with_cursor else row


def validate_row(row):
    if row.get("schemaVersion") != "1.0" or row.get("kind") not in {"site", "retailer", "organization"}:
        raise ValueError("unexpected normalized row type")
    provenance = row.get("provenance") or {}
    for key in ("sourceId", "recordId", "url", "license", "attribution", "visibility"):
        if not isinstance(provenance.get(key), str) or not provenance[key]:
            raise ValueError(f"missing provenance {key}")
    if provenance["visibility"] != "public":
        raise ValueError("non-public source row cannot enter public places package")
    if not isinstance(row.get("data"), dict):
        raise ValueError("missing data object")


def align(curated, output, records_per_packet=1000, packets_per_file=1, limit=None, max_asset_bytes=8 * 1024 * 1024, resume=False):
    curated, output = Path(curated), Path(output)
    if output.exists():
        raise ValueError(f"immutable output already exists: {output}")
    if curated.resolve() == output.resolve() or curated.resolve() in output.resolve().parents or output.resolve() in curated.resolve().parents:
        raise ValueError("input and output roots must be separate")
    output.parent.mkdir(parents=True, exist_ok=True)
    with writer_lock(output):
        return align_owned(curated, output, records_per_packet, packets_per_file, limit, max_asset_bytes, resume)


def align_owned(curated, output, records_per_packet, packets_per_file, limit, max_asset_bytes, resume):
    if output.exists():
        raise ValueError(f"immutable output already exists: {output}")
    if records_per_packet < 1 or packets_per_file < 1 or max_asset_bytes < 1 or (limit is not None and limit < 1):
        raise ValueError("packet sizes must be positive")
    schema = json.loads((ROOT / "contracts/corpus/common-data.schema.json").read_text())
    validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
    partial = output.with_name(output.name + ".partial")
    inputs = sorted(p for p in curated.rglob("*") if p.is_file())
    pins = {"curated": str(curated.resolve()), "output": str(output.resolve()),
            "inputs": {str(p.relative_to(curated)): {"bytes": p.stat().st_size, "sha256": digest(p)} for p in inputs},
            "schema": digest(ROOT / "contracts/corpus/common-data.schema.json"),
            "contract": digest(ROOT / "contracts/corpus/common-data-contract.json"),
            "implementation": digest(Path(__file__)), "checkpointImplementation": digest(Path(__file__).with_name("places_checkpoint.py")),
            "options": [records_per_packet, packets_per_file, limit, max_asset_bytes],
            "createdAt": dt.datetime.now(dt.timezone.utc).isoformat()}
    checkpoint = Checkpoint(output, partial, pins, resume)
    partial.mkdir(parents=True, exist_ok=True)
    packet_dir = partial / "packets"
    packet_dir.mkdir(exist_ok=True)
    sink = PacketSink(packet_dir, validator, packets_per_file, max_asset_bytes)
    if checkpoint.value["sink"]:
        restore_sink(sink, checkpoint.value["sink"])
    input_counts = Counter(checkpoint.value["input_counts"])
    type_counts = Counter(checkpoint.value["type_counts"])
    source_counts = Counter(checkpoint.value["source_counts"])
    source_manifests = {}
    cursor = checkpoint.value["cursor"]
    def save_cursor():
        checkpoint.value.update(cursor=cursor, input_counts=dict(input_counts),
                                type_counts=dict(type_counts), source_counts=dict(source_counts),
                                sink=sink_state(sink))
        checkpoint.save()
    started = time.monotonic()
    try:
        curated_manifest = json.loads((curated / "manifest.json").read_text())
        curated_manifest_sha256 = sha256_bytes((curated / "manifest.json").read_bytes())
        expected_assets = {
            file["key"]: {"bytes": file["bytes"], "sha256": file["sha256"]}
            for file in curated_manifest.get("files", [])
        }
        expected_assets.update({
            notice["key"]: {"bytes": notice["bytes"], "sha256": notice["sha256"]}
            for notice in curated_manifest.get("notices", [])
        })
        if not expected_assets:
            # Isolated unit fixtures intentionally contain only a tiny source
            # manifest.  Real accepted inputs must carry per-asset digests.
            expected_assets = None
        for source_id in ("overture-food-places", "wikidata-food-businesses"):
            source = curated_manifest["sources"][source_id]
            source_manifests[source_id] = {
                "releaseId": source["releaseId"],
                "expectedRecords": source["records"],
                "archiveSha256": source.get("archiveSha256"),
                "license": source["license"],
                "attribution": source["attribution"],
                "curatedManifestSha256": curated_manifest_sha256,
                "rawSourcePayloadPublished": source["rawSourcePayloadPublished"],
            }
            sources = ("overture-food-places", "wikidata-food-businesses")
            if cursor and sources.index(source_id) < sources.index(cursor["source"]):
                continue
            if limit and sum(input_counts.values()) >= limit:
                # Stop at the restored source just as the uninterrupted outer
                # loop does; later source metadata changes coverage/manifest.
                break
            start_cursor = cursor if cursor and cursor["source"] == source_id else None
            for row, row_cursor in curated_rows(curated, source_id, expected_assets, start_cursor, with_cursor=True):
                validate_row(row)
                provenance = row["provenance"]
                key = (provenance["sourceId"], provenance["recordId"])
                if provenance["sourceId"] != source_id:
                    raise ValueError("source identity does not match input partition")
                checkpoint.add_identity(*key)
                cursor = row_cursor
                sink.add(row)
                input_counts[provenance["sourceId"]] += 1
                source_counts[provenance["sourceId"]] += 1
                type_counts[TYPE_SITE if provenance["sourceId"] == "overture-food-places" else TYPE_ORGANIZATION] += 1
                if len(sink.current) >= records_per_packet:
                    sink.flush_packet()
                    save_cursor()
                if limit and sum(input_counts.values()) >= limit:
                    break
            if limit and sum(input_counts.values()) >= limit:
                break
        sink.flush_packet()
        # Persist the final short buffer and its cursor/identities before its
        # atomic close, so resume can verify the exact orphan if close succeeds
        # but the subsequent receipt commit is interrupted.
        save_cursor()
        sink.close()
        save_cursor()
        # Retain the Overture attribution/NOTICE texts with the graph.  They are
        # tiny primary licence artifacts, not a duplicate of the source archive.
        notice_files = []
        notice_root = curated / "notices" / "overture-food-places" / source_manifests["overture-food-places"]["releaseId"]
        if notice_root.is_dir():
            destination = partial / "licenses" / "overture-food-places"
            destination.mkdir(parents=True, exist_ok=True)
            for notice in sorted(notice_root.glob("*.txt")):
                relative_notice_key = str(notice.relative_to(curated))
                expected = expected_assets.get(relative_notice_key)
                if expected is None:
                    raise ValueError(f"{relative_notice_key}: missing input asset manifest entry")
                source_raw = notice.read_bytes()
                if len(source_raw) != expected["bytes"] or sha256_bytes(source_raw) != expected["sha256"]:
                    raise ValueError(f"{relative_notice_key}: input bytes or SHA-256 does not match accepted curated manifest")
                target = destination / notice.name
                shutil.copyfile(notice, target)
                raw = target.read_bytes()
                notice_files.append({"key": str(target.relative_to(partial)), "bytes": len(raw), "sha256": sha256_bytes(raw)})
        for source_id, manifest in source_manifests.items():
            if not limit and input_counts[source_id] != manifest["expectedRecords"]:
                raise ValueError(f"{source_id}: source count mismatch {input_counts[source_id]} != {manifest['expectedRecords']}")
        graph_counts = {
            "packets": int(sink.counts["packets"]),
            "resources": int(sink.counts["resources"]),
            "assertions": int(sink.counts["assertions"]),
            "relations": 0,
            "translations": 0,
        }
        expected_source_records = {source_id: int(details["expectedRecords"]) for source_id, details in source_manifests.items()}
        observed_source_records = {source_id: int(input_counts[source_id]) for source_id in source_manifests}
        expected_input_files = sum(len(list((curated / "records" / source).glob("*.jsonl.gz"))) for source in source_manifests)
        observed_input_files = expected_input_files if limit is None else None
        manifest = {
            "schemaVersion": "offmenu-common-places/1",
            "releaseId": "common-places-20261014",
            "status": "accepted-complete-schema-identity-citation-public-scope-checked" if limit is None else "benchmark-incomplete-not-for-publication",
            "complete": limit is None,
            "limit": limit,
            "createdAt": checkpoint.value["createdAt"],
            "packetDirectory": "packets",
            "recordsPerPacket": records_per_packet,
            "packetsPerFile": packets_per_file,
            "maxAssetBytes": max_asset_bytes,
            "counts": graph_counts,
            "expectedCounts": graph_counts if limit is None else {key: None for key in graph_counts},
            "observedCounts": graph_counts,
            "expectedSourceRecords": expected_source_records if limit is None else None,
            "observedSourceRecords": observed_source_records,
            "partitionCoverage": {
                "complete": limit is None,
                "expectedFiles": len(sink.files) if limit is None else None,
                "observedFiles": len(sink.files),
                "expectedPackets": graph_counts["packets"] if limit is None else None,
                "observedPackets": graph_counts["packets"],
            },
            "inputCoverage": {
                "complete": limit is None,
                "expectedFiles": expected_input_files,
                "observedFiles": observed_input_files,
            },
            "resourceTypes": dict(type_counts),
            "sources": source_manifests,
            "files": sink.files + notice_files,
            "licenseDocuments": notice_files,
            "guarantees": {
                "sourceIdentity": "One source-scoped common resource per normalized source record; no cross-source joins are asserted.",
                "siteOrganizationSeparation": "Overture records are Site resources. Source categories are retained as source fields and do not create an Organization, owner, producer, retailer, supplier, inventory or availability relationship.",
                "businessRoles": "Wikidata direct P31 roles remain source fields on an Organization; no claimed role is promoted to verified ownership, outlet, market coverage or stock.",
                "locations": "Source countries and locations remain typed source assertions. They are not an independent market, territorial, production-origin or cultural assertion.",
                "allFields": "Normalized top-level identity fields, provenance envelope and every data field are typed and cited assertions.",
            },
            "candidateRelationships": {
                "count": 0,
                "reason": "No source-provided cross-source relationship or reviewed crosswalk exists in these two normalized archives. Name/location similarity is not emitted as a candidate relationship.",
            },
            "input": {"curatedRelease": curated_manifest["releaseId"], "rawSourcePayloadPublished": False, "recordFiles": {source: len(list((curated / "records" / source).glob("*.jsonl.gz"))) for source in source_manifests}},
            "diskBudget": {"maximumAdditionalBytes": 25_000_000_000, "uncompressedIntermediates": False},
        }
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        manifest["manifestPayloadSha256"] = sha256_bytes(payload)
        atomic_bytes(partial / "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
        os.replace(partial, output)
        print(json.dumps({"status": "aligned", "output": str(output), "elapsedSeconds": round(time.monotonic() - started, 2), **manifest["counts"]}, sort_keys=True), flush=True)
        return manifest
    finally:
        checkpoint.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--curated", type=Path, default=Path("/home/user/src/offmenu-data/curated-expanded-country-search-20261013/blobs"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records-per-packet", type=int, default=1000)
    parser.add_argument("--packets-per-file", type=int, default=1)
    parser.add_argument("--max-asset-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true", help="Resume only a matching pinned checkpoint, never a legacy partial")
    args = parser.parse_args()
    align(args.curated, args.output, args.records_per_packet, args.packets_per_file, args.limit, args.max_asset_bytes, args.resume)


if __name__ == "__main__":
    main()
