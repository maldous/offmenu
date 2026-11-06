#!/usr/bin/env python3
"""Stream and independently qualify complete OffMenu common-schema packages.

This is deliberately separate from package assembly.  It keeps only SHA-256
keys in SQLite so a release with tens of millions of records never needs an
in-memory identity set.
"""
import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import jsonschema_rs


ROOT = Path(__file__).resolve().parents[1]
GRANDFATHER_MANIFEST_SHA256 = (
    "c15005b224ae18c1e660837c6ac9fab88beb0b4d53ce34db6a5a87f12f6d919d"
)
GRANDFATHER_STATUS = "all-packets-schema-identity-citation-and-scope-checked"
GRANDFATHER_RECIPE_RECORDS = 25_135
GRANDFATHER_FOODON_CLASSES = 29_255
MINIMUM_FREE_BYTES = 10 * 1024 ** 3
DEFAULT_SCRATCH_BUDGET_GIB = 20
COMMIT_EVERY = 10_000
KNOWN_DIMENSIONS = {
    "urn:offmenu:unit:g": "mass",
    "urn:offmenu:unit:kg": "mass",
    "urn:offmenu:unit:mg": "mass",
    "urn:offmenu:unit:microgram": "mass",
    "urn:offmenu:unit:ml": "volume",
    "urn:offmenu:unit:l": "volume",
    "urn:offmenu:unit:count": "count",
    "urn:offmenu:unit:portion": "count",
}
FORBIDDEN_STRUCTURED_FIELDS = {
    "rawFields", "rawNutriments", "ingredientsText", "originalTextLines",
    "sealed", "credentials", "owner", "proofId",
}


class QualificationError(ValueError):
    """A deterministic release-admission or graph-integrity failure."""


def sha_bytes(value):
    return hashlib.sha256(value).digest()


def id_hash(value):
    return sha_bytes(value.encode("utf-8"))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message):
    raise QualificationError(message)


def require_public(scope, location):
    if not isinstance(scope, dict) or scope.get("visibility") != "public":
        fail(f"{location}: non-public scope is not admissible")


def externally_allowed(value):
    return value.startswith((
        "urn:offmenu:country:", "urn:offmenu:unit:", "http://", "https://",
    ))


def manifest_is_grandfathered(directory, manifest, manifest_sha):
    return (
        directory.name == "common-data-reviewed-package-20261014"
        and manifest_sha == GRANDFATHER_MANIFEST_SHA256
        and manifest.get("status") == GRANDFATHER_STATUS
    )


