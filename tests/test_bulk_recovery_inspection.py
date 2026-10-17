import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/verify-bulk-repair-checkpoint.py"
SPEC = importlib.util.spec_from_file_location("recovery_inspection", SCRIPT)
inspection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspection)


class RecoveryInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.retained = self.root / "retained"
        (self.source / "packets").mkdir(parents=True)
        (self.retained / "packets").mkdir(parents=True)
        self.key = "packets/part-00000.jsonl.gz"
        self.packet = {"resources": [{"id": "urn:r", "quantity": 300}], "assertions": [{"propertyId": "urn:offmenu:property:curatedRecordContext", "value": {"fields": {"provenance": {"fields": {"transform": {"kind": "text", "id": "urn:text", "value": "offmenu-curation/1"}}}}}}]}
        data = gzip.compress((json.dumps(self.packet) + "\n").encode(), mtime=0)
        (self.source / self.key).write_bytes(data)
        entry = {"key": self.key, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "packets": 1}
        manifest = {"files": [entry]}
        manifest["manifestSha256"] = inspection.REPAIR.manifest_payload_digest(manifest)
        (self.source / "manifest.json").write_text(json.dumps(manifest))
        self.repaired, _ = inspection.REPAIR.repair_packet(self.packet)
        (self.retained / self.key).write_bytes(gzip.compress((json.dumps(self.repaired) + "\n").encode(), mtime=0))

    def run_inspection(self):
        return inspection.inspect(self.source, self.retained, [self.key], 1)

    def test_exact_source_comparison_is_bounded_and_does_not_mutate(self):
        before = (self.retained / self.key).read_bytes()
        result = self.run_inspection()
        self.assertEqual(result["usableAssets"], 1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["assets"][0]["verifiedPackets"], 1)
        self.assertEqual(before, (self.retained / self.key).read_bytes())

    def test_corrupted_completed_gzip_is_held(self):
        path = self.retained / self.key
        path.write_bytes(path.read_bytes()[:-8])
        result = self.run_inspection()
        self.assertEqual(result["usableAssets"], 0)
        self.assertEqual(result["assets"][0]["status"], "held-not-reusable")

    def test_source_fact_drift_is_held(self):
        self.repaired["resources"][0]["quantity"] = 301
        (self.retained / self.key).write_bytes(gzip.compress((json.dumps(self.repaired) + "\n").encode()))
        result = self.run_inspection()
        self.assertEqual(result["assets"][0]["status"], "held-not-reusable")

    def test_original_checksum_failure_blocks_inspection(self):
        (self.source / self.key).write_bytes(b"changed original")
        with self.assertRaisesRegex(ValueError, "original asset checksum"):
            self.run_inspection()

    def test_unknown_duplicate_and_escaping_selectors_fail(self):
        for keys in [["unlisted"], [self.key, self.key]]:
            with self.assertRaises(ValueError):
                inspection.inspect(self.source, self.retained, keys, 2)
        with self.assertRaisesRegex(ValueError, "unsafe asset"):
            inspection.safe_path(self.source, "../outside")
