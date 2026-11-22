"""OffMenu translation intake. No credential, network, poller or default writer.

An owner binds the ports to its existing authenticated readers, review and
effect authority. Input to receive() is a GitHub issue number, never a webhook
body, route, tracker assignment, command, callback URL or contributor text.
"""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol
from uuid import UUID


REPOSITORY = "maldous/offmenu"
REPOSITORY_ID = 1416253963


def _positive(n):
    return type(n) is int and 0 < n < 2**63


def _uuid(s):
    try:
        return isinstance(s, str) and str(UUID(s)) == s and UUID(s).int != 0
    except ValueError:
        return False


@dataclass(frozen=True)
class Route:
    # Supplied by a trusted private operational binding, never by the reporter.
    team: str
    project: str
    assignee: str
    backlog_state: str

    def valid(self):
        fields = (self.team, self.project, self.assignee, self.backlog_state)
        return all(_uuid(x) for x in fields) and len(set(fields)) == len(fields)


@dataclass(frozen=True)
class Source:
    repository: str
    repository_id: int
    visibility: str
    id: int
    number: int
    url: str
    kind: str
    state: str
    # Digest of the authenticated current revision actually shown to moderation.
    revision_sha256: str


@dataclass(frozen=True)
class Approval:
    # Produced by the private moderation surface, not by GitHub issue content.
    source_key: str
    revision_sha256: str
    allow_public_reference: bool
    category: str


@dataclass(frozen=True)
class Write:
    source_key: str
    source_url: str
    reviewed_revision: str
    title: str
    route: Route

    def linear_fields(self):
        # No title, Markdown, author, uploads, free text, or identifiers from the
        # user's private profile are copied from the untrusted issue body.
        return {"team": self.route.team, "project": self.route.project,
                "assignee": self.route.assignee, "state": self.route.backlog_state,
                "title": self.title, "description": f"Source: {self.source_url}\nIntake ID: {self.source_key}"}


@dataclass(frozen=True)
class Record:
    id: str
    team: str
    project: str
    assignee: str
    source_key: str
    source_url: str
    # Reported by the authenticated readback; state is checked on initial create.
    state: str


@dataclass(frozen=True)
class Matches:
    records: tuple
    # Exact source-key lookup across all relevant destinations, including known
    # historical/archived results, proved complete by the native reader.
    complete: bool


class Reservation(Enum):
    NEW = "new"
    PRIOR = "prior"      # any prior intent, including pending/uncertain/completed
    DENIED = "denied"    # no live writer, expired epoch, unavailable authority


class Ports(Protocol):
    def source(self, number: int) -> Source: ...
    def approval(self, key: str) -> Approval: ...
    def route_current(self, route: Route) -> bool: ...
    def matches(self, key: str) -> Matches: ...
    def reserve_once(self, key: str, write: Write) -> Reservation: ...
    def create_reserved(self, key: str, write: Write) -> str: ...
    def readback(self, native_id: str) -> Record: ...
    def settle(self, key: str, record_id: str) -> bool: ...
    def reconcile_existing(self, key: str, record_id: str) -> Record | None: ...


@dataclass(frozen=True)
class Result:
    disposition: str
    source_key: str = ""
    native_id: str = ""


def _matches_record(r, w, initial=False):
    return (isinstance(r, Record) and _uuid(r.id)
            and (r.team, r.project, r.assignee, r.source_key, r.source_url)
            == (w.route.team, w.route.project, w.route.assignee, w.source_key, w.source_url)
            and _uuid(r.state) and (not initial or r.state == w.route.backlog_state))


def receive(number: int, route: Route, ports: Ports) -> Result:
    """Return bounded status. No automatic retry or switch to alternate writer."""
    if not _positive(number) or not isinstance(route, Route) or not route.valid():
        return Result("invalid-input")
    key = ""
    try:
        source = ports.source(number)
        url = f"https://github.com/{REPOSITORY}/issues/{number}"
        if (not isinstance(source, Source) or not _positive(source.repository_id)
                or source.repository_id != REPOSITORY_ID or source.repository != REPOSITORY
                or source.visibility != "public"
                or not _positive(source.id) or not _positive(source.number) or source.number != number
                or source.kind != "issue" or source.state != "open" or source.url != url
                or not isinstance(source.revision_sha256, str)
                or not re.fullmatch(r"[a-f0-9]{64}", source.revision_sha256)):
            return Result("source-not-eligible")
        key = f"github:{REPOSITORY_ID}:issue:{source.id}"
        review = ports.approval(key)
        if (not isinstance(review, Approval) or review.source_key != key
                or review.revision_sha256 != source.revision_sha256
                or review.allow_public_reference is not True or review.category != "translation"):
            return Result("moderation-held", key)
        if ports.route_current(route) is not True:
            return Result("route-held", key)
        w = Write(key, url, source.revision_sha256, f"OffMenu: Review translation suggestion #{number}", route)
        matches = ports.matches(key)
        if (not isinstance(matches, Matches) or matches.complete is not True
                or type(matches.records) is not tuple
                or any(not isinstance(row, Record) for row in matches.records)):
            return Result("receiving-lookup-incomplete", key)
        if len(matches.records) > 1:
            return Result("ambiguous-receiving", key)
        if matches.records:
            row = matches.records[0]
            if not _matches_record(row, w):
                return Result("receiving-mismatch", key)
            # Reuse only after reading the actual native ID. A search result is
            # not an independent receipt and must not authorize a second write.
            checked = ports.readback(row.id)
            if not _matches_record(checked, w) or checked.id != row.id:
                return Result("receiving-mismatch", key)
            # Require the independent, immutable readback at ORIGINAL create.
            # The current record may legitimately have left Backlog since then;
            # a reservation, bare native ID, or Boolean cannot prove the initial route.
            original = ports.reconcile_existing(key, row.id)
            if not _matches_record(original, w, initial=True) or original.id != row.id:
                return Result("reconcile-original", key)
            return Result("already-received", key, row.id)
        # The *existing* effect authority must atomically fence the writer and
        # durably reserve the stable key before any side effect. No local dict
        # or check-then-create replacement is provided for production.
        reservation = ports.reserve_once(key, w)
        if reservation != Reservation.NEW:
            return Result("reconcile-original" if reservation == Reservation.PRIOR else "writer-held", key)
        native_id = ports.create_reserved(key, w)
        if not _uuid(native_id):
            return Result("reconcile-original", key)
        checked = ports.readback(native_id)
        if not _matches_record(checked, w, initial=True) or checked.id != native_id:
            return Result("reconcile-original", key)
        if ports.settle(key, native_id) is not True:
            return Result("reconcile-original", key)
        return Result("received", key, native_id)
    except Exception:
        # No exception text or public/private bodies in logs. Original readers
        # distinguish operational errors under the same ID; never retry here.
        return Result("reconcile-original" if key else "source-unavailable", key)