def admission_check(directory, manifest, manifest_sha):
    """Reject partial source packages before reading their packet files."""
    if manifest_is_grandfathered(directory, manifest, manifest_sha):
        return {"grandfathered": True}
    if manifest.get("complete") is not True:
        fail(f"{directory}: source package must declare complete=true")
    if "limit" not in manifest or manifest["limit"] is not None:
        fail(f"{directory}: source package must declare limit=null")
    expected = manifest.get("expectedCounts")
    observed = manifest.get("observedCounts")
    manifest_counts = manifest.get("counts")
    expected_source_records = manifest.get("expectedSourceRecords")
    observed_source_records = manifest.get("observedSourceRecords")
    coverage = manifest.get("partitionCoverage")
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        fail(f"{directory}: expectedCounts and observedCounts are required objects")
    if not isinstance(manifest_counts, dict):
        fail(f"{directory}: counts is a required object")
    for key in ("packets", "resources", "assertions", "relations", "translations"):
        if not all(isinstance(group.get(key), int) for group in (expected, observed, manifest_counts)):
            fail(f"{directory}: expectedCounts/observedCounts/counts.{key} must be integers")
    if expected_source_records is None or observed_source_records is None:
        fail(f"{directory}: expectedSourceRecords and observedSourceRecords are required")
    if isinstance(expected_source_records, bool) or isinstance(observed_source_records, bool):
        fail(f"{directory}: source record counts cannot be boolean")
    if type(expected_source_records) is not type(observed_source_records) or expected_source_records != observed_source_records:
        fail(f"{directory}: observed source-record coverage does not equal expected source records")
    if not isinstance(coverage, dict) or coverage.get("complete") is not True:
        fail(f"{directory}: partitionCoverage.complete=true is required")
    for key, value in expected.items():
        if observed.get(key) != value:
            fail(f"{directory}: observedCounts.{key} does not equal expectedCounts.{key}")
    for key in ("expectedFiles", "observedFiles", "expectedPackets", "observedPackets"):
        if key not in coverage:
            fail(f"{directory}: partitionCoverage.{key} is required")
    if coverage["expectedFiles"] != coverage["observedFiles"]:
        fail(f"{directory}: partition file coverage is incomplete")
    if coverage["expectedPackets"] != coverage["observedPackets"]:
        fail(f"{directory}: partition packet coverage is incomplete")
    input_coverage = manifest.get("inputCoverage")
    if input_coverage is not None:
        if not isinstance(input_coverage, dict) or input_coverage.get("complete") is not True:
            fail(f"{directory}: inputCoverage must be a complete object when supplied")
        for key in ("expectedFiles", "observedFiles"):
            if key not in input_coverage:
                fail(f"{directory}: inputCoverage.{key} is required when inputCoverage is supplied")
        if input_coverage["expectedFiles"] != input_coverage["observedFiles"]:
            fail(f"{directory}: input source-file coverage is incomplete")
    return {"grandfathered": False}


def admitted_source_records(directory, manifest, grandfathered):
    """Return the admitted input count map bound into qualification evidence."""
    if grandfathered:
        if manifest.get("recipeRecords") != GRANDFATHER_RECIPE_RECORDS:
            fail(f"{directory}: grandfather recipe record count changed")
        foodon_path = directory / "foodon-source-manifest.json"
        if not foodon_path.is_file():
            fail(f"{directory}: grandfather FoodOn source manifest is missing")
        foodon = json.loads(foodon_path.read_text())
        if foodon.get("sourceId") != "foodon" or foodon.get("counts", {}).get("classes") != GRANDFATHER_FOODON_CLASSES:
            fail(f"{directory}: grandfather FoodOn source count changed")
        return {"world-recipes": GRANDFATHER_RECIPE_RECORDS, "foodon": GRANDFATHER_FOODON_CLASSES}
    observed = manifest.get("observedSourceRecords")
    if isinstance(observed, bool):
        fail(f"{directory}: observedSourceRecords cannot be boolean")
    if isinstance(observed, int):
        source = manifest.get("source")
        source_id = manifest.get("sourceId") or (source.get("id") if isinstance(source, dict) else None)
        if not isinstance(source_id, str) or not source_id:
            fail(f"{directory}: scalar observedSourceRecords requires manifest.source.id or sourceId")
        if observed < 0:
            fail(f"{directory}: observedSourceRecords must be nonnegative")
        return {source_id: observed}
    if not isinstance(observed, dict) or not all(
        isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for key, value in observed.items()
    ):
        fail(f"{directory}: observedSourceRecords must be a nonnegative count map")
    return dict(sorted(observed.items()))


