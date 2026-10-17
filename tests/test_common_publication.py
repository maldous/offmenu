import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "common_publication", ROOT / "scripts" / "publish-common-data.py"
)
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


def payload_digest(manifest):
    payload = {key: value for key, value in manifest.items() if key != "manifestSha256"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def manifest_bytes(manifest, *, indent=None):
    return (
        json.dumps(manifest, ensure_ascii=False, indent=indent)
        + "\n"
    ).encode("utf-8")


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*") if path.is_file()
    }


class CommonPublicationTests(unittest.TestCase):
    def write_checksum_manifest(self, path, release, label, value, *, indent=None):
        manifest = {"releaseId": release, "label": label, "numeric": value}
        manifest["manifestSha256"] = payload_digest(manifest)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = manifest_bytes(manifest, indent=indent)
        path.write_bytes(content)
        return manifest, content

    def test_checksum_receipt_preserves_exact_and_legacy_payload_digests_for_retained_releases(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            current, current_bytes = self.write_checksum_manifest(
                target / "common-data" / "manifest.json", "current", "餡", 1.0, indent=2
            )
            current_release, current_release_bytes = self.write_checksum_manifest(
                target / "common-data" / "releases" / "current" / "manifest.json",
                "current", "餡", 1.0, indent=None,
            )
            retained, retained_bytes = self.write_checksum_manifest(
                target / "common-data" / "releases" / "retained" / "manifest.json",
                "retained", "旧", 1.0, indent=4,
            )

            receipt = publication.write_manifest_checksums(target)
            files = {entry["key"]: entry for entry in receipt["files"]}
            expected = {
                "common-data/manifest.json": (current, current_bytes),
                "common-data/releases/current/manifest.json": (current_release, current_release_bytes),
                "common-data/releases/retained/manifest.json": (retained, retained_bytes),
            }
            self.assertEqual(set(files), set(expected))
            for key, (manifest, exact_bytes) in expected.items():
                self.assertEqual(files[key]["byteSha256"], hashlib.sha256(exact_bytes).hexdigest())
                self.assertEqual(files[key]["payloadSha256"], manifest["manifestSha256"])
                self.assertNotEqual(files[key]["byteSha256"], files[key]["payloadSha256"])
                self.assertEqual(
                    (target / f"{key}.sha256").read_text(encoding="utf-8"),
                    f"{files[key]['byteSha256']}  manifest.json\n",
                )
            self.assertIn("ensure_ascii=True", receipt["manifestSha256Definition"])
            self.assertIn("exact UTF-8 file bytes", receipt["byteSha256Definition"])

    def test_checksum_writer_rejects_malformed_legacy_payload_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for path in [
                target / "common-data" / "manifest.json",
                target / "common-data" / "releases" / "current" / "manifest.json",
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"releaseId": "current", "numeric": 1.0, "manifestSha256": "0" * 64}),
                    encoding="utf-8",
                )
            with self.assertRaises(AssertionError):
                publication.write_manifest_checksums(target)

    def expanded_package(self, root, *, proof_present=True, proof_digest_correct=True):
        package = root / "package"
        package.mkdir()
        schema = package / "schema.json"
        contract = package / "contract.json"
        mappings = package / "source-mappings.json"
        schema.write_text("{}", encoding="utf-8")
        contract.write_text("{}", encoding="utf-8")
        mappings.write_text(json.dumps({"sources": []}), encoding="utf-8")
        counts = {"packets": 0, "resources": 0, "assertions": 0, "relations": 0, "translations": 0}
        proof = {
            "schemaVersion": "offmenu-common-expansion-qualification/1",
            "status": "all-packages-streamed-global-identities-references-and-provenance-checked",
            "packageCount": 0, "packages": [], "aggregateObservedCounts": counts,
            "schemaByteSha256": hashlib.sha256(schema.read_bytes()).hexdigest(),
            "contractByteSha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        }
        proof_path = package / "proof.json"
        if proof_present:
            proof_path.write_text(json.dumps(proof), encoding="utf-8")
        proof_sha = hashlib.sha256(proof_path.read_bytes()).hexdigest() if proof_present else "f" * 64
        if not proof_digest_correct:
            proof_sha = "e" * 64
        manifest = {
            "status": "all-source-packages-qualified-and-file-digests-checked",
            "complete": True, "releaseId": "fixture-release", "recipeRecords": 0,
            "recipeLibraryRecords": 0, "globalQualification": "proof.json",
            "files": [{"key": "proof.json", "bytes": proof_path.stat().st_size if proof_present else 0,
                       "sha256": proof_sha}],
            "sourcePackages": [], "counts": counts, "schema": "schema.json",
            "contract": "contract.json", "sourceMappings": "source-mappings.json",
            "sourceGraphCoverage": {}, "sourceCount": 0, "sourceRecordTotal": 0,
        }
        manifest["manifestSha256"] = hashlib.sha256(
            json.dumps({key: value for key, value in manifest.items() if key != "manifestSha256"},
                       separators=(",", ":")).encode()
        ).hexdigest()
        (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return package

    def target(self, root):
        target = root / "target"
        (target / "common-data").mkdir(parents=True)
        (target / "recipes").mkdir()
        root_manifest = {"releaseId": "base"}
        root_manifest["manifestSha256"] = hashlib.sha256(
            json.dumps(root_manifest, separators=(",", ":")).encode()
        ).hexdigest()
        recipes = {"records": 0, "library": {}}
        recipes["manifestSha256"] = hashlib.sha256(
            json.dumps(recipes, separators=(",", ":")).encode()
        ).hexdigest()
        (target / "manifest.json").write_text(json.dumps(root_manifest), encoding="utf-8")
        (target / "recipes" / "manifest.json").write_text(json.dumps(recipes), encoding="utf-8")
        (target / "index.html").write_text("<main>fixture</main>", encoding="utf-8")
        return target

    def assert_rejected_before_target_mutation(self, *, proof_present, proof_digest_correct):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = self.expanded_package(root, proof_present=proof_present,
                                            proof_digest_correct=proof_digest_correct)
            target = self.target(root)
            before = snapshot(target)
            with self.assertRaises((AssertionError, FileNotFoundError)):
                publication.publish(package, target)
            self.assertEqual(snapshot(target), before)

    def test_expanded_publish_rejects_missing_global_proof_before_mutating_target(self):
        self.assert_rejected_before_target_mutation(proof_present=False, proof_digest_correct=True)

    def test_expanded_publish_rejects_bad_global_proof_digest_before_mutating_target(self):
        self.assert_rejected_before_target_mutation(proof_present=True, proof_digest_correct=False)

    def test_expanded_publish_rejects_invalid_global_proof_before_mutating_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = self.expanded_package(root)
            proof_path = package / "proof.json"
            proof_path.write_text(json.dumps({"schemaVersion": "wrong", "status": "wrong"}), encoding="utf-8")
            manifest_path = package / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["bytes"] = proof_path.stat().st_size
            manifest["files"][0]["sha256"] = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            manifest["manifestSha256"] = hashlib.sha256(
                json.dumps({key: value for key, value in manifest.items() if key != "manifestSha256"},
                           separators=(",", ":")).encode()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            target = self.target(root)
            before = snapshot(target)
            with self.assertRaises(AssertionError):
                publication.publish(package, target)
            self.assertEqual(snapshot(target), before)


if __name__ == "__main__":
    unittest.main()
