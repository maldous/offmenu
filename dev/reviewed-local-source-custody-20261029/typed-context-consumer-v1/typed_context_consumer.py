"""Pinned, offline reader -> frozen typed adapter; candidate context only."""
import argparse
import builtins
import contextlib
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
from types import ModuleType

DEFAULT_BASE = Path("/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1")
SOURCE_PIN = "8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e"
BULK_PIN = "83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694"
BASIS_PIN = "3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9"
CONTRACT_PIN = "b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa"
SCHEMA_PIN = "89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c"
CONTRACT_CANONICAL_PIN = "3c3397af8c735cf19eef98f88ddd4da9ce23602c46ec97b4c67561fa15fc3bf1"
INDEX_PIN = "5e6d5c14a26515632a56aac2ff128a12baaa6ec7d030703c368cc8c297a4c1ad"
PROOF_PIN = "1691828696477efe932d6b3bfc1e20cbdc99ddf047da3e695067f40478e8c2cd"
NATIVE_PIN = "312a7f5ce7c32b81d1eb02251303a000073eea2d0b46d9ac710e09ff89dee895"
CODE = {
    "source_scoped_north_star_consumer.py": "75a43f30967c2ea38606e0a1468132629a51b9c79744eed71938a5e1d146b3bc",
    "derive_north_star_bulk.py": "3adc476be2a6694d62c76bb4d539f0fc698810fd3b942dc9ae501e940efde7a1",
    "north_star_derivations.py": "fee258de07319fd19c0032701ea2731afabc1f560eb69c80f111088c65cf0509",
    "north_star_basis_restoration.py": "cae8b86cbacdbf0d81b9a52bb508dadae56e29639cfd332f87fb2b71bd18566a",
    "run_north_star_basis_restoration.py": "24b477296d17675f7eb2ef3c674e5ae153a603afa599743161a13d0e05106d59",
    "typed_nutrient_context.py": "d85a499493f982bec60af67e2588290f56d74b50a0cba03602de083b26a16e8e",
}
SOURCE_PINS = {"sourceManifestByteSha256": SOURCE_PIN,
               "bulkDerivedManifestByteSha256": BULK_PIN,
               "basisDerivedManifestByteSha256": BASIS_PIN}
ONE_KEY_SQL = """SELECT i.source,i.release,i.namespace,i.lexical
FROM identifiers i
WHERE EXISTS(SELECT 1 FROM unique_product_keys k
             WHERE k.subject=i.subject AND k.key_sha=i.key_sha)
AND EXISTS(SELECT 1 FROM resolved_edges e
           WHERE e.subject=i.subject AND e.has_context=1)
ORDER BY i.key_sha,i.subject,i.assertion_id LIMIT 1"""


class BindingError(ValueError):
    """A required reviewed local source/package binding is unavailable or differs."""


def require(ok, message):
    if not ok:
        raise BindingError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def checked_bytes(path, pin, max_bytes=64 * 1024 * 1024):
    # No aliases, symlink traversal or arbitrary import path substitution.
    require(path.is_absolute() and path.resolve(strict=True) == path,
            "exact existing nonsymlink source path required")
    require(path.stat().st_size <= max_bytes, "bounded source metadata required")
    data = path.read_bytes()
    require(len(data) <= max_bytes and hashlib.sha256(data).hexdigest() == pin,
            "reviewed file byte pin differs: " + path.name)
    return data


def json_bytes(data):
    def object_pairs(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, "duplicate JSON metadata key")
            obj[key] = value
        return obj
    def nonfinite(_):
        raise BindingError("nonfinite JSON metadata")
    return json.loads(data, object_pairs_hook=object_pairs, parse_constant=nonfinite)


def paths(base):
    base = Path(base)
    derived = base / "north-star-derived-20261028"
    return {"base": base, "derived": derived, "source": base / "bulk-parallel",
            "bulk": derived / "full-bulk-v1", "basis": derived / "basis-restoration-v1",
            "caller_code": derived / "caller-code-v2", "basis_code": derived / "basis-code-v1",
            "adapter": derived / "typed-context-adapter-v1"}