class Database:
    def __init__(self, path, scratch_budget_bytes):
        self.path = path
        self.scratch_budget_bytes = scratch_budget_bytes
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=OFF")
        self.connection.execute("PRAGMA synchronous=OFF")
        self.connection.execute("PRAGMA temp_store=FILE")
        self.connection.execute("PRAGMA cache_size=-65536")
        self.connection.executescript("""
            CREATE TABLE ids (
              kind TEXT NOT NULL,
              id_sha256 BLOB NOT NULL,
              PRIMARY KEY (kind, id_sha256)
            ) WITHOUT ROWID;
            CREATE TABLE texts (
              id_sha256 BLOB PRIMARY KEY,
              identity_sha256 BLOB NOT NULL,
              source_sha256 BLOB NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE citations (
              id_sha256 BLOB PRIMARY KEY,
              canonical_sha256 BLOB NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE references_pending (
              target_kind TEXT NOT NULL,
              id_sha256 BLOB NOT NULL,
              PRIMARY KEY (target_kind, id_sha256)
            ) WITHOUT ROWID;
            CREATE TABLE translation_sources (
              text_id_sha256 BLOB NOT NULL,
              source_sha256 BLOB NOT NULL,
              PRIMARY KEY (text_id_sha256, source_sha256)
            ) WITHOUT ROWID;
        """)
        self.pending = 0

    def commit_if_needed(self):
        if self.pending >= COMMIT_EVERY:
            self.connection.commit()
            self.pending = 0
            self.check_budget()

    def check_budget(self):
        if self.path.exists() and self.path.stat().st_size > self.scratch_budget_bytes:
            fail("SQLite qualification scratch exceeded its configured budget")
        if shutil.disk_usage(self.path.parent).free < MINIMUM_FREE_BYTES:
            fail("less than 10 GiB free during SQLite qualification")

    def unique_id(self, kind, value, location):
        try:
            self.connection.execute("INSERT INTO ids VALUES (?, ?)", (kind, id_hash(value)))
        except sqlite3.IntegrityError:
            fail(f"{location}: duplicate global {kind} id {value}")
        self.pending += 1

    def text(self, value, location):
        identifier = id_hash(value["id"])
        source = hashlib.sha256(value["value"].encode("utf-8")).digest()
        if source.hex() != value["sourceTextSha256"]:
            fail(f"{location}: source text SHA-256 mismatch")
        identity = sha_bytes(canonical({
            "language": value["language"],
            "value": value["value"],
            "sourceTextSha256": value["sourceTextSha256"],
            "citationIds": sorted(set(value["citationIds"])),
        }).encode("utf-8"))
        previous = self.connection.execute(
            "SELECT identity_sha256 FROM texts WHERE id_sha256=?", (identifier,)
        ).fetchone()
        if previous is None:
            self.connection.execute("INSERT INTO texts VALUES (?, ?, ?)", (identifier, identity, source))
        elif previous[0] != identity:
            fail(f"{location}: repeated text id has different language/value/hash/citations")
        self.pending += 1

    def citation(self, value, location):
        require_public(value.get("scope"), location)
        identifier = id_hash(value["id"])
        digest = sha_bytes(canonical(value).encode("utf-8"))
        previous = self.connection.execute(
            "SELECT canonical_sha256 FROM citations WHERE id_sha256=?", (identifier,)
        ).fetchone()
        if previous is None:
            self.connection.execute("INSERT INTO citations VALUES (?, ?)", (identifier, digest))
        elif previous[0] != digest:
            fail(f"{location}: repeated citation id has different canonical content")
        self.pending += 1

    def reference(self, kind, value, location, stats, allow_external=True):
        if allow_external and externally_allowed(value):
            stats["externalReferences"] += 1
            return
        self.connection.execute(
            "INSERT OR IGNORE INTO references_pending VALUES (?, ?)", (kind, id_hash(value))
        )
        self.pending += 1

    def translation(self, value, location):
        self.unique_id("translation", value["id"], location)
        self.connection.execute(
            "INSERT OR IGNORE INTO translation_sources VALUES (?, ?)",
            (id_hash(value["textId"]), bytes.fromhex(value["sourceTextSha256"])),
        )
        self.pending += 1

    def finish(self):
        self.connection.commit()
        self.check_budget()
        unresolved = self.connection.execute("""
            SELECT count(*) FROM references_pending p
            LEFT JOIN ids i ON i.kind=p.target_kind AND i.id_sha256=p.id_sha256
            WHERE i.id_sha256 IS NULL
        """).fetchone()[0]
        if unresolved:
            fail(f"{unresolved} internal resource/assertion references do not resolve globally")
        bad_translations = self.connection.execute("""
            SELECT count(*) FROM translation_sources x
            LEFT JOIN texts t ON t.id_sha256=x.text_id_sha256
            WHERE t.id_sha256 IS NULL OR t.source_sha256 != x.source_sha256
        """).fetchone()[0]
        if bad_translations:
            fail(f"{bad_translations} translations do not reference the correct original text hash")
        result = {}
        for table in ("ids", "texts", "citations", "translation_sources"):
            result[table] = self.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        result["referencesRecorded"] = self.connection.execute(
            "SELECT count(*) FROM references_pending"
        ).fetchone()[0]
        self.connection.close()
        return result


