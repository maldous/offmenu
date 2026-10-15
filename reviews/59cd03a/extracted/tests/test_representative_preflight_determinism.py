"""Deterministic small reproducer harness for the 2026-10-15 repair-preflight incident.

The latest fatal incident was a native ``Segmentation fault`` inside the C JSON
scanner (``json/decoder.py:353 raw_decode`` <- ``representative_checks`` line 182
``packet = json.loads(line)``) during repair preflight.  Bounded retained
fixtures parse clean in fresh interpreters, so no deterministic data trigger is
proven and the root cause is unproven (working hypothesis: host-level C-runtime
instability).  The pinned implementation is therefore intentionally unchanged;
this module lands the narrowest meaningful evidence instead of an invented fix:

* ``representative_checks`` must produce identical results across fresh
  interpreters (the incident fault was process-local and nondeterministic);
* the real ``verify_input -> representative_checks -> checkpoint`` preflight
  path must complete in a fresh interpreter on a small retained fixture.

A recurrence of a native fault fails these tests loudly (non-zero subprocess
exit / signal) instead of being conflated with a data-format error.
"""
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "repair-bulk-controls-20261014.py"

LOAD_AND_CHECK = (
    "import importlib.util,json,sys;"
    "from pathlib import Path;"
    "s=importlib.util.spec_from_file_location('repair',sys.argv[1]);"
    "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
    "root=Path(sys.argv[2]);"
    "manifest=json.loads((root/'manifest.json').read_text());"
    "print(json.dumps(m.representative_checks(root,manifest),sort_keys=True))"
)

LOAD_AND_REPAIR = (
    "import importlib.util,json,sys;"
    "from pathlib import Path;"
    "s=importlib.util.spec_from_file_location('repair',sys.argv[1]);"
    "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
    "result=m.repair(Path(sys.argv[2]),Path(sys.argv[3]),workers=1);"
    "print(json.dumps(result['repair']['representativePreflight'],sort_keys=True))"
)

FRESH_RUNS = 6
WANTED_SOURCES = ["off", "usda-files", "prices"]


def packet(source_id):
    return {
        "assertions": [{
            "propertyId": "urn:offmenu:property:curatedRecordContext",
            "value": {"fields": {"provenance": {"fields": {"transform": {
                "kind": "text", "id": "urn:removed", "language": "und",
                "value": "offmenu-curation/1", "sourceTextSha256": "x",
                "status": "source-asserted", "citationIds": ["c"],
            }}}}},
        }],
        "resources": [{"id": "r", "names": [{"kind": "text", "value": "unchanged"}]}],
        "relations": [], "citations": [{"sourceId": source_id}],
        "translations": [],
    }


def source_fixture(root):
    """Small retained fixture: a preamble line exercises the full line scan at
    representative_checks line 182 before the wanted source row is reached."""
    source = root / "source"
    (source / "packets").mkdir(parents=True)
    entries = []
    for index, source_id in enumerate(WANTED_SOURCES):
        lines = [json.dumps(packet("fixture-preamble")) + "\n",
                 json.dumps(packet(source_id)) + "\n"]
        data = gzip.compress("".join(lines).encode(), mtime=0)
        key = f"packets/part-{index:05d}.jsonl.gz"
        (source / key).write_bytes(data)
        entries.append({"key": key, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(), "packets": 2})
    manifest = {
        "files": entries, "releaseId": "fixture",
        "counts": {"packets": 6},
        "inputCoverage": {"fixture": {"complete": True, "expectedFiles": 3, "observedFiles": 3}},
    }
    manifest["manifestSha256"] = hashlib.sha256(json.dumps(
        {key: value for key, value in manifest.items() if key != "manifestSha256"},
        ensure_ascii=True, separators=(",", ":")).encode("utf8")).hexdigest()
    (source / "manifest.json").write_text(json.dumps(manifest))
    return source


def run_fresh(code, *arguments):
    return subprocess.run(
        [sys.executable, "-c", code, str(SCRIPT), *(str(item) for item in arguments)],
        capture_output=True, text=True, timeout=120,
    )


class RepresentativePreflightDeterminismTests(unittest.TestCase):
    def in_process_checks(self, source):
        import importlib.util
        spec = importlib.util.spec_from_file_location("repair_in_process", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = json.loads((source / "manifest.json").read_text())
        return module.representative_checks(source, manifest)

    def test_representative_preflight_is_deterministic_across_fresh_interpreters(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = source_fixture(Path(temporary))
            outputs = []
            for _ in range(FRESH_RUNS):
                result = run_fresh(LOAD_AND_CHECK, source)
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(len(set(outputs)), 1, "preflight drifted across fresh interpreters")
            found = json.loads(outputs[0])
            self.assertEqual(sorted(found), sorted(WANTED_SOURCES))
            for source_id, entry in found.items():
                self.assertEqual(entry["control"], {"kind": "text", "value": "offmenu-curation/1"})
                self.assertTrue(entry["packetFile"].startswith("packets/part-"))

    def test_representative_preflight_matches_in_process_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = source_fixture(Path(temporary))
            result = run_fresh(LOAD_AND_CHECK, source)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout),
                             self.in_process_checks(source))

    def test_full_preflight_path_completes_and_is_deterministic_in_fresh_interpreters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = source_fixture(root)
            outputs = []
            for run in range(FRESH_RUNS):
                target = root / f"recovery-{run}"
                result = run_fresh(LOAD_AND_REPAIR, source, target)
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(result.stdout)
                checkpoint = json.loads((target / "checkpoint.json").read_text())
                self.assertTrue(checkpoint["complete"])
                manifest = json.loads((target / "manifest.json").read_text())
                self.assertEqual(
                    sorted(manifest["repair"]["representativePreflight"]),
                    sorted(WANTED_SOURCES))
                self.assertEqual(manifest["repair"]["inputAssetsVerified"], 3)
            self.assertEqual(len(set(outputs)), 1, "preflight result drifted across full runs")


if __name__ == "__main__":
    unittest.main()