def verify_inputs(p):
    source = json_bytes(checked_bytes(p["source"] / "manifest.json", SOURCE_PIN))
    bulk = json_bytes(checked_bytes(p["bulk"] / "manifest.json", BULK_PIN))
    basis = json_bytes(checked_bytes(p["basis"] / "manifest.json", BASIS_PIN))
    require(source.get("schemaVersion") == "offmenu-common-bulk-food/1"
            and source.get("complete") is True, "completed normalized source required")
    for package, schema, rules, source_key in (
        (bulk, "offmenu-north-star-full-derivation/1",
         "north-star-structural-derivations/2", "manifestByteSha256"),
        (basis, "offmenu-same-source-basis-restoration/1",
         "north-star-per-nutrient-basis-restoration/1", "normalizedManifestByteSha256"),
    ):
        require(package.get("schemaVersion") == schema and package.get("complete") is True
                and package.get("semanticStatus") == "candidate-not-admitted"
                and package.get("publicationEligible") is False,
                "completed candidate-only derived package required")
        s = package["selection"]
        require(s[source_key] == SOURCE_PIN and s["contractByteSha256"] == CONTRACT_PIN
                and s["schemaByteSha256"] == SCHEMA_PIN and s["rulesetVersion"] == rules,
                "derived source/contract/schema selection differs")
    bulk_code = {k: CODE[k] for k in ("derive_north_star_bulk.py", "north_star_derivations.py")}
    basis_code = {k: CODE[k] for k in ("derive_north_star_bulk.py", "north_star_derivations.py",
                                     "north_star_basis_restoration.py", "run_north_star_basis_restoration.py")}
    require(bulk["selection"]["codePins"] == bulk_code
            and basis["selection"]["codePins"] == basis_code, "derived producer code selection differs")
    require(basis["selection"]["nativeManifestByteSha256"] == NATIVE_PIN
            and basis["selection"]["selectedSources"] == ["off", "usda-files"],
            "basis native selection differs")
    require(bulk["consumerIndex"]["sqliteSha256"] == INDEX_PIN
            and basis["consumerProof"]["sqliteSha256"] == PROOF_PIN, "reader index selection differs")
    for index in (bulk["consumerIndex"], basis["consumerProof"]):
        require(type(index["acceptedIdentityJoins"]) is int and index["acceptedIdentityJoins"] == 0
                and type(index["servedAppQueries"]) is int and index["servedAppQueries"] == 0,
                "index admission boundary differs")
    entries = {}
    for entry in source["files"]:
        require(entry["key"] not in entries, "duplicate source manifest asset key")
        entries[entry["key"]] = entry
    values = {}
    for key, pin in (("contract.json", CONTRACT_PIN), ("schema.json", SCHEMA_PIN)):
        entry = entries.get(key)
        require(entry is not None and entry["sha256"] == pin, "manifest-listed contract/schema required")
        data = checked_bytes(p["source"] / key, pin)
        require(type(entry["bytes"]) is int and len(data) == entry["bytes"],
                "manifest-listed metadata size differs")
        values[key] = json_bytes(data)
    contract_pin = digest(values["contract.json"])
    require(contract_pin == CONTRACT_CANONICAL_PIN, "reviewed canonical contract differs")
    return contract_pin


