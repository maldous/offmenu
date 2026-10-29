import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "offmenu_projector_inventory.py"
spec = importlib.util.spec_from_file_location("projector_inventory", SCRIPT)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ProjectorInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "source.py"

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self, raw, expected=None):
        self.path.write_bytes(raw)
        return inventory.inspect_file(str(self.path), expected or digest(raw))

    def report(self, raw=b'import json\ndef view():\n return "PRIVATE_BODY"\n'):
        self.path.write_bytes(raw)
        modules = {key: (str(self.path), digest(raw)) for key in inventory.MODULES}
        self.fixture_modules = modules
        with mock.patch.object(inventory, "MODULES", modules):
            return inventory.inventory()

    def sanitize(self, report):
        with mock.patch.object(inventory, "MODULES", self.fixture_modules):
            return inventory.sanitize_report(report)

    def test_six_fixed_modules_and_expected_hashes(self):
        self.assertEqual(len(inventory.MODULES), 6)
        self.assertEqual({Path(path).name for path, _ in inventory.MODULES.values()},
                         {"ledger.py", "backlog.py", "management_actions.py", "followthrough.py", "session_actions.py", "country_management.py"})
        for path, sha in inventory.MODULES.values():
            self.assertTrue(path.startswith('/home/user/Documents/Codex/2026-10-16/worker64-'))
            self.assertRegex(sha, r'^[0-9a-f]{64}$')

    def test_matching_source_static_summary_without_values(self):
        raw = b'import json as local_alias\nfrom pathlib import Path\nclass Ledger:\n def view(self):\n  return "PRIVATE_BODY"\n'
        result = self.inspect(raw)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["structure"]["imports"], ["json", "pathlib"])
        self.assertEqual(result["structure"]["classes"], ["Ledger"])
        self.assertEqual(result["structure"]["functions"], ["view"])
        serialized = json.dumps(result)
        self.assertNotIn("PRIVATE_BODY", serialized)
        self.assertNotIn("local_alias", serialized)
        self.assertNotIn(str(self.root), serialized)

    def test_python_source_is_never_executed(self):
        marker = self.root / "must-not-exist"
        raw = f'from pathlib import Path\nPath({str(marker)!r}).write_text("NO")\nraise RuntimeError("PRIVATE_BODY")\n'.encode()
        self.assertEqual(self.inspect(raw)["status"], "verified")
        self.assertFalse(marker.exists())

    def test_hash_mismatch_skips_ast(self):
        with mock.patch.object(inventory, "syntax_summary", side_effect=AssertionError("AST must not run")):
            result = self.inspect(b'def safe():\n pass\n', "0" * 64)
        self.assertEqual(result["status"], "hash-mismatch")
        self.assertFalse(result["sha256Match"])
        self.assertNotIn("structure", result)

    def test_invalid_syntax_has_no_message_or_line(self):
        result = self.inspect(b'def PRIVATE_CANARY(\n')
        self.assertEqual(result["status"], "syntax-invalid")
        self.assertEqual(result["syntax"], "invalid")
        self.assertTrue(result["sha256Match"])
        self.assertNotIn("PRIVATE_CANARY", json.dumps(result))

    def test_missing_leaf_and_ancestor(self):
        for path in (self.path, self.root / "absent" / "file.py"):
            result = inventory.inspect_file(str(path), "0" * 64)
            self.assertEqual(result["status"], "missing")
            self.assertFalse(result["present"])

    def test_symlink_leaf_and_ancestor_rejected(self):
        self.path.write_text('pass\n')
        leaf = self.root / "link.py"
        leaf.symlink_to(self.path)
        ancestor = self.root / "linked-dir"
        ancestor.symlink_to(self.root, target_is_directory=True)
        for path in (leaf, ancestor / "source.py"):
            result = inventory.inspect_file(str(path), digest(b'pass\n'))
            self.assertEqual(result["status"], "unsafe-path")
            self.assertNotIn("structure", result)

    def test_directory_and_fifo_rejected_without_read(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)
        for path in (self.root, fifo):
            result = inventory.inspect_file(str(path), "0" * 64)
            self.assertEqual(result["status"], "not-regular")

    def test_oversize_rejected_before_read(self):
        self.path.write_bytes(b"x" * (inventory.MAX_FILE_BYTES + 1))
        with mock.patch.object(inventory.os, "read", side_effect=AssertionError("must not read")):
            result = inventory.inspect_file(str(self.path), "0" * 64)
        self.assertEqual(result["status"], "oversize")
        self.assertIsNone(result["sha256"])

    def test_changed_during_read_rejected(self):
        raw = b'def view():\n return 1\n'
        self.path.write_bytes(raw)
        real_read = os.read
        changed = False

        def changing_read(fd, count):
            nonlocal changed
            chunk = real_read(fd, count)
            if not changed:
                changed = True
                with self.path.open('ab') as stream:
                    stream.write(b'# changed\n')
            return chunk

        with mock.patch.object(inventory.os, "read", side_effect=changing_read):
            result = inventory.inspect_file(str(self.path), digest(raw))
        self.assertEqual(result["status"], "changed-during-read")
        self.assertIsNone(result["sha256"])

    def test_replaced_leaf_rejected(self):
        raw = b'pass\n'
        self.path.write_bytes(raw)
        replacement = self.root / "replacement.py"
        replacement.write_bytes(raw)
        real_read = os.read
        changed = False

        def replacing_read(fd, count):
            nonlocal changed
            chunk = real_read(fd, count)
            if not changed:
                changed = True
                os.replace(replacement, self.path)
            return chunk

        with mock.patch.object(inventory.os, "read", side_effect=replacing_read):
            result = inventory.inspect_file(str(self.path), digest(raw))
        self.assertEqual(result["status"], "changed-during-read")

    def test_replaced_ancestor_rejected(self):
        directory = self.root / "source-dir"
        directory.mkdir()
        path = directory / "source.py"
        raw = b'pass\n'
        path.write_bytes(raw)
        real_read = os.read
        changed = False

        def replacing_read(fd, count):
            nonlocal changed
            chunk = real_read(fd, count)
            if not changed:
                changed = True
                directory.rename(self.root / "old-dir")
                directory.mkdir()
                (directory / "source.py").write_bytes(raw)
            return chunk

        with mock.patch.object(inventory.os, "read", side_effect=replacing_read):
            result = inventory.inspect_file(str(path), digest(raw))
        self.assertEqual(result["status"], "changed-during-read")

    def test_read_permission_error_is_static(self):
        self.path.write_text('pass\n')
        with mock.patch.object(inventory.os, "read", side_effect=PermissionError("PRIVATE_PATH")):
            result = inventory.inspect_file(str(self.path), digest(b'pass\n'))
        self.assertEqual(result["status"], "unreadable")
        self.assertNotIn("PRIVATE_PATH", json.dumps(result))

    def test_relative_imports_async_and_bounded_names(self):
        raw = b'from . import backlog\nfrom ..session_actions import view\nasync def run():\n pass\n'
        result = self.inspect(raw)
        self.assertEqual(result["structure"]["imports"], ["backlog", "session_actions"])
        self.assertEqual(result["structure"]["relativeImportStatements"], 2)
        self.assertEqual(result["structure"]["functions"], ["run"])

    def test_secret_identifiers_unicode_and_literals_withheld(self):
        raw = 'import personal_secret_canary\ndef api_key_CANARY(): pass\ndef café(): pass\ndef safe(): return "body-canary"\n'.encode()
        result = self.inspect(raw)
        self.assertEqual(result["structure"]["functions"], ["safe"])
        self.assertEqual(result["structure"]["functionsOmitted"], 2)
        self.assertEqual(result["structure"]["importsOmitted"], 1)
        self.assertNotIn("CANARY", json.dumps(result))
        self.assertNotIn("canary", json.dumps(result))

    def test_summary_counts_omitted_names(self):
        names = sorted(inventory.SAFE_SYMBOLS)
        raw = ''.join(f'def {name}(): pass\n' for name in names).encode()
        result = self.inspect(raw)
        self.assertEqual(len(result["structure"]["functions"]), inventory.MAX_FUNCTIONS)
        self.assertEqual(result["structure"]["functionsOmitted"], len(names) - inventory.MAX_FUNCTIONS)

    def test_report_roundtrip_boundaries_and_size(self):
        report = self.report()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(self.sanitize(report), report)
        self.assertLess(len(inventory.canonical(report)), inventory.MAX_REPORT_BYTES)
        self.assertNotIn(str(self.root), json.dumps(report))
        self.assertNotIn("PRIVATE_BODY", json.dumps(report))

    def test_output_cap_preserves_hashes_and_drops_structure(self):
        names = ''.join(f'def {name}(): pass\n' for name in inventory.SAFE_SYMBOLS).encode()
        with mock.patch.object(inventory, "MAX_REPORT_BYTES", 2500):
            report = self.report(names)
            self.assertTrue(report["summaryTruncated"])
            self.assertLessEqual(len(inventory.canonical(report)), 2500)
            self.assertEqual(self.sanitize(report), report)
        self.assertTrue(all(record["sha256Match"] for record in report["files"].values()))
        self.assertTrue(all("structure" not in record for record in report["files"].values()))

    def test_sanitizer_rejects_unexpected_fields_values_and_false_types(self):
        baseline = self.report()
        first = next(iter(baseline["files"]))
        for transform in (
            lambda x: x.update(rawSource="PRIVATE_BODY"),
            lambda x: x.update(sourceCodeUploaded=0),
            lambda x: x["files"][first].update(path="/private/path"),
            lambda x: x["files"][first]["structure"]["functions"].append("bad-name"),
            lambda x: x["files"][first]["structure"]["functions"].append("secret_canary"),
            lambda x: x["files"][first].update(sha256Match=1),
            lambda x: x["files"][first]["structure"].update(rawBody="PRIVATE_BODY"),
            lambda x: x.update(status="incomplete"),
        ):
            modified = copy.deepcopy(baseline)
            transform(modified)
            with self.assertRaises(ValueError):
                self.sanitize(modified)

    def test_report_hashes_bound_to_each_fixed_module_pin(self):
        report = self.report()
        for record in report["files"].values():
            record["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.sanitize(report)

    def test_credential_shaped_and_unknown_identifiers_not_exported(self):
        raw = b'import ghp_SYNTHETICCANARY012345678901234567890123\ndef github_pat_SYNTHETICCANARY0123456789012345(): pass\ndef ordinary_unknown_function(): pass\n'
        result = self.inspect(raw)
        self.assertEqual(result["structure"]["imports"], [])
        self.assertEqual(result["structure"]["functions"], [])
        self.assertEqual(result["structure"]["functionsOmitted"], 2)
        self.assertNotIn("SYNTHETICCANARY", json.dumps(result))
        self.assertNotIn("ordinary_unknown_function", json.dumps(result))

    def test_unhashed_reports_cannot_assert_valid_syntax(self):
        report = self.report()
        first = next(iter(report["files"]))
        record = report["files"][first]
        record.pop("structure")
        record.update(status="missing", present=False, type="missing", bytes=None,
                      sha256=None, sha256Match=None, syntax="valid")
        report["status"] = "incomplete"
        with self.assertRaises(ValueError):
            self.sanitize(report)
        record["syntax"] = "not-inspected"
        self.assertEqual(self.sanitize(report), report)

    def test_all_hashed_statuses_require_regular_present_bounded_file(self):
        for status, raw, matches, syntax in (("hash-mismatch", b'pass\n', False, "not-inspected"),
                                              ("syntax-invalid", b'def broken(\n', True, "invalid")):
            report = self.report(raw)
            record = report["files"][next(iter(report["files"]))]
            record.pop("structure", None)
            record.update(status=status, sha256Match=matches, syntax=syntax)
            if not matches:
                record["sha256"] = "0" * 64
            report["status"] = "incomplete"
            self.assertEqual(self.sanitize(report), report)
            for key, value in (("present", False), ("type", "missing"), ("bytes", None),
                               ("bytes", inventory.MAX_FILE_BYTES + 1)):
                bad = copy.deepcopy(report)
                bad["files"][next(iter(bad["files"]))][key] = value
                with self.assertRaises(ValueError):
                    self.sanitize(bad)

    def test_source_selected_codec_not_used(self):
        raw = b'# coding: nonexistent_secret_codec\nimport json\ndef view(): pass\n'
        result = self.inspect(raw)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["structure"]["functions"], ["view"])
        self.assertNotIn("nonexistent_secret_codec", json.dumps(result))
        result = self.inspect(b'# coding: latin-1\nx="\xff"\n')
        self.assertEqual(result["status"], "syntax-invalid")

    def test_root_and_arguments_block_before_reads(self):
        for args, uid in (([], 0), (["--source", "/private/path"], 1000)):
            output = io.StringIO()
            with mock.patch.object(inventory.os, "getuid", return_value=uid), mock.patch.object(inventory.os, "geteuid", return_value=uid), mock.patch.object(inventory, "inventory", side_effect=AssertionError("no reads")), contextlib.redirect_stdout(output):
                self.assertEqual(inventory.main(args), 2)
            report = json.loads(output.getvalue())
            self.assertEqual(inventory.sanitize_report(report), report)
            self.assertNotIn("/private/path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
