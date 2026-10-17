import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "offmenu_ledger_audit.py"
spec = importlib.util.spec_from_file_location("ledger_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def stream(raw):
    return audit.audit_stream(io.BytesIO(raw), len(raw), pin(raw))


def write_fixture(root, raw=b'{"sequence":1,"eventId":"private-value","payload":{}}\n'):
    prefix = root / audit.SOURCE_PREFIX
    prefix.mkdir(parents=True)
    pins = {}

    def write(name, value):
        data = value if isinstance(value, bytes) else json.dumps(value).encode() + b"\n"
        path = prefix / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        pins[name] = pin(data)
        return pins[name]["sha256"]

    initial = write("operational-ledger/base-initial-copy.json", {"requirements": []})
    current = write("operational-ledger/interim-obligation-index.json", {"requirements": [1]})
    authority = write("operational-ledger/authority.json", {"initialBase": {"sha256": initial}})
    journal = write("operational-ledger/events.jsonl", raw)
    write("operational-ledger/management-summary.json", {
        "eventCount": raw.count(b"\n"), "sourceSequence": raw.count(b"\n"),
        "sources": {"base": {"sha256": current}, "journal": {"sha256": journal}}})
    write("operational-ledger/handover.json", {
        "eventCount": 5269, "authority": {"sha256": authority}, "base": {"sha256": current},
        "journal": {"sha256": hashlib.sha256(b"".join(raw.splitlines(keepends=True)[:5269])).hexdigest()},
        "managementSummary": {"sha256": "0" * 64}})
    write("morgan-batches-20261017/current-checkpoint.json", {"cut": 5105})
    write("morgan-batches-20261017/transport-checkpoint-current.json", {"primaryAdmissions": 64})
    return pins


class StructuralAuditTests(unittest.TestCase):
    def test_stream_hashes_exact_bytes_without_values(self):
        raw = b'{"sequence":1,"eventId":"DO-NOT-EMIT-SECRET","payload":{"a":true}}\n'
        result = stream(raw)
        self.assertTrue(result["pinsMatch"])
        self.assertEqual(result["sha256"], pin(raw)["sha256"])
        self.assertEqual(result["gitBlob"], pin(raw)["gitBlob"])
        self.assertEqual(result["jsonObjects"], 1)
        self.assertNotIn("DO-NOT-EMIT-SECRET", json.dumps(result))
        self.assertEqual(next(f for f in result["topLevelFields"] if f["name"] == "sequence")["types"], {"integer": 1})

    def test_unknown_schema_does_not_interpret_sequence(self):
        result = stream(b'{"sequence":99}\n{"sequence":2}\n{"sequence":2}\n')
        self.assertEqual(result["jsonObjects"], 3)
        self.assertTrue(result["allJsonValid"])
        self.assertNotIn("sequenceContiguous", result)

    def test_bad_json_is_counted_while_full_hash_is_computed(self):
        raw = b'{"ok":1}\nno raw secret please\n{"ok":2}\n'
        result = stream(raw)
        self.assertFalse(result["allJsonValid"])
        self.assertEqual((result["invalidLines"], result["firstInvalidLine"]), (1, 2))
        self.assertEqual(result["sha256"], pin(raw)["sha256"])
        self.assertEqual(result["physicalLines"], 3)
        self.assertNotIn("secret", json.dumps(result))

    def test_duplicate_keys_rejected_including_nested(self):
        for raw in (b'{"x":1,"x":2}\n', b'{"x":{"y":1,"y":2}}\n'):
            with self.subTest(raw=raw):
                self.assertFalse(stream(raw)["allJsonValid"])

    def test_nonfinite_rejected_including_overflow_and_nested(self):
        for raw in (b'{"x":NaN}\n', b'{"x":Infinity}\n', b'{"x":-Infinity}\n',
                    b'{"x":1e9999}\n', b'{"x":[{"x":NaN}]}\n'):
            with self.subTest(raw=raw):
                self.assertFalse(stream(raw)["allJsonValid"])

    def test_invalid_utf8_and_blank_lines_rejected(self):
        for raw in (b'{"x":"\xff"}\n', b'\n', b' \t\n'):
            self.assertFalse(stream(raw)["allJsonValid"])

    def test_valid_nonobjects_do_not_pass_object_schema(self):
        result = stream(b'[]\nnull\ntrue\n42\n"x"\n')
        self.assertTrue(result["allJsonValid"])
        self.assertFalse(result["objectOnly"])
        self.assertEqual(result["nonObjectLines"], 5)

    def test_missing_final_newline_is_reported(self):
        result = stream(b'{"x":1}')
        self.assertTrue(result["allJsonValid"])
        self.assertFalse(result["allRecordsNewlineTerminated"])

    def test_field_types_complete_and_names_bounded(self):
        records = [{"sequence": x} for x in (None, True, 1, 1.0, "s", [], {})]
        records.append({f"key{i}": "hidden" for i in range(100)})
        records.append({"bad\nfield": "hidden", "x" * 65: "hidden"})
        result = stream(b"".join(json.dumps(x).encode() + b"\n" for x in records))
        self.assertEqual(set(result["topLevelFields"][0]["types"]), audit.TYPE_NAMES)
        self.assertEqual(len(result["topLevelFields"]), 1)
        self.assertEqual(result["omittedFieldOccurrences"], 102)
        self.assertNotIn("hidden", json.dumps(result))

    def test_oversized_line_drained_and_hash_preserved(self):
        raw = b'{"value":"' + b"x" * (audit.MAX_LINE_BYTES + 100) + b'"}\n{}\n'
        result = stream(raw)
        self.assertEqual(result["physicalLines"], 2)
        self.assertEqual(result["invalidLines"], 1)
        self.assertEqual(result["jsonObjects"], 1)
        self.assertTrue(result["pinsMatch"])

    def test_growing_oversized_line_stops_at_byte_cap(self):
        class GrowingStream:
            def __init__(self):
                self.calls = 0

            def readline(self, limit):
                self.calls += 1
                if self.calls > 4:
                    raise AssertionError("Read beyond source byte cap")
                return b"x" * limit

        growing = GrowingStream()
        with mock.patch.object(audit, "MAX_LINE_BYTES", 10), mock.patch.object(audit, "MAX_SOURCE_BYTES", 30):
            with self.assertRaisesRegex(audit.AuditError, "source-file-invalid"):
                audit.audit_stream(growing, 1, pin(b"x"))
        self.assertEqual(growing.calls, 3)

    def test_secret_like_ascii_keys_never_exported(self):
        raw = b'{"secretkey_ABC123XYZ":"x","sequence":1}\n'
        result = stream(raw)
        self.assertEqual(result["omittedFieldOccurrences"], 1)
        self.assertNotIn("secretkey", json.dumps(result))

    def test_field_cap_applies_even_if_allowlist_expands(self):
        names = {"field" + str(i) for i in range(100)}
        with mock.patch.object(audit, "SAFE_FIELD_NAMES", names):
            result = stream(json.dumps(dict.fromkeys(sorted(names), None)).encode() + b"\n")
        self.assertEqual(len(result["topLevelFields"]), audit.MAX_FIELDS)
        self.assertEqual(result["omittedFieldOccurrences"], 100 - audit.MAX_FIELDS)

    def test_full_size_stream_and_historical_prefix(self):
        rows = [json.dumps({"sequence": i + 1, "payload": "x" * 1800}).encode() + b"\n" for i in range(5271)]
        raw = b"".join(rows)
        self.assertGreater(len(raw), 9_000_000)
        result = stream(raw)
        self.assertEqual(result["physicalLines"], 5271)
        self.assertEqual(result["prefix5269Sha256"], hashlib.sha256(b"".join(rows[:5269])).hexdigest())
        self.assertTrue(result["pinsMatch"])

    def test_journal_pin_mismatch(self):
        result = audit.audit_stream(io.BytesIO(b'{}\n'), 3, pin(b'{"x":1}\n'))
        self.assertFalse(result["pinsMatch"])

    def test_summary_lineage_and_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = b'{}\n' * 5271
            report = audit.build_report(root, write_fixture(root, raw))
        self.assertEqual(audit.sanitize_report(report), report)
        self.assertEqual(report["status"], "complete")
        self.assertTrue(report["lineage"]["handoverJournalPrefixMatches"])
        self.assertTrue(report["lineage"]["summaryEventCountMatchesPhysicalLines"])
        self.assertFalse(report["lineage"]["handoverSummaryHashMatchesCurrentSummary"])
        self.assertEqual(report["lineage"]["transportCheckpointCut"], 5105)
        self.assertTrue(all(value is False for value in report["boundaries"].values()))

    def test_changed_companion_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pins = write_fixture(root)
            (root / audit.SOURCE_PREFIX / "operational-ledger/authority.json").write_text('{}\n')
            with self.assertRaisesRegex(audit.AuditError, "source-pin-mismatch"):
                audit.build_report(root, pins)

    def test_leaf_and_parent_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.write_text('{}\n')
            (root / "link").symlink_to(target)
            (root / "dirlink").symlink_to(root, target_is_directory=True)
            for relative in (Path("link"), Path("dirlink/target"), Path("../target")):
                with self.assertRaises(audit.AuditError):
                    audit.open_source(root, relative)

    def test_fifo_is_rejected_without_blocking(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            os.mkfifo(root / "pipe")
            with self.assertRaises(audit.AuditError):
                audit.open_source(root, Path("pipe"))

    def test_source_commit_is_fixed_and_git_environment_sanitized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            with mock.patch.object(audit.subprocess, "check_output", return_value=b"0" * 40 + b"\n") as call:
                with self.assertRaisesRegex(audit.AuditError, "source-revision-mismatch"):
                    audit.verify_source_checkout(root)
            self.assertNotIn("GITHUB_TOKEN", call.call_args.kwargs["env"])
            self.assertEqual(call.call_args.kwargs["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
            with mock.patch.object(audit.subprocess, "check_output", return_value=audit.SOURCE_COMMIT.encode() + b"\n"):
                audit.verify_source_checkout(root)

    def test_report_rejects_raw_values_and_extra_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = audit.build_report(root, write_fixture(root))
        for transform in (
            lambda x: x.update(rawEvent="SECRET"),
            lambda x: x["journal"].update(rawEvent="SECRET"),
            lambda x: x["journal"]["topLevelFields"].append({"name": "ok", "types": {"SECRET": 1}}),
            lambda x: x["journal"]["topLevelFields"].append({"name": "bad\nSECRET", "types": {"string": 1}}),
            lambda x: x["boundaries"].update(semanticProjectionAvailable=True),
            lambda x: x["boundaries"].update(semanticProjectionAvailable=0),
            lambda x: x.update(sourceCommit="0" * 40),
        ):
            modified = copy.deepcopy(baseline)
            transform(modified)
            with self.assertRaises(audit.AuditError):
                audit.sanitize_report(modified)

    def test_report_limit(self):
        with self.assertRaisesRegex(audit.AuditError, "report-limit-exceeded"):
            audit.sanitize_report({"value": "x" * audit.MAX_REPORT_BYTES})

    def test_cli_has_no_source_override_or_raw_error(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = audit.main(["--source", "/private/value"])
        self.assertEqual(result, 1)
        value = json.loads(output.getvalue())
        self.assertEqual(audit.sanitize_report(value), value)
        self.assertNotIn("/private/value", output.getvalue())
        self.assertLess(len(output.getvalue()), audit.MAX_REPORT_BYTES)


if __name__ == "__main__":
    unittest.main()
