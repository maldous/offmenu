
"""Generated, network-blocked contract tests for the embedded completion publisher."""
import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import textwrap
import types
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path(os.environ.get("W57_PUBLISHER_TEST_WORKFLOW", ROOT / ".github/workflows/foo-runner.yml"))
workflow = WORKFLOW.read_text()
embedded = workflow.split("          #!/usr/bin/env python3\n", 1)[1].split("          PUBLISHER_PY\n", 1)[0]
PUB = types.ModuleType("generated_completion_publisher")
exec(compile("#!/usr/bin/env python3\n" + textwrap.dedent(embedded), str(WORKFLOW) + ":embedded", "exec"), PUB.__dict__)

def receipt():
    return {
        "schemaVersion": "offmenu-completion-receipt/1",
        "repositoryId": PUB.REPOSITORY_ID, "workflowId": PUB.WORKFLOW_ID,
        "runId": 100, "runNumber": 10, "runAttempt": 1,
        "publicationAttempt": 1, "sourceJobId": 200, "sourceRunnerId": 21,
        "controlSha": "a" * 40, "trustedCodeSha": "b" * 40,
        "request": {"schemaVersion": 1, "jobId": "generated-fixture-only", "profile": "readiness"},
        "sourceJobConclusion": "success",
        "report": {"validation": "verified", "status": "passed", "reportSha256": "c" * 64,
                   "requestIdentity": "d" * 64, "steps": []},
        "idempotencyKey": f"{PUB.REPOSITORY_ID}:100:1:200",
        "runUrl": "https://github.com/maldous/offmenu/actions/runs/100",
        "workflowRunTerminalAtPublish": False, "consumerMustVerifyTerminalRun": True,
    }

def target(state="closed"):
    return {"number": 31, "state": state, "merged": False,
            "head": {"ref": PUB.RESULTS_BRANCH, "repo": {"id": PUB.REPOSITORY_ID}},
            "base": {"ref": PUB.RESULTS_BASE, "repo": {"id": PUB.REPOSITORY_ID}}}

class FakeAPI:
    def __init__(self, pr=None, old=None):
        self.pr = target() if pr is None else pr
        self.old = {"schemaVersion": "offmenu-completion-bootstrap/1"} if old is None else old
        self.calls, self.puts = [], []
        self.errors = []
        self.saved = None
        self.commit = "e" * 40
        self.readback_wrong = False
        self.target_after_collision = None
        self.pr_reads = 0
        self.artifact = {"id": 300, "expired": False, "name": "offmenu-receipt-100-1",
                         "workflow_run": {"id": 100, "head_sha": "a" * 40},
                         "digest": "sha256:" + "f" * 64}

    def request(self, path, method="GET", payload=None):
        self.calls.append((path, method))
        prefix = "/repos/maldous/offmenu"
        if method == "GET" and path == prefix + "/actions/artifacts/300":
            return copy.deepcopy(self.artifact)
        if method == "GET" and path == prefix + "/pulls/31":
            self.pr_reads += 1
            return copy.deepcopy(self.target_after_collision if self.pr_reads > 1 and self.target_after_collision is not None else self.pr)
        contents = prefix + "/contents/" + PUB.RECEIPT_PATH
        if method == "GET" and path.startswith(contents + "?ref="):
            ref = path.split("?ref=", 1)[1]
            if ref == PUB.RESULTS_BRANCH:
                raw = PUB.canonical(self.old)
            elif ref == self.commit and self.saved is not None:
                raw = b"wrong generated readback" if self.readback_wrong else self.saved
            else:
                raise AssertionError("Unexpected generated fixture ref")
            return {"type": "file", "encoding": "base64", "size": len(raw),
                    "content": base64.b64encode(raw).decode(), "sha": "9" * 40}
        if method == "PUT" and path == contents:
            self.puts.append(copy.deepcopy(payload))
            if self.errors:
                raise PUB.Rejected(self.errors.pop(0))
            if payload["branch"] != PUB.RESULTS_BRANCH or payload["sha"] != "9" * 40:
                raise AssertionError("Receipt role/CAS changed")
            self.saved = base64.b64decode(payload["content"], validate=True)
            return {"commit": {"sha": self.commit}}
        raise AssertionError(f"Unexpected API path or job/control mutation: {method} {path}")

