import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "repair-bulk-controls-20261014.py"
SPEC = importlib.util.spec_from_file_location("bulk_repair", SCRIPT)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


def packet():
    return {
        "assertions": [{
            "propertyId": "urn:offmenu:property:curatedRecordContext",
            "value": {"fields": {"provenance": {"fields": {"transform": {
                "kind": "text", "id": "urn:removed", "language": "und", "value": "offmenu-curation/1",
                "sourceTextSha256": "x", "status": "source-asserted", "citationIds": ["c"],
            }}}}},
        }],
        "resources": [{"id": "r", "names": [{"kind": "text", "value": "unchanged"}]}],
        "relations": [], "citations": [{"sourceId": "off"}], "translations": [],
    }


class BulkControlRecoveryTests(unittest.TestCase):
    def test_changes_only_transform_type_and_preserves_value(self):
        before = packet()
        after, old_id = repair.repair_packet(before)
        self.assertEqual(old_id, "urn:removed")
        self.assertEqual(repair.control_node(after), {"kind": "identifier", "value": "offmenu-curation/1"})
        self.assertEqual(before["resources"], after["resources"])
        self.assertEqual(before["citations"], after["citations"])

    def test_rejects_removed_text_id_reference(self):
        before = packet()
        before["relations"].append({"comment": "urn:removed"})
        with self.assertRaisesRegex(ValueError, "remains referenced"):
            repair.repair_packet(before)

    def test_normalizes_per_source_coverage_without_losing_it(self):
        source_coverage = {"off": {"complete": True, "expectedFiles": 2, "observedFiles": 2}}
        normalized = repair.normalize_input_coverage(source_coverage)
        self.assertTrue(normalized["complete"])
        self.assertEqual(normalized["expectedFiles"], 2)
        self.assertEqual(normalized["sources"], source_coverage)

    def test_atomic_asset_repair_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "output"
            (source / "packets").mkdir(parents=True)
            original = json.dumps(packet(), separators=(",", ":")) + "\n"
            compressed = gzip.compress(original.encode(), mtime=0)
            input_path = source / "packets" / "part-00000.jsonl.gz"
            input_path.write_bytes(compressed)
            entry = {"key": "packets/part-00000.jsonl.gz", "bytes": len(compressed), "sha256": hashlib.sha256(compressed).hexdigest(), "packets": 1}
            first, count = repair.repair_asset(source, output, entry)
            second_root = root / "output2"
            second, second_count = repair.repair_asset(source, second_root, entry)
            self.assertEqual(count, second_count)
            self.assertEqual(first, second)
            self.assertFalse(list(output.rglob("*.tmp.*")))


if __name__ == "__main__":
    unittest.main()
