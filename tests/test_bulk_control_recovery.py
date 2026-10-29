import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / 'tools/data-processing' / 'repair_bulk_controls_20261014.py'
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
    def source_fixture(self, root):
        source = root / "source"
        (source / "packets").mkdir(parents=True)
        entries = []
        for index, source_id in enumerate(["off", "usda-files", "prices"]):
            value = packet()
            value["citations"][0]["sourceId"] = source_id
            data = gzip.compress((json.dumps(value) + "\n").encode(), mtime=0)
            key = f"packets/part-{index:05d}.jsonl.gz"
            (source / key).write_bytes(data)
            entries.append({"key": key, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "packets": 1})
        manifest = {"files": entries, "releaseId": "fixture", "counts": {"packets": 3}, "inputCoverage": {"fixture": {"complete": True, "expectedFiles": 3, "observedFiles": 3}}}
        manifest["manifestSha256"] = repair.manifest_payload_digest(manifest)
        (source / "manifest.json").write_text(json.dumps(manifest))
        return source

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

    def test_asset_bytes_are_identical_across_worker_processes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "packets").mkdir(parents=True)
            data = gzip.compress((json.dumps(packet()) + "\n").encode(), mtime=0)
            (source / "packets/part-00000.jsonl.gz").write_bytes(data)
            entry = {"key": "packets/part-00000.jsonl.gz", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "packets": 1}
            code = "import importlib.util,json,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('repair',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.repair_asset(Path(sys.argv[2]),Path(sys.argv[3]),json.loads(sys.argv[4]))"
            for directory in [root / "worker1", root / "worker2"]:
                subprocess.run([sys.executable, "-c", code, str(SCRIPT), str(source), str(directory), json.dumps(entry)], check=True, capture_output=True)
            self.assertEqual((root / "worker1" / entry["key"]).read_bytes(), (root / "worker2" / entry["key"]).read_bytes())

    def test_interrupted_repair_resumes_without_overwriting_completed_asset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_fixture(root)
            output = root / "recovery"
            original_function = repair.repair_asset
            def interrupted(input_root, output_root, entry):
                if entry["key"].endswith("00001.jsonl.gz"):
                    raise RuntimeError("simulated interruption")
                return original_function(input_root, output_root, entry)
            with patch.object(repair, "repair_asset", side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    repair.repair(source, output, workers=1)
            first = output / "packets/part-00000.jsonl.gz"
            before = (first.read_bytes(), first.stat().st_mtime_ns)
            result = repair.repair(source, output, workers=1, resume=True)
            self.assertEqual(before, (first.read_bytes(), first.stat().st_mtime_ns))
            baseline = repair.repair(source, root / "baseline", workers=1)
            self.assertEqual(result, baseline)
            self.assertTrue(json.loads((output / "checkpoint.json").read_text())["complete"])
            with self.assertRaisesRegex(ValueError, "completed immutable"):
                repair.repair(source, output, workers=1, resume=True)

    def test_resume_requires_pins_and_rejects_legacy_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_fixture(root)
            output = root / "recovery"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "legacy partial"):
                repair.repair(source, output, workers=1, resume=True)
            checkpoint = {"schemaVersion": "offmenu-bulk-repair-checkpoint/1", "pins": repair.checkpoint_pins(source), "assets": {}}
            checkpoint["pins"]["schemaByteSha256"] = "changed"
            (output / "checkpoint.json").write_text(json.dumps(checkpoint))
            with self.assertRaisesRegex(ValueError, "pins changed"):
                repair.repair(source, output, workers=1, resume=True)

    def test_corrupt_unjournaled_output_is_held_not_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_fixture(root)
            output = root / "recovery"
            (output / "packets").mkdir(parents=True)
            checkpoint = {"schemaVersion": "offmenu-bulk-repair-checkpoint/1", "pins": repair.checkpoint_pins(source), "assets": {}}
            (output / "checkpoint.json").write_text(json.dumps(checkpoint))
            held = output / "packets/part-00000.jsonl.gz"
            held.write_bytes(b"truncated gzip evidence")
            with self.assertRaises(OSError):
                repair.repair(source, output, workers=1, resume=True)
            self.assertEqual(held.read_bytes(), b"truncated gzip evidence")
            self.assertFalse((output / "manifest.json").exists())

    def test_existing_writer_lock_blocks_without_reclaiming_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_fixture(root)
            output = root / "recovery"
            lock = root / "recovery.repair.lock"
            lock.write_text('retained existing owner evidence')
            with self.assertRaisesRegex(ValueError, "writer lock exists"):
                repair.repair(source, output, workers=1)
            self.assertEqual(lock.read_text(), 'retained existing owner evidence')
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
