"""Display-only counts: synthetic fixtures, no original data or live requests."""
from copy import deepcopy
import io
import unittest
from unittest.mock import patch

from offmenu.refresh.collection_progress import (
    FIELDS, ProgressReporter, asset_record_counts,
)
from offmenu.refresh.retained_collection import ReadAccounting
import test_collection_progress_hookup as hookup


def outcome(custody, stage, code=None):
    return {"custody": custody, "stage": stage, "code": code}


class DisplayMeaningTests(unittest.TestCase):
    def render(self, **values):
        stream = io.StringIO()
        reporter = ProgressReporter(stream=stream)
        reporter.update(**values)
        reporter._emit(reporter.snapshot())
        return stream.getvalue()

    def test_verified_custody_and_stage_counts_are_independent(self):
        alias = outcome("verified-original", "held", "extract-permission-held")
        rows = [alias, alias, outcome("verified-original", "error", "media-mismatch"),
                outcome("verified-original", "ready-nextstage"),
                outcome("verified-original", "held", "copy-permission-held"),
                outcome("stat-observed", "held"),
                outcome("no-path", "held", "extract-permission-held")]
        self.assertEqual(asset_record_counts(iter(rows)), {
            "failed": 1, "held": 5, "verified_original_records": 5,
            "extraction_held_records": 3, "extraction_held_verified_records": 2,
        })
        self.assertEqual(rows[0], alias)

    def test_full_cardinality_terminal_labels_are_exact_and_separate(self):
        # Matches reviewed count metadata, without embedding any real records.
        text = self.render(network_bytes=0, prepared=23, preparation_reused=18,
                           verified_original_records=1041, held=979, failed=92,
                           extraction_held_records=930, extraction_held_verified_records=929,
                           retained_preparation_unselected_held=913, prepared_bytes=15336896,
                           retained_selected=988, retained_verified=988,
                           retained_verified_payload_bytes=28437595507)
        self.assertIn("prepared-ready-total=23 new=5 reused=18", text)
        self.assertIn("asset records verified-original-records=1041 (aliases included)", text)
        self.assertIn("held-stage=979 extraction-held-stage=930 verified-extraction-held=929 other-held-stage=49", text)
        self.assertIn("failed-stage=92", text)
        self.assertIn("bytes network-body-read=0", text)
        self.assertIn("new-preparation-storage-known=15336896 (includes partial output)", text)
        self.assertIn("preparation-unselected-held=913", text)
        self.assertIn("retained payloads completed-verified=988/988", text)
        self.assertIn("verified-payload-bytes=28437595507 (excludes other local I/O)", text)
        for misleading in ("bytes read=", "unique", "files", "total-local", "GB", "100%"):
            self.assertNotIn(misleading, text)

    def test_unknown_scope_stays_unknown_and_negative_differences_are_not_invented(self):
        text = self.render(prepared=0, preparation_reused=1, held=0,
                           extraction_held_records=1, extraction_held_verified_records=1)
        self.assertIn("prepared-ready-total=0 new=unknown reused=1", text)
        self.assertIn("other-held-stage=unknown", text)
        self.assertIn("completed-verified=unknown/unknown", text)
        self.assertIn("verified-payload-bytes=unknown", text)
        self.assertIn("verified-original-records=unknown", text)

    def test_new_display_fields_keep_closed_integer_boundary(self):
        reporter = ProgressReporter(stream=io.StringIO())
        for field in ("verified_original_records", "extraction_held_records", "extraction_held_verified_records",
                      "retained_preparation_unselected_held",
                      "retained_selected", "retained_verified", "retained_verified_payload_bytes"):
            self.assertIn(field, FIELDS)
            for invalid in (True, -1, "private-path", 2**63, 1.5):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    reporter.update(**{field: invalid})
            reporter.update(**{field: None})

    def test_retained_payload_counts_never_use_reservations_or_uncertain_reads(self):
        assets = [{"assetId": str(i)} for i in range(4)]
        records = [{"assetId": str(i), "retainedOriginal": {"bytes": 100 + i},
                    "preparationContract": {}} for i in range(4)]
        plan = {"proposedAssetIds": [str(i) for i in range(4)],
                "proposedStructuralAssetIds": [], "budget": {"maximumOriginalReadBytes": 410}}
        account = ReadAccounting({"assets": assets}, {"records": records}, plan)
        for index in range(3):
            account.reserve(index)
        account.finish(0, {"integrityVerified": True})
        account.finish(1, None)
        account.finish(2, {"integrityVerified": True}, uncertain=True)
        summary = account.summary(lambda _: [])
        self.assertEqual(len(account.verified), 1)
        self.assertEqual(summary["verifiedOriginalPayloadBytes"], 100)
        self.assertEqual(summary["reservedOriginalReadBytes"], 306)
        self.assertEqual(account.uncertain, {2})
        self.assertNotIn(3, account.attempted)