class PublisherContract(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"ARTIFACT_ID": "300", "ARTIFACT_DIGEST": "f" * 64}, clear=True)
        self.environment.start()
        self.network = patch.object(urllib.request.OpenerDirector, "open", side_effect=AssertionError("Network disabled"))
        self.network.start()
        self.connections = patch.object(socket, "create_connection", side_effect=AssertionError("Network disabled"))
        self.connections.start()
        temp_root = ROOT / ".generated-publisher-fixtures"
        temp_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="generated-only-", dir=temp_root)
        self.output = Path(self.tmp.name)
        (self.output / "evidence.json").write_bytes(PUB.canonical(receipt()))

    def tearDown(self):
        self.tmp.cleanup()
        self.connections.stop()
        self.network.stop()
        self.environment.stop()

    def run_publish(self, api):
        PUB.publish(api, self.output)

    def reject(self, api):
        with self.assertRaises(PUB.Rejected):
            self.run_publish(api)

    def test_closed_unmerged_publication_keeps_identity(self):
        api = FakeAPI()
        self.run_publish(api)
        self.assertEqual(len(api.puts), 1)
        result = json.loads(api.saved)
        expected = receipt()
        expected["artifact"] = {"id": 300, "sha256": "f" * 64,
                               "url": "https://github.com/maldous/offmenu/actions/runs/100/artifacts/300",
                               "retentionDays": 14}
        self.assertEqual(result, expected)
        self.assertIs(result["workflowRunTerminalAtPublish"], False)
        self.assertIs(result["consumerMustVerifyTerminalRun"], True)
        self.assertEqual(api.puts[0]["branch"], "offmenu-runner-results")

    def test_open_and_closed_publish_byte_identical_receipts(self):
        opened, closed = FakeAPI(target("open")), FakeAPI(target("closed"))
        self.run_publish(opened); self.run_publish(closed)
        self.assertEqual(opened.saved, closed.saved)

    def test_merged_target_rejected_before_write(self):
        api = FakeAPI(); api.pr["merged"] = True
        self.reject(api); self.assertEqual(api.puts, [])

    def test_wrong_pr_number_rejected(self):
        api = FakeAPI(); api.pr["number"] = 32
        self.reject(api); self.assertEqual(api.puts, [])

    def test_wrong_head_repository_rejected(self):
        api = FakeAPI(); api.pr["head"]["repo"]["id"] += 1
        self.reject(api); self.assertEqual(api.puts, [])

    def test_wrong_base_repository_rejected(self):
        api = FakeAPI(); api.pr["base"]["repo"]["id"] += 1
        self.reject(api); self.assertEqual(api.puts, [])

    def test_wrong_results_branch_rejected(self):
        api = FakeAPI(); api.pr["head"]["ref"] = "develop"
        self.reject(api); self.assertEqual(api.puts, [])

    def test_wrong_base_branch_rejected(self):
        api = FakeAPI(); api.pr["base"]["ref"] = "develop"
        self.reject(api); self.assertEqual(api.puts, [])

    def test_missing_state_rejected(self):
        api = FakeAPI(); del api.pr["state"]
        self.reject(api); self.assertEqual(api.puts, [])

    def test_unknown_state_rejected(self):
        api = FakeAPI(); api.pr["state"] = "unexpected"
        self.reject(api); self.assertEqual(api.puts, [])

    def test_missing_merged_boolean_rejected(self):
        api = FakeAPI(); del api.pr["merged"]
        self.reject(api); self.assertEqual(api.puts, [])

    def test_numeric_merged_false_rejected(self):
        api = FakeAPI(); api.pr["merged"] = 0
        self.reject(api); self.assertEqual(api.puts, [])

    def test_artifact_control_binding_rejected(self):
        api = FakeAPI(); api.artifact["workflow_run"]["head_sha"] = "0" * 40
        self.reject(api); self.assertEqual(api.puts, [])

    def test_expired_artifact_rejected(self):
        api = FakeAPI(); api.artifact["expired"] = True
        self.reject(api); self.assertEqual(api.puts, [])

    def test_duplicate_receipt_never_republishes(self):
        api = FakeAPI(old=receipt())
        self.run_publish(api); self.assertEqual(api.puts, [])

    def test_stale_receipt_never_republishes(self):
        old = receipt(); old["runNumber"] = 11
        api = FakeAPI(old=old)
        self.run_publish(api); self.assertEqual(api.puts, [])

    def test_same_identity_conflict_rejected(self):
        old = receipt(); old["idempotencyKey"] = "different"
        api = FakeAPI(old=old)
        self.reject(api); self.assertEqual(api.puts, [])

    def test_definite409_revalidates_closed_target_then_retries(self):
        api = FakeAPI(); api.errors = ["github-api-http-409"]
        self.run_publish(api)
        self.assertEqual(len(api.puts), 2); self.assertEqual(api.pr_reads, 2)

    def test_changed_target_after409_aborts(self):
        api = FakeAPI(); api.errors = ["github-api-http-409"]
        api.target_after_collision = target(); api.target_after_collision["merged"] = True
        self.reject(api); self.assertEqual(len(api.puts), 1)

    def test_http500_is_not_retried(self):
        api = FakeAPI(); api.errors = ["github-api-http-500"]
        self.reject(api); self.assertEqual(len(api.puts), 1)

    def test_uncertain_network_error_is_not_retried(self):
        api = FakeAPI(); api.errors = ["github-api-network-error"]
        self.reject(api); self.assertEqual(len(api.puts), 1)

    def test_readback_mismatch_is_not_retried(self):
        api = FakeAPI(); api.readback_wrong = True
        self.reject(api); self.assertEqual(len(api.puts), 1)

    def test_invalid_published_commit_is_not_retried(self):
        api = FakeAPI(); api.commit = "invalid"
        self.reject(api); self.assertEqual(len(api.puts), 1)

    def test_invalid_digest_aborts_before_api(self):
        os.environ["ARTIFACT_DIGEST"] = "not-a-digest"
        api = FakeAPI()
        self.reject(api); self.assertEqual(api.calls, [])

    def test_oversized_generated_evidence_aborts_before_api(self):
        (self.output / "evidence.json").write_bytes(b" " * (PUB.MAX_RECEIPT + 1))
        api = FakeAPI()
        self.reject(api); self.assertEqual(api.calls, [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
