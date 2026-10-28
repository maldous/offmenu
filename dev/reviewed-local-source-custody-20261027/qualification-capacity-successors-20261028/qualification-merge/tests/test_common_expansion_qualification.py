import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "common_expansion_qualification", ROOT / "scripts/qualify-common-expansion.py"
)
qualification = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualification)


def citation(identifier="urn:test:citation"):
    return {
        "id": identifier, "sourceId": "fixture", "originalRecordId": "row-1",
        "originalUrl": "https://example.test/source", "license": "CC0-1.0",
        "attribution": "fixture", "scope": {"visibility": "public"},
    }


def text(identifier="urn:test:text", value="name", citation_id="urn:test:citation"):
    return {
        "kind": "text", "id": identifier, "language": "en", "value": value,
        "sourceTextSha256": hashlib.sha256(value.encode()).hexdigest(),
        "status": "source-asserted", "citationIds": [citation_id],
    }


def resource(identifier="urn:test:resource", name=None):
    return {
        "id": identifier, "type": "urn:offmenu:type:FoodConcept",
        "identityStatus": "source-scoped", "names": [name or text()],
        "citationIds": ["urn:test:citation"], "scope": {"visibility": "public"},
    }


def assertion(identifier="urn:test:assertion", subject="urn:test:resource", value=None):
    return {
        "id": identifier, "subjectId": subject, "propertyId": "urn:offmenu:property:name",
        "value": value or text(), "status": "source-asserted",
        "citationIds": ["urn:test:citation"], "sourcePath": "fixture.name",
        "scope": {"visibility": "public"},
    }


def packet(resources=None, assertions=None, translations=None):
    return {
        "schemaVersion": "offmenu-common/1", "resources": resources or [],
        "assertions": assertions or [], "relations": [], "citations": [citation()],
        "translations": translations or [],
    }