def check_packet_citations(packet, location):
    values = packet["citations"]
    by_id = {}
    for citation in values:
        if citation["id"] in by_id:
            fail(f"{location}: duplicate packet citation id {citation['id']}")
        by_id[citation["id"]] = citation

    def require_ids(ids, child_location):
        for identifier in ids:
            if identifier not in by_id:
                fail(f"{child_location}: citation {identifier} is not in this packet")
    return require_ids


def walk_value(value, location, db, require_citations, stats):
    kind = value.get("kind")
    if kind == "text":
        require_citations(value["citationIds"], location)
        db.text(value, location)
    elif kind == "reference":
        db.reference("resource", value["id"], location, stats)
    elif kind == "quantity":
        unit = value.get("unitId")
        expected_dimension = KNOWN_DIMENSIONS.get(unit)
        if expected_dimension and value.get("dimension") != expected_dimension:
            fail(f"{location}: {unit} must have {expected_dimension} dimension")
        for field in ("unitId", "countedEntityId", "preparationStateId", "methodId", "definitionId"):
            target = value.get(field)
            if target:
                db.reference("resource", target, f"{location}.{field}", stats)
        if value.get("sourceNotation") is not None:
            walk_value(value["sourceNotation"], location + ".sourceNotation", db, require_citations, stats)
        if value.get("basis") is not None:
            walk_value(value["basis"], location + ".basis", db, require_citations, stats)
    elif kind == "list":
        for index, child in enumerate(value["items"]):
            walk_value(child, f"{location}.items[{index}]", db, require_citations, stats)
    elif kind == "structure":
        for key, child in value["fields"].items():
            if key in FORBIDDEN_STRUCTURED_FIELDS:
                fail(f"{location}.fields.{key}: retained restricted source field is not public-corpus data")
            walk_value(child, f"{location}.fields.{key}", db, require_citations, stats)


def packet_counts(packet):
    return Counter({
        "packets": 1,
        "resources": len(packet["resources"]),
        "assertions": len(packet["assertions"]),
        "relations": len(packet["relations"]),
        "translations": len(packet["translations"]),
    })


def validate_packet(packet, location, validator, registered_types, db, stats):
    try:
        validator.validate(packet)
    except Exception as error:
        fail(f"{location}: schema validation failed: {error}")
    require_citations = check_packet_citations(packet, location)
    for index, citation in enumerate(packet["citations"]):
        db.citation(citation, f"{location}.citations[{index}]")
    for index, resource in enumerate(packet["resources"]):
        child = f"{location}.resources[{index}]"
        require_public(resource["scope"], child)
        if resource["type"] not in registered_types:
            fail(f"{child}: unregistered resource type {resource['type']}")
        for extra in resource.get("additionalTypes", []):
            if extra not in registered_types:
                fail(f"{child}: unregistered additional resource type {extra}")
        require_citations(resource["citationIds"], child)
        db.unique_id("resource", resource["id"], child)
        for name_index, name in enumerate(resource["names"]):
            walk_value(name, f"{child}.names[{name_index}]", db, require_citations, stats)
    for index, assertion in enumerate(packet["assertions"]):
        child = f"{location}.assertions[{index}]"
        require_public(assertion["scope"], child)
        require_citations(assertion["citationIds"], child)
        db.unique_id("assertion", assertion["id"], child)
        db.reference("resource", assertion["subjectId"], child + ".subjectId", stats, allow_external=False)
        for cultural in assertion.get("culturalRepresentationIds", []):
            db.reference("resource", cultural, child + ".culturalRepresentationIds", stats, allow_external=False)
        walk_value(assertion["value"], child + ".value", db, require_citations, stats)
        for input_id in assertion.get("derivation", {}).get("inputAssertionIds", []):
            db.reference("assertion", input_id, child + ".derivation.inputAssertionIds", stats, allow_external=False)
    for index, relation in enumerate(packet["relations"]):
        child = f"{location}.relations[{index}]"
        require_public(relation["scope"], child)
        require_citations(relation["citationIds"], child)
        db.unique_id("relation", relation["id"], child)
        db.reference("resource", relation["subjectId"], child + ".subjectId", stats, allow_external=False)
        db.reference("resource", relation["objectId"], child + ".objectId", stats)
    for index, translation in enumerate(packet["translations"]):
        child = f"{location}.translations[{index}]"
        require_citations(translation["citationIds"], child)
        for term in translation["terminologyResourceIds"]:
            db.reference("resource", term, child + ".terminologyResourceIds", stats, allow_external=False)
        db.translation(translation, child)


