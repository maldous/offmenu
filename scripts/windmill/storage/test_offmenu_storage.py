"""Synthetic-only tests; no network, credentials, production data or host state."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from offmenu_storage import Store, StorageError, canonical, digest, main, read_json


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="offmenu-storage-test-")
        self.base = Path(self.tmp.name)
        self.store = Store(self.base / "data" / ".offmenu-platform")
        self.input = self.base / "synthetic.csv"
        self.input.write_bytes(b"id,value\n1,synthetic\n")
        self.key = "synthetic-run/partition-01"
        self.record = {"run_id": "synthetic-run", "partition": "partition-01",
                       "status": "completed", "cursor": 1, "counts": {"processed": 1}}

    def tearDown(self):
        self.tmp.cleanup()

    def seeded(self):
        receipt = self.store.publish(self.input, "synthetic/example.csv")
        saved = self.store.checkpoint(self.key, self.record, [receipt["receipt_path"]])
        return receipt, saved

    def test_publish_is_content_addressed_idempotent_and_private(self):
        a = self.store.publish(self.input, "synthetic/example.csv")
        b = self.store.publish(self.input, "synthetic/example.csv")
        self.assertEqual(a, b)
        manifest = self.store.verify_artifact(a["receipt_path"])
        self.assertEqual(manifest["sha256"], digest(self.input.read_bytes()))
        self.assertEqual(self.store.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.store.path(a["receipt_path"]).stat().st_mode & 0o777, 0o600)
        self.assertNotIn("source", manifest)

    def test_round_trip_backup_restores_deleted_checkpoint_into_new_version(self):
        receipt, original = self.seeded()
        backup = self.store.backup(self.key)
        shutil.rmtree(self.store.path(self.store._base(self.key)))
        restored = self.store.restore(self.key, backup["backup_path"])
        self.assertNotEqual(original["version"], restored["version"])
        body = self.store.verify(self.key)["body"]
        self.assertEqual(body["record"], self.record)
        self.assertEqual(body["restored_from"], original["version"])
        self.assertEqual(body["artifact_receipts"], [receipt["receipt_path"]])
        self.assertTrue(self.store.path(backup["backup_path"]).exists())

    def test_restore_preserves_later_history(self):
        _, original = self.seeded()
        backup = self.store.backup(self.key)
        newer = self.store.checkpoint(self.key, {**self.record, "cursor": 2})
        self.store.restore(self.key, backup["backup_path"])
        self.assertEqual(self.store.verify(self.key, newer["version"])["body"]["record"]["cursor"], 2)
        self.assertEqual(self.store.verify(self.key)["body"]["record"]["cursor"], 1)

    def test_restore_refuses_tampered_backup_and_keeps_current(self):
        _, original = self.seeded()
        backup = self.store.backup(self.key)
        path = self.store.path(backup["backup_path"])
        value = read_json(path)
        value["body"]["record"]["cursor"] = 9
        path.write_bytes(canonical(value))
        with self.assertRaises(StorageError):
            self.store.restore(self.key, backup["backup_path"])
        self.assertEqual(self.store.verify(self.key)["body"]["version"], original["version"])

    def test_artifact_corruption_blocks_checkpoint_and_restore(self):
        receipt, _ = self.seeded()
        backup = self.store.backup(self.key)
        manifest = self.store.verify_artifact(receipt["receipt_path"])
        self.store.path(manifest["object_path"]).write_bytes(b"corrupted")
        with self.assertRaises(StorageError):
            self.store.checkpoint(self.key, self.record, [receipt["receipt_path"]])
        with self.assertRaises(StorageError):
            self.store.restore(self.key, backup["backup_path"])

    def test_receipt_tampering_is_rejected(self):
        receipt = self.store.publish(self.input, "synthetic/example.csv")
        path = self.store.path(receipt["receipt_path"])
        manifest = read_json(path)
        manifest["name"] = "different.csv"
        path.write_bytes(canonical(manifest))
        with self.assertRaises(StorageError):
            self.store.verify_artifact(receipt["receipt_path"])

    def test_failed_atomic_pointer_swap_keeps_old_current(self):
        _, original = self.seeded()
        with mock.patch("offmenu_storage.os.replace", side_effect=OSError("synthetic interruption")):
            with self.assertRaises(OSError):
                self.store.checkpoint(self.key, {**self.record, "cursor": 2})
        self.assertEqual(self.store.verify(self.key)["body"]["version"], original["version"])

    def test_local_single_writer_lock_and_independent_keys(self):
        with self.store._lock(self.key):
            with self.assertRaises(StorageError):
                self.store.checkpoint(self.key, self.record)
            self.store.checkpoint("synthetic-run/partition-02", self.record)

    def test_path_traversal_and_symlinks_rejected(self):
        for invalid in ("../escape", "/absolute", "a//b", "a/../b", "a\\b", "."):
            with self.subTest(invalid=invalid), self.assertRaises(StorageError):
                self.store.checkpoint(invalid, self.record)
        link = self.base / "linked"
        link.symlink_to(self.input)
        with self.assertRaises(StorageError):
            self.store.publish(link, "synthetic/example.csv")
        root_link = self.base / "root-link"
        root_link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(StorageError):
            Store(root_link / "child")

    def test_symlink_inside_store_rejected(self):
        self.store._mkdir(self.store.root)
        (self.store.root / "artifacts").symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(StorageError):
            self.store.publish(self.input, "synthetic/example.csv")

    def test_root_with_broad_permissions_rejected_without_chmod(self):
        self.store.root.mkdir(parents=True, mode=0o755)
        self.store.root.chmod(0o755)  # Synthetic fixture independent of caller/jail umask.
        with self.assertRaises(StorageError):
            self.store.checkpoint(self.key, self.record)
        self.assertEqual(self.store.root.stat().st_mode & 0o777, 0o755)

    def test_checkpoint_metadata_allowlist_and_limits(self):
        for extra in ({"token": "synthetic-not-a-real-secret"}, {"rows": [1, 2]},
                      {"cursor": "$var:u/admin/example"}, {"cursor": -1},
                      {"counts": {"processed": True}}, {"cursor": "x" * 513}):
            with self.subTest(extra=list(extra)), self.assertRaises(StorageError):
                self.store.checkpoint(self.key, {**self.record, **extra})

    def test_artifact_budget_is_enforced_and_partial_staging_removed(self):
        with self.assertRaises(StorageError):
            self.store.publish(self.input, "synthetic/example.csv", max_bytes=2)
        self.assertEqual(list(self.store.path("artifacts/staging").iterdir()), [])

    def test_restoring_different_key_is_rejected(self):
        self.seeded()
        backup = self.store.backup(self.key)
        with self.assertRaises(StorageError):
            self.store.restore("other-key", backup["backup_path"])

    def test_manifest_location_cannot_read_arbitrary_file(self):
        receipt = self.store.publish(self.input, "synthetic/example.csv")
        manifest = read_json(self.store.path(receipt["receipt_path"]))
        manifest["object_path"] = "../synthetic.csv"
        self.store.path(receipt["receipt_path"]).write_bytes(canonical(manifest))
        with self.assertRaises(StorageError):
            self.store.verify_artifact(receipt["receipt_path"])

    def test_cli_emits_receipts_not_artifact_contents_or_exception_text(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = main(["--root", str(self.store.root), "publish", "--source", str(self.input), "--name", "synthetic.csv"])
        self.assertEqual(result, 0)
        self.assertNotIn("synthetic\n", out.getvalue())
        self.assertNotIn(str(self.input), out.getvalue())
        self.assertIn("sha256", json.loads(out.getvalue()))
        with contextlib.redirect_stderr(err):
            result = main(["--root", str(self.store.root), "verify", "--key", "missing"])
        self.assertEqual(result, 2)
        self.assertNotIn(str(self.store.root), err.getvalue())


if __name__ == "__main__":
    unittest.main()
