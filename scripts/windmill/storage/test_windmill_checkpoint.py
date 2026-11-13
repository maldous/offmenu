"""No live SDK calls. Test the Windmill-side contract with synthetic receipts."""
import copy
import unittest
from unittest.mock import patch

from windmill_checkpoint import (CheckpointError, commit_reference, inspect_reference,
                                 resource_path)


class Response:
    def __init__(self, code, payload=None):
        self.status_code = code
        self.payload = payload

    def json(self):
        return copy.deepcopy(self.payload)


class FakeClient:
    def __init__(self):
        self.resources = {}
        self.posts = []
        self.read_status = None
        self.write_status = None

    def get(self, endpoint, raise_for_status=False):
        if self.read_status:
            return Response(self.read_status)
        path = endpoint.split("/resources/get/")[1]
        return Response(200, self.resources[path]) if path in self.resources else Response(404)

    def post(self, endpoint, raise_for_status=False, json=None):
        self.posts.append((endpoint, copy.deepcopy(json)))
        if self.write_status:
            return Response(self.write_status)
        if endpoint.endswith("/create"):
            path = json["path"]
            if path in self.resources:
                return Response(400)
            self.resources[path] = {**json, "workspace_id": "offmenu",
                                    "created_by": "admin", "extra_perms": {}}
            return Response(201)
        path = endpoint.split("/update_value/")[1]
        self.resources[path]["value"] = json["value"]
        return Response(200)


class WindmillCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.key = "synthetic-run/partition-01"
        self.path = resource_path(self.key)
        keyhash = self.path.rsplit("/", 1)[1]
        version = "123456-0123456789abcdef"
        self.cp = {"key": self.key, "version": version, "sha256": "a" * 64,
                   "checkpoint_path": f"checkpoints/{keyhash}/versions/{version}.json",
                   "artifact_count": 1}
        self.backup = {"version": version, "sha256": "a" * 64,
                       "backup_path": f"backups/checkpoints/{keyhash}/{version}.json"}

    def commit(self):
        return commit_reference(self.key, self.cp, self.backup, self.client)

    def test_create_private_state_then_read_back_and_idempotent_retry(self):
        self.assertTrue(self.commit()["changed"])
        self.assertFalse(self.commit()["changed"])
        self.assertEqual(len(self.client.posts), 1)
        self.assertTrue(inspect_reference(self.key, self.client)["present"])
        self.assertEqual(self.client.posts[0][1]["resource_type"], "state")
        self.assertNotIn("update_if_exists", self.client.posts[0][0])

    def test_404_is_absent_but_auth_and_server_errors_are_not(self):
        self.assertFalse(inspect_reference(self.key, self.client)["present"])
        for status in (401, 403, 500, 503):
            self.client.read_status = status
            with self.assertRaises(CheckpointError):
                self.commit()
        self.assertEqual(self.client.posts, [])

    def test_no_overwrite_of_nonprivate_or_unrelated_state(self):
        self.commit()
        for key, value in (("extra_perms", {"g/all": False}), ("created_by", "someone_else"),
                           ("resource_type", "postgresql"), ("value", {"unrelated": True})):
            old = copy.deepcopy(self.client.resources[self.path])
            self.client.resources[self.path][key] = value
            with self.assertRaises(CheckpointError):
                self.commit()
            self.client.resources[self.path] = old
        self.assertEqual(len(self.client.posts), 1)

    def test_backup_receipt_must_match_checkpoint(self):
        self.backup["sha256"] = "b" * 64
        with self.assertRaises(CheckpointError):
            self.commit()
        self.assertEqual(self.client.posts, [])

    def test_malformed_existing_reference_is_not_returned_or_overwritten(self):
        self.commit()
        original = copy.deepcopy(self.client.resources[self.path]["value"])
        for field, bad in (("version", {"unexpected": "payload"}), ("sha256", "not-a-hash"),
                           ("checkpoint_path", "arbitrary/path"), ("schema_version", True),
                           ("extra_field", "synthetic-not-a-secret")):
            self.client.resources[self.path]["value"] = {**original, field: bad}
            with self.assertRaises(CheckpointError):
                inspect_reference(self.key, self.client)
            with self.assertRaises(CheckpointError):
                self.commit()
        self.assertEqual(len(self.client.posts), 1)

    def test_existing_null_resource_is_not_mistaken_for_missing(self):
        self.commit()
        self.client.resources[self.path]["value"] = None
        with self.assertRaises(CheckpointError):
            inspect_reference(self.key, self.client)
        with self.assertRaises(CheckpointError):
            self.commit()
        self.assertEqual(len(self.client.posts), 1)

    def test_extra_payload_fields_rejected(self):
        self.cp["token"] = "synthetic-not-a-token"
        with self.assertRaises(CheckpointError):
            self.commit()

    def test_error_does_not_contain_response_payload(self):
        self.client.write_status = 403
        with self.assertRaisesRegex(CheckpointError, "HTTP 403"):
            self.commit()

    def test_live_sdk_refuses_wrong_context_without_importing(self):
        with patch.dict("os.environ", {"WM_WORKSPACE": "other", "WM_USERNAME": "admin"}):
            with self.assertRaises(CheckpointError):
                inspect_reference(self.key)

    def test_key_traversal_is_rejected(self):
        for key in ("../escape", "a//b", "/absolute", "a\\b", ".", "a" * 161):
            with self.assertRaises(CheckpointError):
                resource_path(key)


if __name__ == "__main__":
    unittest.main()
