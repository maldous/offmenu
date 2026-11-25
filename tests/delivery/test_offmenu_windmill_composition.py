import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import offmenu_native_upgrade_ingress as ingress


class CompositionTest(TestCase):
    def test_only_exact_fixed_packet_can_reach_shared_core(self):
        operation, release, head, tree = ("a"*64, "b"*64, "c"*40, "d"*40)
        job = "12345678-1234-1234-1234-123456789abc"
        review_raw = b"review"
        manifest_raw = json.dumps(dict(owner="user", head=head, tree=tree,
            review={"path": "package-review.json", "sha256": ingress.sha(review_raw)})).encode()
        approval = ingress.WindmillReleaseApproval(
            "user", operation, release, ingress.sha(manifest_raw), ingress.sha(b"request"), head, tree)
        request = dict(owner="user", package_sha256=ingress.sha(manifest_raw))
        packet_read = lambda path, _limit: manifest_raw if path.name == "manifest.json" else b"request"
        with (patch.object(ingress.os, "getresuid", return_value=(0, 0, 0)),
              patch.object(ingress, "release_digest", return_value=release),
              patch.object(ingress, "request_record", return_value=(request, b"request")),
              patch.object(ingress, "request_inputs", return_value=(
                  {"package-review.json": review_raw}, dict(owner="user", head=head, tree=tree))),
              patch.object(ingress, "read", side_effect=packet_read),
              patch.object(ingress, "signed_request", side_effect=AssertionError("signature route used")),
              patch.object(ingress, "_run_protected_release",
                           return_value={"state": "installed"}) as core):
            receiver = ingress.bind_private_windmill_release(approval, object(), object())
            self.assertEqual({"state": "installed"}, receiver("status", operation, job))
            self.assertEqual(("status", operation), core.call_args.args[:2])
            with self.assertRaisesRegex(ValueError, "operation_refused"):
                receiver("replace", "e"*64, job)
            request["package_sha256"] = "e"*64
            with self.assertRaisesRegex(ValueError, "approval_pin_mismatch"):
                receiver("replace", operation, job)
            core.assert_called_once()

    def test_unbound_receiver_is_not_a_fallback(self):
        with self.assertRaisesRegex(ValueError, "unbound"):
            ingress.bind_private_windmill_release(None, None, None)("status", "", "")
