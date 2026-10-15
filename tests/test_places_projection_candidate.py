"""Contract-level integration fixture for the A3 places dataset projection.

Runs the EXISTING places->common adapter seam (align-places-common.py +
places_checkpoint.py, unchanged) over the committed byte-pinned fixture and
verifies the candidate manifest pins, source/native identity, rights,
coordinates and missingness preservation, the checkpointed output handoff and
the projection arithmetic. This is a candidate evidence fixture, not an
acceptance decision and not a bulk run.
"""
import gzip
import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "places-projection-20261015"
spec = importlib.util.spec_from_file_location("places", ROOT / "scripts" / "align-places-common.py")
places = importlib.util.module_from_spec(spec)
spec.loader.exec_module(places)

sha = lambda b: hashlib.sha256(b).hexdigest()


def fixture_row(relative_key):
    path = FIXTURE / relative_key
    with gzip.open(path, "rt", encoding="utf8") as handle:
        line = handle.readline()
    return json.loads(line)[1][0], sha(line.encode("utf8"))


def typed_leaves(node, out):
    if isinstance(node, dict):
        if "kind" in node and "value" in node and node["kind"] != "structure":
            out.append((node["kind"], node["value"]))
        for child in node.values():
            typed_leaves(child, out)
    elif isinstance(node, list):
        for child in node:
            typed_leaves(child, out)


def raw_leaves(node, scalars, nulls):
    if isinstance(node, dict):
        for child in node.values():
            raw_leaves(child, scalars, nulls)
    elif isinstance(node, list):
        for child in node:
            raw_leaves(child, scalars, nulls)
    elif node is None:
        nulls.append(True)
    else:
        scalars.append(node)


class PlacesProjectionCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((FIXTURE / "candidate-manifest.json").read_text())

    def run_fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "out"
        manifest = places.align(FIXTURE / "curated", output, records_per_packet=1, packets_per_file=1)
        return output, manifest

    def test_fixture_output_pins_and_checkpointed_handoff(self):
        output, manifest = self.run_fixture()
        pins = self.manifest["fixtureRun"]["packetPins"]
        self.assertEqual(manifest["counts"], self.manifest["fixtureRun"]["counts"])
        self.assertEqual(manifest["resourceTypes"], self.manifest["fixtureRun"]["resourceTypes"])
        self.assertTrue(manifest["complete"])
        # Deterministic output pins: actual bytes == receipts == candidate pins.
        receipts = {f["key"]: f for f in manifest["files"]}
        self.assertEqual(set(receipts), set(pins))
        for key, pin in pins.items():
            raw = (output / key).read_bytes()
            self.assertEqual(len(raw), pin["bytes"])
            self.assertEqual(sha(raw), pin["sha256"])
            self.assertEqual(receipts[key]["sha256"], pin["sha256"])
            self.assertEqual(receipts[key]["bytes"], pin["bytes"])
        # Checkpointed handoff: state checkpoint pins the inputs/schema/contract.
        checkpoint_path = output.with_name(output.name + ".checkpoint.sqlite")
        self.assertTrue(checkpoint_path.is_file())
        with sqlite3.connect(checkpoint_path) as db:
            state = json.loads(db.execute("SELECT payload FROM state WHERE id=1").fetchone()[0])
        self.assertEqual(state["pins"]["schema"], sha((ROOT / "corpus/common-data.schema.json").read_bytes()))
        self.assertEqual(state["pins"]["contract"], sha((ROOT / "corpus/common-data-contract.json").read_bytes()))
        self.assertEqual(state["pins"]["implementation"], self.manifest["implementationPins"]["alignPlacesCommon"])
        self.assertEqual(state["pins"]["checkpointImplementation"], self.manifest["implementationPins"]["placesCheckpoint"])
        expected_inputs = {str(path.relative_to(FIXTURE / "curated")): {"bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
                           for path in (FIXTURE / "curated").rglob("*") if path.is_file()}
        self.assertEqual(state["pins"]["inputs"], expected_inputs)
        self.assertEqual(state["pins"]["inputs"]["manifest.json"]["sha256"],
                         self.manifest["sourcePins"]["fixtureManifest"]["sha256"])
        self.assertFalse(output.with_name(output.name + ".alignment.lock").exists())
        self.assertFalse(manifest["diskBudget"]["uncompressedIntermediates"])

    def test_identity_rights_coordinates_missingness_preserved(self):
        output, _ = self.run_fixture()
        packets = []
        for path in sorted((output / "packets").glob("*.jsonl.gz")):
            packets.extend(json.loads(line) for line in gzip.open(path, "rt", encoding="utf8") if line.strip())
        resources = {r["id"]: r for packet in packets for r in packet["resources"]}
        citations = {c["id"]: c for packet in packets for c in packet["citations"]}
        source_records, original_ids = {}, {}
        for packet in packets:
            for assertion in packet["assertions"]:
                if assertion["sourcePath"] == "$.sourceRecord":
                    source_records[assertion["subjectId"]] = assertion["value"]
                elif assertion["sourcePath"] == "$.id":
                    original_ids[assertion["subjectId"]] = assertion["value"]
        rows_with_nulls = 0
        for key, expected in self.manifest["sourcePins"]["linePreservation"].items():
            row, line_sha = fixture_row(key)
            self.assertEqual(line_sha, expected["lineSha256"])  # native row bytes preserved
            resource_id = expected["expectedResourceId"]
            self.assertIn(resource_id, resources)  # source/native identity
            self.assertEqual(original_ids[resource_id], {"kind": "identifier", "value": row["id"]})
            citation = citations[resources[resource_id]["citationIds"][0]]
            self.assertEqual(citation["license"], row["provenance"]["license"])  # rights
            self.assertEqual(citation["attribution"], row["provenance"]["attribution"])
            self.assertEqual(citation["originalUrl"], row["provenance"]["url"])
            self.assertEqual(citation["rightsEvidenceUrl"], row["provenance"].get("licenseUrl") or row["provenance"]["url"])
            typed = source_records[resource_id]["fields"]
            self.assertEqual(sorted(typed), sorted(["schemaVersion", "kind", "countries", "provenance", "curation", "data"]))
            # Source identity fields are excluded here ($.id assertion holds row id);
            # every other source scalar must survive as a typed value, nulls stay
            # typed nulls, and absent fields are never invented (unknown != zero).
            leaves = []
            typed_leaves(typed, leaves)
            values = [value for _, value in leaves]
            scalars, nulls = [], []
            raw_leaves({k: v for k, v in row.items() if k != "id"}, scalars, nulls)
            for scalar in scalars:
                self.assertIn(scalar, values)
            self.assertEqual(sum(1 for kind, value in leaves if kind == "null" and value is None), len(nulls))
            if nulls:
                rows_with_nulls += 1
            # Coordinates retained exactly, as numbers, without projection.
            text = json.dumps(typed)
            for needle in ("latitude", "longitude", "coordinates", "geometry"):
                if needle in json.dumps(row):
                    self.assertIn(needle, text)
            if "latitude" in json.dumps(row):
                self.assertIn(row["data"]["locations"][0]["latitude"], values)
                self.assertIn(row["data"]["locations"][0]["longitude"], values)
            self.assertEqual(set(typed["data"]["fields"]), set(row["data"]))  # no invented data fields
        self.assertGreaterEqual(rows_with_nulls, 1)  # missingness path exercised

    def test_projection_arithmetic_and_gates(self):
        projection = self.manifest["projectionDeclaration"]
        measured, denominators = projection["measurement"], projection["denominators"]
        self.assertEqual(denominators["totalRecords"], denominators["overture-food-places"] + denominators["wikidata-food-businesses"])
        expected_compressed = round(sum(denominators[source] * measured[source]["compressedBytesPerRecord"] for source in ("overture-food-places", "wikidata-food-businesses")))
        self.assertEqual(projection["projectedPacketBytes"]["compressed"], expected_compressed)
        self.assertFalse(projection["projectedPacketBytes"]["uncompressedMaterialized"])
        joined = json.dumps(self.manifest)
        self.assertIn("NOT zero", joined)
        self.assertIn("Morgan verdict", self.manifest["acceptanceGates"]["requires"])
        self.assertIn("independent exact review", self.manifest["acceptanceGates"]["requires"][0])
        self.assertTrue(self.manifest["acceptanceGates"]["status"].startswith("CANDIDATE"))
        self.assertIn("bulk places run", self.manifest["storageGates"]["blocked"])
        curated = Path("/home/user/src/offmenu-data/curated-expanded-country-search-20261013/blobs/manifest.json")
        if not curated.is_file():
            self.skipTest("local curated manifest unavailable")
        self.assertEqual(sha(curated.read_bytes()), self.manifest["sourcePins"]["curatedManifest"]["sha256"])
        sources = json.loads(curated.read_text())["sources"]
        self.assertEqual(denominators["overture-food-places"], sources["overture-food-places"]["records"])
        self.assertEqual(denominators["wikidata-food-businesses"], sources["wikidata-food-businesses"]["records"])

    def test_fixture_file_pins_match_candidate_manifest(self):
        for entry in self.manifest["sourcePins"]["fixtureFiles"]:
            raw = (FIXTURE / entry["key"]).read_bytes()
            self.assertEqual(len(raw), entry["bytes"])
            self.assertEqual(sha(raw), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
