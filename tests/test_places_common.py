import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema_rs

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("places", ROOT / "scripts/align-places-common.py")
places = importlib.util.module_from_spec(spec)
spec.loader.exec_module(places)


class PlacesCommonTests(unittest.TestCase):
    def normalized(self, directory, source, record, kind, data):
        destination = directory / "records" / source
        destination.mkdir(parents=True, exist_ok=True)
        row = {
            "schemaVersion": "1.0", "kind": kind, "id": f"{source}:{kind}:{record}", "countries": ["AU"],
            "provenance": {"sourceId": source, "recordId": record, "url": "https://example.org/record", "license": "CC0 1.0", "licenseUrl": "https://example.org/license", "attribution": "Example", "visibility": "public", "releaseId": "fixture", "sourceDate": "2026-10-14"},
            "data": data,
        }
        with gzip.open(destination / "00.jsonl.gz", "wt", encoding="utf-8") as handle:
            handle.write(json.dumps(["offmenu:fixture", [row]]) + "\n")

    def test_sites_and_organizations_remain_distinct_and_all_fields_are_typed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            curated, output = root / "curated", root / "out"
            self.normalized(curated, "overture-food-places", "gers-1", "retailer", {"name": "A Shop", "taxonomy": {"primary": "grocery_store"}, "ownershipVerified": False, "locations": [{"country": "AU"}]})
            self.normalized(curated, "wikidata-food-businesses", "Q1", "organization", {"name": "A Company", "roles": ["food-manufacturer"], "websites": ["https://example.org"]})
            (curated / "manifest.json").write_text(json.dumps({"releaseId": "fixture", "sources": {source: {"releaseId": "fixture", "records": 1, "license": "CC0 1.0", "attribution": "Example", "rawSourcePayloadPublished": False} for source in ["overture-food-places", "wikidata-food-businesses"]}}))
            manifest = places.align(curated, output, records_per_packet=1, packets_per_file=1)
            self.assertEqual(manifest["counts"]["resources"], 2)
            packets = []
            for file in manifest["files"]:
                if "packets" not in file:
                    continue
                self.assertTrue(file["key"].startswith("packets/"))
                self.assertLessEqual(file["bytes"], manifest["maxAssetBytes"])
                packets.extend(json.loads(line) for line in gzip.open(output / file["key"], "rt") if line.strip())
            resources = {r["id"]: r for packet in packets for r in packet["resources"]}
            self.assertEqual({r["type"] for r in resources.values()}, {places.TYPE_SITE, places.TYPE_ORGANIZATION})
            self.assertFalse(any(r["type"] == "urn:offmenu:type:Retailer" for r in resources.values()))
            paths = {a["sourcePath"] for packet in packets for a in packet["assertions"]}
            self.assertIn("$.sourceRecord", paths)
            record_facts = [a for packet in packets for a in packet["assertions"] if a["sourcePath"] == "$.sourceRecord"]
            nested_keys = {key for fact in record_facts for key in fact["value"]["fields"]}
            self.assertTrue({"data", "provenance", "countries"} <= nested_keys)
            self.assertEqual(manifest["candidateRelationships"]["count"], 0)
            self.assertTrue(manifest["complete"])
            schema = json.loads((ROOT / "corpus/common-data.schema.json").read_text())
            validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
            for packet in packets:
                validator.validate(packet)


if __name__ == "__main__":
    unittest.main()
