"""Wrapper-only synthetic integration tests; never run the accepted adapter suite."""
import contextlib
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
sys.path.insert(0, str(HERE))
import typed_context_consumer as w

# Reuse only the retained synthetic fixture builder, not its test suite.
test_path = HERE.parent / "typed-context-adapter-v1/test_typed_nutrient_context.py"
assert hashlib.sha256(test_path.read_bytes()).hexdigest() == "e1b5aee280344ed7104f31e69295d97cc463238bcaa72eed50bfdd3215e065bc"
spec = importlib.util.spec_from_file_location("retained_adapter_fixture_only", test_path)
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
adapter = sys.modules["typed_nutrient_context"]


class FakeDB:
    def __init__(self, row=None):
        self.row = row
        self.calls = []
        self.handlers = []
    def execute(self, sql):
        self.calls.append(sql)
        return self
    def fetchone(self):
        return self.row
    def set_progress_handler(self, handler, steps):
        self.handlers.append((handler, steps))


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.result, self.options = fixture_module.fixture()
        self.temp = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.p = w.paths(self.base)
        for key in ("bulk", "basis", "source"):
            self.p[key].mkdir(parents=True)
        for key in ("bulk", "basis"):
            (self.p[key] / ".writer.lock").write_bytes(b"")
        result = self.result
        class Reader:
            def __init__(self, *args):
                self.args = args
                self.calls = []
                self.closed = False
                self.index = FakeDB(("synthetic-source", "synthetic-release", "synthetic-namespace", "0000000000000"))
                self.locations = FakeDB()
            def lookup(self, *key, **kwargs):
                self.calls.append((key, kwargs))
                return deepcopy(result)
            def close(self):
                self.closed = True
        self.reader_class = Reader

    @contextlib.contextmanager
    def prepared(self):
        with patch.object(w, "verify_inputs", return_value=self.options["expected_contract_canonical_sha256"]) as verify, \
             patch.object(w, "load_runtime", return_value=(self.reader_class, adapter)) as load, \
             patch.object(w, "SOURCE_PINS", self.options["expected_source_pins"]):
            with w.TypedContextConsumer(self.base) as consumer:
                yield consumer, verify, load

    def test_opt_in_skips_all_package_and_index_reads(self):
        with patch.object(w, "verify_inputs") as verify, patch.object(w, "load_runtime") as load:
            c = w.TypedContextConsumer(self.base)
            for opt in (False, None, 1, "true"):
                out = c.lookup("", "", "", "", include_candidates=opt)
                self.assertEqual(out["status"], "candidate-opt-in-required")
                self.assertEqual(out["records"], [])
            verify.assert_not_called(); load.assert_not_called()

    def test_existing_reader_invoked_then_real_frozen_adapter(self):
        with self.prepared() as (c, verify, load):
            out = c.lookup("s", "r", "n", "0001", include_candidates=True)
            self.assertEqual(len(out["records"]), 4)
            self.assertEqual(c.reader.calls, [(("s", "r", "n", "0001"), {"include_candidates": True})])
            self.assertEqual(c.reader.args[:3], (self.p["source"], self.p["bulk"], self.p["basis"]))
            self.assertEqual(c.reader.args[3:], (w.BULK_PIN, w.BASIS_PIN))
            self.assertEqual(out["upstreamReader"]["contractCanonicalSha256"],
                             self.options["expected_contract_canonical_sha256"])
            c.lookup("s", "r", "n", "0001", include_candidates=True)
            verify.assert_called_once(); load.assert_called_once()
            reader = c.reader
        self.assertTrue(reader.closed)

    def test_missing_and_ambiguous_keys_preserve_status_without_fallback(self):
        for status in ("source-key-not-found", "ambiguous-source-product-key"):
            self.result.update(status=status, products=[])
            with self.prepared() as (c, _, __):
                out = c.lookup("s", "r", "n", "missing", include_candidates=True)
                self.assertEqual(out["callerStatus"], status)
                self.assertEqual(out["records"], [])
                self.assertEqual(len(c.reader.calls), 1)
                self.assertFalse(out["servedApplicationActivation"])

    def test_result_manifest_tampering_not_used_as_expected_bindings(self):
        self.result["sourcePins"]["sourceManifestByteSha256"] = "0" * 64
        with self.prepared() as (c, _, __):
            with self.assertRaises(adapter.EvidenceError):
                c.lookup("s", "r", "n", "key", include_candidates=True)

    def test_invalid_key_does_not_prepare_reader(self):
        with patch.object(w, "verify_inputs") as verify:
            with self.assertRaises(w.BindingError):
                w.TypedContextConsumer(self.base).lookup("", "r", "n", "key", include_candidates=True)
            verify.assert_not_called()

    def test_single_key_exercise_exports_only_aggregates(self):
        with self.prepared() as (c, _, __):
            report = w.exercise_one(c, 60)
            self.assertEqual(report["sourceKeyQueries"], 1)
            self.assertEqual(report["typedRecordCount"], 4)
            self.assertEqual(report["unknownQuantityCount"], 1)
            self.assertEqual(report["zeroQuantityCount"], 1)
            self.assertEqual(len(c.reader.calls), 1)
            self.assertEqual(c.reader.index.calls, [w.ONE_KEY_SQL])
            self.assertEqual(c.reader.index.handlers[-1], (None, 0))
            serialized = w.canonical(report).decode()
            self.assertNotIn("0000000000000", serialized)
            self.assertNotIn("synthetic-profile", serialized)
            self.assertNotIn("synthetic attribution", serialized.lower())
            self.assertNotIn("records", report)
            self.assertEqual(len(report["outputCanonicalSha256"]), 64)

    def test_no_connected_key_returns_no_false_success(self):
        with self.prepared() as (c, _, __):
            c._prepare(); c.reader.index.row = None
            out = w.exercise_one(c, 60)
            self.assertEqual(out["sourceKeyQueries"], 0)
            self.assertEqual(out["status"], "no-connected-source-key-available")
            self.assertEqual(c.reader.calls, [])

    def test_failed_preflight_never_loads_reader_or_keeps_locks(self):
        c = w.TypedContextConsumer(self.base)
        with patch.object(w, "verify_inputs", side_effect=w.BindingError("test refusal")), \
             patch.object(w, "load_runtime") as load:
            with self.assertRaises(w.BindingError):
                c.lookup("s", "r", "n", "key", include_candidates=True)
            load.assert_not_called()
            self.assertIsNone(c.reader)
            self.assertIsNone(c._locks)

    def synthetic_metadata(self, mutate=None):
        contract = {"units": {"g": {"id": "urn:synthetic:unit:g"}}}
        schema = {"title": "synthetic-only-schema"}
        cb = w.canonical(contract) + b"\n"; sb = w.canonical(schema) + b"\n"
        cp = hashlib.sha256(cb).hexdigest(); sp = hashlib.sha256(sb).hexdigest()
        source = {"schemaVersion": "offmenu-common-bulk-food/1", "complete": True,
                  "files": [{"key": "contract.json", "sha256": cp, "bytes": len(cb)},
                            {"key": "schema.json", "sha256": sp, "bytes": len(sb)}]}
        if mutate:
            mutate("source", source)
        source_bytes = w.canonical(source); source_pin = hashlib.sha256(source_bytes).hexdigest()
        common = {"complete": True, "semanticStatus": "candidate-not-admitted", "publicationEligible": False}
        selection = {"contractByteSha256": cp, "schemaByteSha256": sp}
        bulk = dict(common, schemaVersion="offmenu-north-star-full-derivation/1",
                    selection=dict(selection, manifestByteSha256=source_pin,
                                   rulesetVersion="north-star-structural-derivations/2",
                                   codePins={k: w.CODE[k] for k in ("derive_north_star_bulk.py", "north_star_derivations.py")}),
                    consumerIndex={"sqliteSha256": w.INDEX_PIN, "acceptedIdentityJoins": 0, "servedAppQueries": 0})
        basis = dict(common, schemaVersion="offmenu-same-source-basis-restoration/1",
                     selection=dict(selection, normalizedManifestByteSha256=source_pin,
                                    rulesetVersion="north-star-per-nutrient-basis-restoration/1",
                                    nativeManifestByteSha256=w.NATIVE_PIN, selectedSources=["off", "usda-files"],
                                    codePins={k: w.CODE[k] for k in ("derive_north_star_bulk.py", "north_star_derivations.py",
                                                                  "north_star_basis_restoration.py", "run_north_star_basis_restoration.py")}),
                     consumerProof={"sqliteSha256": w.PROOF_PIN, "acceptedIdentityJoins": 0, "servedAppQueries": 0})
        if mutate:
            mutate("bulk", bulk); mutate("basis", basis)
        bb = w.canonical(bulk); nb = w.canonical(basis)
        for p, data in [(self.p["source"] / "manifest.json", source_bytes), (self.p["source"] / "contract.json", cb),
                        (self.p["source"] / "schema.json", sb), (self.p["bulk"] / "manifest.json", bb),
                        (self.p["basis"] / "manifest.json", nb)]:
            p.write_bytes(data)
        return {"SOURCE_PIN": source_pin, "BULK_PIN": hashlib.sha256(bb).hexdigest(),
                "BASIS_PIN": hashlib.sha256(nb).hexdigest(), "CONTRACT_PIN": cp, "SCHEMA_PIN": sp,
                "CONTRACT_CANONICAL_PIN": w.digest(contract)}

    def test_canonical_contract_comes_from_manifest_listed_verified_bytes(self):
        bindings = self.synthetic_metadata()
        with patch.multiple(w, **bindings):
            self.assertEqual(w.verify_inputs(self.p), bindings["CONTRACT_CANONICAL_PIN"])
        self.assertNotEqual(bindings["CONTRACT_CANONICAL_PIN"], bindings["CONTRACT_PIN"])

    def test_contract_schema_selection_missing_duplicate_or_rights_mismatch_rejected(self):
        mutations = [
            lambda kind, d: d["files"].pop() if kind == "source" else None,
            lambda kind, d: d["files"].append(deepcopy(d["files"][0])) if kind == "source" else None,
            lambda kind, d: d["selection"].update(contractByteSha256="0" * 64) if kind == "basis" else None,
            lambda kind, d: d["selection"].update(schemaByteSha256="0" * 64) if kind == "bulk" else None,
            lambda kind, d: d.update(publicationEligible=True) if kind == "bulk" else None,
            lambda kind, d: d.update(complete=False) if kind == "basis" else None,
        ]
        for mutation in mutations:
            bindings = self.synthetic_metadata(mutation)
            with patch.multiple(w, **bindings), self.assertRaises(w.BindingError):
                w.verify_inputs(self.p)

    def test_index_producer_and_native_bindings_checked(self):
        for target in ("index", "producer", "native"):
            def mutate(kind, d):
                if kind == "bulk" and target == "index":
                    d["consumerIndex"]["sqliteSha256"] = "0" * 64
                if kind == "basis" and target == "producer":
                    d["selection"]["codePins"]["north_star_basis_restoration.py"] = "0" * 64
                if kind == "basis" and target == "native":
                    d["selection"]["nativeManifestByteSha256"] = "0" * 64
            bindings = self.synthetic_metadata(mutate)
            with patch.multiple(w, **bindings), self.assertRaises(w.BindingError):
                w.verify_inputs(self.p)

    def test_changed_metadata_bytes_or_symlink_rejected(self):
        bindings = self.synthetic_metadata()
        (self.p["source"] / "contract.json").write_bytes(b"changed")
        with patch.multiple(w, **bindings), self.assertRaises(w.BindingError):
            w.verify_inputs(self.p)
        data = self.base / "source-code.py"; data.write_text("value = 1\n")
        link = self.base / "alias.py"; link.symlink_to(data)
        with self.assertRaises(w.BindingError):
            w.checked_bytes(link, hashlib.sha256(data.read_bytes()).hexdigest())

    def test_pinned_loader_rejects_modified_code_before_execution(self):
        p = self.base / "source.py"; p.write_text("raise RuntimeError('must not execute')\n")
        with self.assertRaises(w.BindingError):
            w.exec_verified("synthetic", p, "0" * 64, {})

    def test_actual_source_only_loader_uses_pinned_modules_without_global_replacement(self):
        before_path = sys.path[:]
        before = {k: sys.modules.get(k) for k in ("north_star_derivations", "derive_north_star_bulk",
                                                 "source_scoped_north_star_consumer", "typed_nutrient_context")}
        reader, loaded_adapter = w.load_runtime(w.paths(BASE))
        self.assertEqual(reader.__name__, "SourceScopedConsumer")
        self.assertEqual(loaded_adapter.CODE_PINS, adapter.CODE_PINS)
        self.assertEqual(sys.path, before_path)
        self.assertEqual({k: sys.modules.get(k) for k in before}, before)

    def test_existing_or_outside_proof_root_refused_without_reader(self):
        with patch.object(w, "TypedContextConsumer") as consumer:
            for root in (self.base / "outside", self.p["derived"] / "typed-context-proof-v1-existing"):
                root.mkdir()
                with self.assertRaises(w.BindingError):
                    w.main(["--base", str(self.base), "--proof-root", str(root)])
            consumer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