def exec_verified(name, path, pin, bindings):
    """Compile the verified bytes; bind local imports to verified module objects.

    This is trusted pinned source loading, not a sandbox for untrusted code.
    Restore the retained producer's module-level sys.path insertion afterwards.
    No global sys.modules entries are replaced.
    """
    data = checked_bytes(path, pin, max_bytes=2 * 1024 * 1024)
    module = ModuleType(name); module.__file__ = str(path)
    original_import = builtins.__import__
    def verified_import(import_name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and import_name in bindings:
            return bindings[import_name]
        return original_import(import_name, globals, locals, fromlist, level)
    module.__dict__["__builtins__"] = dict(vars(builtins), __import__=verified_import)
    original_path = sys.path[:]
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    finally:
        sys.path[:] = original_path
    return module


def load_runtime(p):
    local = {}
    for name in ("north_star_derivations", "derive_north_star_bulk", "source_scoped_north_star_consumer"):
        local[name] = exec_verified(name, p["caller_code"] / (name + ".py"), CODE[name + ".py"], local)
    # These are selected producer prerequisites, not re-executed derivations.
    for name in ("north_star_derivations.py", "north_star_basis_restoration.py",
                 "run_north_star_basis_restoration.py", "derive_north_star_bulk.py"):
        checked_bytes(p["basis_code"] / name, CODE[name], max_bytes=2 * 1024 * 1024)
    adapter = exec_verified("typed_nutrient_context", p["adapter"] / "typed_nutrient_context.py",
                            CODE["typed_nutrient_context.py"], {})
    return local["source_scoped_north_star_consumer"].SourceScopedConsumer, adapter


class TypedContextConsumer:
    """Lazy, closable qualified offline entrypoint for one selected package set."""
    def __init__(self, base=DEFAULT_BASE):
        self.paths = paths(base)
        self.reader = None
        self.adapter = None
        self.contract_pin = None
        self._locks = None

    def _prepare(self):
        if self.reader is None:
            locks = contextlib.ExitStack()
            try:
                for key in ("bulk", "basis"):
                    lock = locks.enter_context((self.paths[key] / ".writer.lock").open("rb"))
                    fcntl.flock(lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                contract_pin = verify_inputs(self.paths)
                reader_class, adapter = load_runtime(self.paths)
                reader = reader_class(self.paths["source"], self.paths["bulk"], self.paths["basis"],
                                      BULK_PIN, BASIS_PIN)
            except BaseException:
                locks.close()
                raise
            self.contract_pin, self.adapter, self.reader = contract_pin, adapter, reader
            self._locks = locks

    def lookup(self, source_id, release, namespace, lexical_value, *, include_candidates=False):
        if include_candidates is not True:
            return {"schemaVersion": "offmenu-typed-context-consumer/1",
                    "status": "candidate-opt-in-required", "records": [],
                    "acceptedIdentityJoins": 0, "publicationEligible": False,
                    "automaticPlanningEligible": False, "nutritionAggregationEligible": False,
                    "servedApplicationActivation": False}
        require(all(isinstance(v, str) and v for v in (source_id, release, namespace, lexical_value)),
                "explicit source/release/namespace/lexical key required")
        self._prepare()
        result = self.reader.lookup(source_id, release, namespace, lexical_value, include_candidates=True)
        typed = self.adapter.adapt(
            result, include_candidates=True, expected_source_pins=dict(SOURCE_PINS),
            upstream_code_pins={k: CODE[k] for k in self.adapter.CODE_PINS},
            expected_contract_canonical_sha256=self.contract_pin)
        typed["upstreamReader"] = {
            "method": "SourceScopedConsumer.lookup", "verification": "pinned-existing-local-reader",
            "codePins": dict(CODE), "sourcePins": dict(SOURCE_PINS),
            "consumerIndexSha256": INDEX_PIN, "basisConsumerProofSha256": PROOF_PIN,
            "contractByteSha256": CONTRACT_PIN, "schemaByteSha256": SCHEMA_PIN,
            "contractCanonicalSha256": self.contract_pin,
            "scope": "selected-source-key-only-not-fresh-full-corpus-proof",
        }
        return typed

    def close(self):
        if self.reader is not None:
            try:
                self.reader.close()
            finally:
                self.reader = None
                self._locks.close()
                self._locks = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def exercise_one(consumer, max_seconds=600):
    """One index-selected key; return only non-row aggregate evidence."""
    require(type(max_seconds) is int and 1 <= max_seconds <= 600, "bounded exercise deadline required")
    started = time.monotonic(); deadline = started + max_seconds
    consumer._prepare()
    require(time.monotonic() < deadline, "reader verification exceeded exercise deadline")
    try:
        for db in (consumer.reader.index, consumer.reader.locations):
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
        key = consumer.reader.index.execute(ONE_KEY_SQL).fetchone()
        require(time.monotonic() < deadline, "key selection exceeded exercise deadline")
        if key is None:
            return {"schemaVersion": "offmenu-typed-context-integration-proof/1",
                    "status": "no-connected-source-key-available", "sourceKeyQueries": 0,
                    "sourcePins": dict(SOURCE_PINS), "codePins": dict(CODE),
                    "automaticPlanningEligible": False, "nutritionAggregationEligible": False,
                    "servedApplicationActivation": False, "publicationEligible": False,
                    "acceptedIdentityJoins": 0}
        output = consumer.lookup(*key, include_candidates=True)
        require(time.monotonic() < deadline, "selected-key read exceeded exercise deadline")
        require(output["callerStatus"] == "source-scoped-candidate-context" and output["records"],
                "index-selected connected key did not return typed records")
        records = output["records"]
        return {
            "schemaVersion": "offmenu-typed-context-integration-proof/1",
            "status": "one-connected-source-key-typed-offline",
            "sourceKeyQueries": 1, "typedRecordCount": len(records),
            "unknownQuantityCount": sum(r["quantity"]["original"]["value"] is None for r in records),
            "zeroQuantityCount": sum(r["quantity"]["original"]["value"] == 0 for r in records),
            "ownBasisCount": sum(r["provenance"]["basisMatch"] is not None for r in records),
            "unknownPreparationCount": sum(r["preparation"]["status"] == "unknown" for r in records),
            "missingPreparationCount": sum(r["preparation"]["status"] == "not-supplied" for r in records),
            "outputCanonicalSha256": digest(output),
            "sourcePins": dict(SOURCE_PINS), "codePins": dict(CODE),
            "consumerIndexSha256": INDEX_PIN, "basisConsumerProofSha256": PROOF_PIN,
            "contractByteSha256": CONTRACT_PIN, "schemaByteSha256": SCHEMA_PIN,
            "contractCanonicalSha256": consumer.contract_pin,
            "candidateOptIn": True, "acceptedIdentityJoins": 0, "publicationEligible": False,
            "automaticPlanningEligible": False, "nutritionAggregationEligible": False,
            "servedApplicationActivation": False,
            "confidence": {"status": "not-calibrated", "probability": None},
            "rawRecordValuesExported": False, "lexicalIdentifiersExported": False,
            "elapsedSeconds": round(time.monotonic() - started, 6),
        }
    finally:
        for db in (consumer.reader.index, consumer.reader.locations):
            db.set_progress_handler(None, 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="One bounded offline typed-context integration proof")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--proof-root", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=600)
    args = parser.parse_args(argv)
    p = paths(args.base); root = args.proof_root
    require(root.is_absolute() and root.parent == p["derived"]
            and root.name.startswith("typed-context-proof-v1-"),
            "fresh disjoint proof root under selected derived root required")
    require(root.parent.resolve(strict=True) == root.parent and not root.exists(),
            "existing proof root or aliased output parent forbidden")
    # Execution/admission authority remains the existing confined job supervisor.
    # This command does not acquire admission, launch another job, or alter it.
    with TypedContextConsumer(args.base) as consumer:
        result = exercise_one(consumer, args.max_seconds)
    root.mkdir(mode=0o700)
    with (root / "integration-proof.json").open("x", encoding="utf-8") as handle:
        handle.write(canonical(result).decode("utf-8") + "\n")
    print(canonical(result).decode("utf-8"))
    return result


if __name__ == "__main__":
    main()