class CollectorMeaningTests(unittest.TestCase):
    setUp = hookup.HookupTests.setUp
    retained = hookup.HookupTests.retained

    def test_deduplicated_preparation_counts_alias_records_separately(self):
        self.retained(2)
        f = self.fixture
        # The same original and contract produces one job and two asset records.
        f.manifest["assets"][1]["retainedOriginal"] = deepcopy(f.manifest["assets"][0]["retainedOriginal"])
        result = f.execute(terminal=self.reporter)
        state = self.reporter.snapshot()
        self.assertEqual(state["preparation_total"], 1)
        self.assertEqual(state["prepared"], 1)
        self.assertEqual(state["verified_original_records"], 2)
        self.assertEqual(state["extraction_held_verified_records"], 0)
        self.assertIsNone(state["retained_verified"])
        self.assertNotIn("retainedOriginalVerification", result)

    def test_completed_retained_counts_preserve_report_and_uncertainty(self):
        self.retained(3)
        f, g = self.fixture, hookup.g
        f.manifest["assets"][1]["preparationContract"]["permissions"]["extract"] = False
        records = deepcopy(f.manifest["assets"][:3])
        ids = [row["assetId"] for row in records]
        payload = sum(row["retainedOriginal"]["bytes"] for row in records)
        plan = {"proposedAssetIds": ids, "proposedStructuralAssetIds": [ids[0], ids[2]],
                "budget": {"maximumOriginalReadBytes": payload + 3}}
        f.selected["retainedVerification"] = {"status": "parent-reviewed-owner-manual"}
        def prepare(asset, contract, path, folder, deadline, maximum):
            if asset == ids[2]:
                return None, "global-preparation-unavailable", 0
            held = asset == ids[1]
            return {
                "status": "held" if held else "ready",
                "errorCode": "extract-permission-held" if held else None,
                "stages": {"integrity": "passed", "media": "passed", "extraction": "held" if held else "passed"},
                "actualMediaType": "text/csv", "originalSHA256": contract["expectedSHA256"],
                "originalBytes": contract["expectedBytes"], "outputs": [],
                "nextStageReady": not held, "metrics": {},
            }, None, 0
        with patch.object(g.retained_collection, "validate_combined", return_value=({"records": records}, plan, None)), \
             patch.object(g.taiwan, "run_diagnostics", return_value=None), \
             patch.object(g.prepdiag, "run_diagnostics", return_value=None), \
             patch("socket.create_connection", side_effect=AssertionError("live request forbidden")):
            observed = f.execute(prepare=prepare, owner_runtime=object(), terminal=self.reporter)
            unobserved = f.execute(prepare=prepare, owner_runtime=object())
        self.assertEqual(observed, unobserved)
        state = self.reporter.snapshot()
        self.assertEqual(state["retained_selected"], 3)
        self.assertEqual(state["retained_verified"], 2)
        self.assertEqual(state["retained_verified_payload_bytes"], payload * 2 // 3)
        self.assertEqual(state["verified_original_records"], 2)
        self.assertEqual(state["extraction_held_records"], 1)
        self.assertEqual(state["extraction_held_verified_records"], 1)
        self.assertEqual(state["retained_preparation_unselected_held"], 1)
        self.assertEqual(state["held"], 2)  # One extraction hold plus the baseline hold.
        self.assertEqual(state["preparation_completed"], 3)
        self.assertEqual(state["preparation_active"], 0)
        self.assertEqual(state["network_bytes"], 0)
        self.assertEqual(observed["retainedOriginalVerification"]["verifiedOriginalPayloadBytes"], state["retained_verified_payload_bytes"])
        self.assertEqual({group["state"] for group in observed["retainedOriginalVerification"]["jobOutcomeGroups"]}, {"completed-verified", "uncertain"})


if __name__ == "__main__":
    unittest.main()
