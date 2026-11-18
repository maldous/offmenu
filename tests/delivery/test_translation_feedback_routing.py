"""Offline bridge contracts. In-memory ports are deliberate fixtures, never production."""
import dataclasses as dc
import importlib.util
from pathlib import Path
import sys
import unittest
from uuid import UUID


PATH = Path(__file__).resolve().parents[2] / "tools/delivery/translation_feedback.py"
SPEC = importlib.util.spec_from_file_location("offmenu_translation_intake_test_subject", PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)


def uid(i):
    return str(UUID(int=i))


ROUTE = m.Route(*(uid(i) for i in range(1, 5)))
KEY = "github:1416253963:issue:900"
URL = "https://github.com/maldous/offmenu/issues/42"
REV = "a" * 64


class Ports:
    def __init__(self):
        self.issue = m.Source("maldous/offmenu", 1416253963, "public", 900, 42, URL, "issue", "open", REV)
        self.review = m.Approval(KEY, REV, True, "translation")
        self.route_ok = self.writer = self.complete = self.settle_ok = self.trusted_prior = True
        self.reserved = self.lost_reply = False
        self.rows = []
        self.calls = []
        self.changed_at_effect = False
        self.initial_state = ROUTE.backlog_state
        self.original_create = None

    def source(self, n):
        return self.issue

    def approval(self, key):
        return self.review

    def route_current(self, r):
        return self.route_ok and r == ROUTE

    def matches(self, key):
        return m.Matches(tuple(self.rows), self.complete)

    def reserve_once(self, key, w):
        if not self.writer:
            return m.Reservation.DENIED
        if self.reserved:
            return m.Reservation.PRIOR
        self.reserved = True
        return m.Reservation.NEW

    def create_reserved(self, key, w):
        assert self.reserved and self.writer and key == w.source_key
        if self.changed_at_effect or w.reviewed_revision != self.issue.revision_sha256:
            raise PermissionError("source or approval no longer current")
        self.calls.append(w.linear_fields())
        self.rows.append(m.Record(uid(8), ROUTE.team, ROUTE.project, ROUTE.assignee,
                                  key, URL, self.initial_state))
        # Separate immutable fixture for the original native creation. A recorded
        # intent by itself does not set this, nor does a later mutable row.
        self.original_create = self.rows[0]
        if self.lost_reply:
            raise ConnectionError("do not surface private message")
        return uid(8)

    def readback(self, ident):
        return next(r for r in self.rows if r.id == ident)

    def settle(self, key, ident):
        return self.settle_ok and self.reserved and ident == uid(8)

    def reconcile_existing(self, key, ident):
        return self.original_create if self.trusted_prior and ident == uid(8) else None