def make_package(directory, packets, *, complete=True, source_records=None, mutate_manifest=None):
    directory.mkdir()
    key = "arbitrary/packet-stream.jsonl.gz"
    target = directory / key
    target.parent.mkdir()
    with gzip.open(target, "wt", encoding="utf-8") as handle:
        for item in packets:
            handle.write(json.dumps(item) + "\n")
    counts = {
        "packets": len(packets),
        "resources": sum(len(item["resources"]) for item in packets),
        "assertions": sum(len(item["assertions"]) for item in packets),
        "relations": sum(len(item["relations"]) for item in packets),
        "translations": sum(len(item["translations"]) for item in packets),
    }
    source_records = source_records if source_records is not None else {"fixture": 1}
    manifest = {
        "releaseId": directory.name, "status": "qualified", "complete": complete,
        "limit": None, "counts": counts, "expectedCounts": counts, "observedCounts": counts,
        "expectedSourceRecords": source_records, "observedSourceRecords": source_records,
        "partitionCoverage": {"complete": True, "expectedFiles": 1, "observedFiles": 1,
                              "expectedPackets": len(packets), "observedPackets": len(packets)},
        "files": [{"key": key, "bytes": target.stat().st_size,
                   "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                   "packets": len(packets)}],
    }
    if mutate_manifest:
        mutate_manifest(manifest)
    (directory / "manifest.json").write_text(json.dumps(manifest))


class CommonExpansionQualificationTests(unittest.TestCase):
    def run_qualification(self, root, *packages):
        return qualification.qualify(root / "evidence.json", root / "scratch.sqlite", list(packages))

    def test_streams_multiple_manifest_listed_files_and_resolves_global_references(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "one"
            second = root / "two"
            make_package(first, [packet(resources=[resource()])])
            translated = {
                "id": "urn:test:translation", "textId": "urn:test:text", "language": "fr",
                "value": "nom", "sourceTextSha256": hashlib.sha256(b"name").hexdigest(),
                "translator": "publisher", "method": "source-published", "status": "published-source",
                "citationIds": ["urn:test:citation"], "terminologyResourceIds": ["urn:test:resource"],
            }
            make_package(second, [packet(assertions=[assertion()], translations=[translated])])
            evidence = self.run_qualification(root, first, second)
            self.assertEqual(evidence["aggregateObservedCounts"]["packets"], 2)
            self.assertEqual(evidence["database"]["ids"], 3)
            self.assertEqual(evidence["packages"][0]["admittedSourceRecords"], {"fixture": 1})
            self.assertEqual(evidence["schemaByteSha256"], hashlib.sha256(
                (ROOT / "corpus/common-data.schema.json").read_bytes()).hexdigest())
            self.assertEqual(evidence["contractByteSha256"], hashlib.sha256(
                (ROOT / "corpus/common-data-contract.json").read_bytes()).hexdigest())
            self.assertTrue((root / "evidence.json").is_file())

    def test_rejects_partial_or_benchmark_package_before_streaming(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "partial"
            make_package(package, [packet(resources=[resource()])], complete=False)
            with self.assertRaisesRegex(qualification.QualificationError, "complete=true"):
                self.run_qualification(root, package)

    def test_checks_auxiliary_jsonl_bytes_without_misparsing_it_as_packets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "with-evidence"
            make_package(package, [packet(resources=[resource()])])
            auxiliary = package / "identity-evidence.jsonl.gz"
            with gzip.open(auxiliary, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps({"edge": "not a common graph packet"}) + "\n")
            manifest_path = package / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files"].append({"key": auxiliary.name, "bytes": auxiliary.stat().st_size,
                                      "sha256": hashlib.sha256(auxiliary.read_bytes()).hexdigest()})
            manifest_path.write_text(json.dumps(manifest))
            evidence = self.run_qualification(root, package)
            self.assertEqual(evidence["aggregateObservedCounts"]["packets"], 1)
            self.assertEqual(evidence["aggregateObservedCounts"]["assets"], 2)

    def test_rejects_conflicting_reused_text_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "conflict"
            first = resource(name=text(value="first"))
            second = resource("urn:test:resource-2", name=text(value="second"))
            make_package(package, [packet(resources=[first, second])])
            with self.assertRaisesRegex(qualification.QualificationError, "repeated text id"):
                self.run_qualification(root, package)

    def test_rejects_unresolved_non_external_reference_and_bad_quantity_dimension(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "bad-reference"
            bad = assertion(subject="urn:test:missing", value={
                "kind": "quantity", "value": 1, "unitId": "urn:offmenu:unit:g",
                "dimension": "volume", "sourceValue": 1, "sourceUnit": "g", "qualifiers": [],
            })
            make_package(package, [packet(assertions=[bad])])
            with self.assertRaisesRegex(qualification.QualificationError, "must have mass dimension"):
                self.run_qualification(root, package)

    def test_requires_authoritative_source_record_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "missing-source-counts"
            make_package(package, [packet(resources=[resource()])],
                         mutate_manifest=lambda manifest: manifest.pop("observedSourceRecords"))
            with self.assertRaisesRegex(qualification.QualificationError, "expectedSourceRecords"):
                self.run_qualification(root, package)

    def test_normalizes_accepted_scalar_source_count_using_declared_source_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "qudt"
            def scalar_source_count(manifest):
                manifest["expectedSourceRecords"] = 56
                manifest["observedSourceRecords"] = 56
                manifest["source"] = {"id": "qudt-measurement-definitions"}
            make_package(package, [packet(resources=[resource()])], mutate_manifest=scalar_source_count)
            evidence = self.run_qualification(root, package)
            self.assertEqual(evidence["packages"][0]["admittedSourceRecords"],
                             {"qudt-measurement-definitions": 56})

    def test_rejects_boolean_source_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "boolean-source-count"
            def boolean_source_count(manifest):
                manifest["expectedSourceRecords"] = True
                manifest["observedSourceRecords"] = True
                manifest["sourceId"] = "not-a-count"
            make_package(package, [packet(resources=[resource()])], mutate_manifest=boolean_source_count)
            with self.assertRaisesRegex(qualification.QualificationError, "cannot be boolean"):
                self.run_qualification(root, package)

    def test_rejects_nonpositive_optional_scratch_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "valid"
            make_package(package, [packet(resources=[resource()])])
            with self.assertRaisesRegex(qualification.QualificationError, "scratch budget"):
                qualification.qualify(root / "evidence.json", root / "scratch.sqlite", [package], 0)

    def test_rejects_restricted_source_fields_inside_typed_structures(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "restricted"
            retained = assertion(value={
                "kind": "structure", "fields": {
                    "rawFields": {"kind": "identifier", "value": "not-for-publication"},
                },
            })
            make_package(package, [packet(resources=[resource()], assertions=[retained])])
            with self.assertRaisesRegex(qualification.QualificationError, "restricted source field"):
                self.run_qualification(root, package)