def listed_assets(directory, manifest):
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        fail(f"{directory}: manifest.files is required")
    result = []
    for entry in files:
        key = entry.get("key") if isinstance(entry, dict) else None
        if not isinstance(key, str) or key.startswith("/") or ".." in Path(key).parts:
            fail(f"{directory}: unsafe manifest file key")
        for required in ("bytes", "sha256"):
            if required not in entry:
                fail(f"{directory}/{key}: asset metadata {required} is required")
        if "packets" in entry:
            if not key.endswith(".jsonl.gz"):
                fail(f"{directory}/{key}: packet metadata is only valid for JSONL gzip assets")
            result.append(entry)
    if not result:
        fail(f"{directory}: manifest lists no JSONL gzip packet files")
    return files, result


def qualify(evidence_path, scratch_path, package_dirs, scratch_budget_gib=DEFAULT_SCRATCH_BUDGET_GIB):
    if evidence_path.exists():
        fail(f"evidence output already exists: {evidence_path}")
    if scratch_path.exists():
        fail(f"scratch SQLite path already exists: {scratch_path}")
    if scratch_budget_gib <= 0:
        fail("scratch budget must be greater than zero GiB")
    scratch_budget_bytes = int(scratch_budget_gib * 1024 ** 3)
    scratch_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(scratch_path.parent).free < MINIMUM_FREE_BYTES:
        fail("less than 10 GiB free for bounded SQLite qualification scratch space")
    schema_path = ROOT / "corpus/common-data.schema.json"
    contract_path = ROOT / "corpus/common-data-contract.json"
    schema_bytes = schema_path.read_bytes()
    contract_bytes = contract_path.read_bytes()
    schema = json.loads(schema_bytes)
    contract = json.loads(contract_bytes)
    validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
    registered_types = {value["id"] for value in contract["types"].values()}
    db = Database(scratch_path, scratch_budget_bytes)
    aggregate = Counter()
    packages = []
    started = time.time()
    try:
        for directory in package_dirs:
            directory = directory.resolve()
            manifest_path = directory / "manifest.json"
            if not manifest_path.is_file():
                fail(f"missing package manifest: {manifest_path}")
            manifest_sha = sha_file(manifest_path)
            manifest = json.loads(manifest_path.read_text())
            admission = admission_check(directory, manifest, manifest_sha)
            observed = Counter()
            assets, files = listed_assets(directory, manifest)
            for asset in assets:
                asset_path = directory / asset["key"]
                if not asset_path.is_file():
                    fail(f"missing manifest-listed file: {asset_path}")
                if asset_path.stat().st_size != asset["bytes"] or sha_file(asset_path) != asset["sha256"]:
                    fail(f"{asset_path}: byte length or SHA-256 does not match manifest")
                aggregate["assets"] += 1
            for file_number, entry in enumerate(files, 1):
                path = directory / entry["key"]
                packet_count = 0
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, 1):
                        if not line.strip():
                            continue
                        try:
                            packet = json.loads(line)
                        except json.JSONDecodeError as error:
                            fail(f"{path}:{line_number}: invalid JSON: {error}")
                        location = f"{path.name}:{line_number}"
                        validate_packet(packet, location, validator, registered_types, db, aggregate)
                        observed.update(packet_counts(packet))
                        packet_count += 1
                        if packet_count % 100_000 == 0:
                            print(json.dumps({"progress": "packets-qualified", "package": directory.name,
                                              "file": entry["key"], "packets": packet_count}),
                                  file=sys.stderr, flush=True)
                        db.commit_if_needed()
                if packet_count != entry["packets"]:
                    fail(f"{path}: observed {packet_count} packets, manifest declares {entry['packets']}")
                print(json.dumps({"progress": "file-qualified", "package": directory.name,
                                  "file": file_number, "files": len(files), "packets": packet_count}), file=sys.stderr, flush=True)
            if observed["packets"] != sum(entry["packets"] for entry in files):
                fail(f"{directory}: total packet count does not equal manifest file metadata")
            if not admission["grandfathered"]:
                for key, value in observed.items():
                    if manifest["expectedCounts"].get(key) != value:
                        fail(f"{directory}: expectedCounts.{key}={manifest['expectedCounts'].get(key)}; streamed {value}")
                    if manifest["observedCounts"].get(key) != value:
                        fail(f"{directory}: observedCounts.{key}={manifest['observedCounts'].get(key)}; streamed {value}")
                coverage = manifest["partitionCoverage"]
                if coverage["observedFiles"] != len(files) or coverage["observedPackets"] != observed["packets"]:
                    fail(f"{directory}: partition coverage does not equal streamed files/packets")
            for key, value in observed.items():
                if manifest["counts"].get(key) != value:
                    fail(f"{directory}: counts.{key}={manifest['counts'].get(key)}; streamed {value}")
            packages.append({
                "directory": str(directory), "releaseId": manifest.get("releaseId"),
                "manifestByteSha256": manifest_sha, "grandfathered": admission["grandfathered"],
                "packetFiles": len(files), "observedCounts": dict(observed),
                "admittedSourceRecords": admitted_source_records(directory, manifest, admission["grandfathered"]),
            })
            aggregate.update(observed)
        db_counts = db.finish()
    except Exception:
        db.connection.close()
        raise
    evidence = {
        "schemaVersion": "offmenu-common-expansion-qualification/1",
        "status": "all-packages-streamed-global-identities-references-and-provenance-checked",
        "schemaByteSha256": hashlib.sha256(schema_bytes).hexdigest(),
        "contractByteSha256": hashlib.sha256(contract_bytes).hexdigest(),
        "contractVersion": contract["schemaVersion"], "schemaId": schema.get("$id"),
        "packageCount": len(packages), "packages": packages,
        "aggregateObservedCounts": dict(aggregate), "database": db_counts,
        "diskGuardBytes": MINIMUM_FREE_BYTES, "scratchBudgetBytes": scratch_budget_bytes,
        "seconds": round(time.time() - started, 3),
        "contractTextIdentityRule": contract["textIdentityRule"],
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(evidence, ensure_ascii=False))
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, help="new JSON evidence output path")
    parser.add_argument("scratch", type=Path, help="new SQLite scratch database path")
    parser.add_argument("--scratch-budget-gib", type=float, default=DEFAULT_SCRATCH_BUDGET_GIB,
                        help="maximum SQLite scratch size in GiB (default: 20)")
    parser.add_argument("packages", nargs="+", type=Path, help="complete common-schema package directories")
    args = parser.parse_args()
    try:
        qualify(args.evidence, args.scratch, args.packages, args.scratch_budget_gib)
    except QualificationError as error:
        print(json.dumps({"status": "qualification-failed", "error": str(error)}), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