class Intake(unittest.TestCase):
    def setUp(self):
        self.p = Ports()

    def call(self, number=42, route=ROUTE):
        return m.receive(number, route, self.p)

    def test_exact_route_minimal_payload_and_duplicate_after_status_change(self):
        first = self.call()
        self.assertEqual(first, m.Result("received", KEY, uid(8)))
        self.assertEqual(self.p.calls, [{"team": ROUTE.team, "project": ROUTE.project,
            "assignee": ROUTE.assignee, "state": ROUTE.backlog_state,
            "title": "OffMenu: Review translation suggestion #42",
            "description": f"Source: {URL}\nIntake ID: {KEY}"}])
        self.p.rows[0] = dc.replace(self.p.rows[0], state=uid(9))
        self.assertEqual(self.call(), m.Result("already-received", KEY, uid(8)))
        self.assertEqual(len(self.p.calls), 1)

    def test_wrong_repo_pr_state_url_and_identifier_cannot_route(self):
        for change in ({"repository": "unrelated/offmenu"}, {"repository_id": 99},
                {"visibility": "private"}, {"visibility": "internal"},
                {"kind": "pull_request"}, {"state": "closed"}, {"url": URL+"?x=1"},
                {"id": True}, {"number": 41}, {"revision_sha256": "not-a-hash"}):
            with self.subTest(change=change):
                self.p = Ports()
                self.p.issue = dc.replace(self.p.issue, **change)
                self.assertEqual(self.call().disposition, "source-not-eligible")
                self.assertFalse(self.p.reserved)

    def test_safety_edited_public_source_and_contributor_approval_do_not_transfer(self):
        for change in ({"allow_public_reference": False}, {"allow_public_reference": 1},
                       {"revision_sha256": "b"*64}, {"category": "security"},
                       {"source_key": KEY+"1"}):
            self.p = Ports()
            self.p.review = dc.replace(self.p.review, **change)
            self.assertEqual(self.call().disposition, "moderation-held")
            self.assertFalse(self.p.reserved)

    def test_bad_number_invalid_private_binding_and_missing_authority(self):
        for number in (0, True, "42", 2**63):
            self.assertEqual(self.call(number).disposition, "invalid-input")
        self.assertEqual(self.call(route=dc.replace(ROUTE, assignee=ROUTE.team)).disposition,
                         "invalid-input")
        self.p.route_ok = False
        self.assertEqual(self.call().disposition, "route-held")
        self.p.route_ok = True
        self.p.writer = False
        self.assertEqual(self.call().disposition, "writer-held")
        self.assertEqual(self.p.calls, [])

    def test_false_empty_or_untyped_receiving_collections_do_not_create(self):
        for bad in ("", {}, [], None, (object(),)):
            with self.subTest(kind=type(bad).__name__):
                self.p = Ports()
                self.p.matches = lambda _: m.Matches(bad, True)
                self.assertEqual(self.call().disposition, "receiving-lookup-incomplete")
                self.assertFalse(self.p.reserved)
                self.assertEqual(self.p.calls, [])

    def test_wrong_or_unproved_initial_route_never_becomes_duplicate_success(self):
        self.p.initial_state = uid(15)
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.p.rows[0] = dc.replace(self.p.rows[0], state=ROUTE.backlog_state)
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.p.original_create = None
        self.assertEqual(self.call().disposition, "reconcile-original")
        for false_receipt in (True, dc.replace(self.p.rows[0], id=uid(100)),
                              dc.replace(self.p.rows[0], team=uid(63))):
            self.p.reconcile_existing = lambda key, ident: false_receipt
            self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertEqual(len(self.p.calls), 1)

    def test_incomplete_lookup_conflicting_or_other_destination_never_creates(self):
        self.p.complete = False
        self.assertEqual(self.call().disposition, "receiving-lookup-incomplete")
        self.p.complete = True
        row = m.Record(uid(8), ROUTE.team, ROUTE.project, ROUTE.assignee, KEY, URL, uid(9))
        self.p.rows = [row, dc.replace(row, id=uid(19))]
        self.assertEqual(self.call().disposition, "ambiguous-receiving")
        self.p.rows = [dc.replace(row, project=uid(20))]
        self.assertEqual(self.call().disposition, "receiving-mismatch")
        self.p.rows = [row]
        self.assertEqual(self.call().disposition, "reconcile-original")  # no original intent
        self.assertEqual(self.p.calls, [])

    def test_lost_ack_recovers_from_same_native_record_and_never_recreates(self):
        self.p.lost_reply = True
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertEqual(self.call(), m.Result("already-received", KEY, uid(8)))
        self.p.rows.clear()  # missing or stale native result, original may still exist
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertEqual(len(self.p.calls), 1)

    def test_revision_change_at_effect_boundary_fails_closed_without_resend(self):
        self.p.changed_at_effect = True
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertTrue(self.p.reserved)
        self.assertEqual(self.p.calls, [])
        self.assertEqual(self.call().disposition, "reconcile-original")

    def test_readback_and_settlement_must_be_positive(self):
        self.p.readback = lambda _: m.Record(uid(17), ROUTE.team, ROUTE.project,
                ROUTE.assignee, KEY, URL, ROUTE.backlog_state)
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.p = Ports()
        self.p.settle_ok = False
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertEqual(len(self.p.calls), 1)

    def test_retry_after_existing_receipt_without_provenance_remains_held(self):
        self.assertEqual(self.call().disposition, "received")
        self.p.trusted_prior = False
        self.assertEqual(self.call().disposition, "reconcile-original")
        self.assertEqual(len(self.p.calls), 1)


if __name__ == "__main__":
    unittest.main()
