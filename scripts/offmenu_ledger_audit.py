#!/usr/bin/env python3
"""Read-only structural audit of one immutable preserved journal; no projection."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SOURCE_COMMIT = "8c25c6d76088c958d17f7adc4a3c0af7aab5c298"
SOURCE_PREFIX = Path("docs/handover/2026-10-17")
SCHEMA = "offmenu-ledger-structural-audit/1"
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_FIELDS = 64
MAX_REPORT_BYTES = 12288
TYPE_NAMES = {"null", "boolean", "integer", "number", "string", "array", "object"}
# A source can put a secret in a key as easily as in a value. Unknown names are
# counted, never copied. These names expose structure, not record semantics.
SAFE_FIELD_NAMES = {"schema", "schemaVersion", "version", "sequence", "seq", "eventId", "event",
                    "eventType", "id", "type", "kind", "task", "taskId", "owner", "actor",
                    "recipient", "atUTC", "createdUTC", "recordedUTC", "updatedUTC", "timestamp",
                    "source", "sources", "sourceHash", "sourceSha256", "sha256", "previousHash",
                    "payload", "data", "record", "details", "metadata", "patch", "changes",
                    "before", "after", "operation", "target", "result", "state", "status",
                    "action", "reason", "evidence", "correlationId", "requestId", "parentEventId",
                    "dependencies", "nextAction", "scope", "mode", "authority"}
ERROR_CODES = {"source-checkout-invalid", "source-revision-mismatch", "source-file-invalid",
               "source-pin-mismatch", "source-json-invalid", "journal-structure-invalid",
               "journal-pin-mismatch", "report-limit-exceeded", "audit-failed"}
JOURNAL_INTS = {"bytes", "physicalLines", "nonEmptyLines", "jsonObjects", "invalidLines",
                "nonObjectLines", "firstInvalidLine", "omittedFieldOccurrences"}
JOURNAL_BOOLS = {"allJsonValid", "objectOnly", "allRecordsNewlineTerminated", "pinsMatch"}
JOURNAL_HASHES = {"gitBlob", "sha256", "prefix5269Sha256"}
LINEAGE_INTS = {"verifiedSourceFiles", "handoverEventCount", "summaryEventCount",
               "summarySourceSequence", "transportCheckpointCut"}
LINEAGE_BOOLS = {"initialBaseAuthorityMatches", "authorityHandoverMatches",
                "currentBaseHandoverMatches", "currentBaseSummaryMatches",
                "journalSummaryMatches", "handoverJournalPrefixMatches",
                "summaryEventCountMatchesPhysicalLines", "summarySequenceMatchesPhysicalLines",
                "handoverSummaryHashMatchesCurrentSummary", "checkpointPrecedesSummary"}
BOUNDARIES = {"knownRecordSchemaVerified", "semanticProjectionAvailable", "sequenceSemanticsVerified",
              "journalDerivedOwnershipAvailable", "currentWorkerCapacityEstablished",
              "sourceContentsUploaded", "sourceReceiptsVerified", "dispatchPerformed"}


class AuditError(Exception):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("source-json-invalid")
        result[key] = value
    return result


def finite_number(value):
    result = float(value)
    if not math.isfinite(result):
        raise AuditError("source-json-invalid")
    return result


def invalid_constant(_):
    raise AuditError("source-json-invalid")


def strict_json(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object,
                          parse_float=finite_number, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise AuditError("source-json-invalid") from None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def open_source(root, relative):
    """Only fixed regular checkout files; never follow source symlinks."""
    if relative.is_absolute() or ".." in relative.parts:
        raise AuditError("source-file-invalid")
    current = root
    for part in (None, *relative.parts):
        if part is not None:
            current = current / part
        if current.is_symlink():
            raise AuditError("source-file-invalid")
    fd = os.open(current, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
        os.close(fd)
        raise AuditError("source-file-invalid")
    return os.fdopen(fd, "rb"), info.st_size


def verify_source_checkout(root):
    if root.is_symlink() or not root.is_dir() or not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise AuditError("source-checkout-invalid")
    env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C.UTF-8",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                                   env=env, stderr=subprocess.DEVNULL, timeout=10)
    if head.strip().decode("ascii") != SOURCE_COMMIT:
        raise AuditError("source-revision-mismatch")


def read_verified_json(root, name, pin):
    stream, size = open_source(root, SOURCE_PREFIX / name)
    with stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    digest = hashlib.sha256(raw).hexdigest()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if size != len(raw) or len(raw) != pin["bytes"] or digest != pin["sha256"] or blob != pin["gitBlob"]:
        raise AuditError("source-pin-mismatch")
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise AuditError("source-json-invalid")
    return value


def value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def audit_stream(stream, size, pin):
    """Hash every byte; inspect JSON shape without interpreting record semantics."""
    sha256 = hashlib.sha256()
    blob = hashlib.sha1(b"blob " + str(size).encode() + b"\0")
    report = {key: 0 for key in JOURNAL_INTS}
    report.update(allRecordsNewlineTerminated=True, prefix5269Sha256=None)
    fields = {}
    while True:
        raw = stream.readline(MAX_LINE_BYTES + 1)
        if not raw:
            break
        report["physicalLines"] += 1
        number = report["physicalLines"]
        oversized = len(raw) > MAX_LINE_BYTES
        sha256.update(raw)
        blob.update(raw)
        report["bytes"] += len(raw)
        if report["bytes"] > MAX_SOURCE_BYTES:
            raise AuditError("source-file-invalid")
        # Continue hashing an oversized physical line without buffering it.
        while not raw.endswith(b"\n") and oversized:
            raw = stream.readline(MAX_LINE_BYTES + 1)
            if not raw:
                break
            sha256.update(raw)
            blob.update(raw)
            report["bytes"] += len(raw)
            if report["bytes"] > MAX_SOURCE_BYTES:
                raise AuditError("source-file-invalid")
        if number == 5269:
            report["prefix5269Sha256"] = sha256.copy().hexdigest()
        if not raw.endswith(b"\n"):
            report["allRecordsNewlineTerminated"] = False
        if raw.strip() or oversized:
            report["nonEmptyLines"] += 1
        try:
            if oversized:
                raise AuditError("source-json-invalid")
            value = strict_json(raw)
            if not isinstance(value, dict):
                report["nonObjectLines"] += 1
                continue
            report["jsonObjects"] += 1
            for name, item in value.items():
                if name not in SAFE_FIELD_NAMES or (name not in fields and len(fields) == MAX_FIELDS):
                    report["omittedFieldOccurrences"] += 1
                    continue
                fields.setdefault(name, Counter())[value_type(item)] += 1
        except AuditError:
            report["invalidLines"] += 1
            if not report["firstInvalidLine"]:
                report["firstInvalidLine"] = number
    report.update(sha256=sha256.hexdigest(), gitBlob=blob.hexdigest(),
                  allJsonValid=report["invalidLines"] == 0,
                  objectOnly=report["nonObjectLines"] == 0,
                  topLevelFields=[{"name": name, "types": dict(sorted(counts.items()))}
                                  for name, counts in sorted(fields.items())])
    report["pinsMatch"] = (size == report["bytes"] == pin["bytes"] and
                           report["sha256"] == pin["sha256"] and report["gitBlob"] == pin["gitBlob"])
    return report


def integer(value):
    if type(value) is not int or not 0 <= value <= 2**53 - 1:
        raise AuditError("source-json-invalid")
    return value


def build_report(root, pins):
    docs = {name: read_verified_json(root, name, pin) for name, pin in pins.items()
            if name != "operational-ledger/events.jsonl"}
    pin = pins["operational-ledger/events.jsonl"]
    stream, size = open_source(root, SOURCE_PREFIX / "operational-ledger/events.jsonl")
    with stream:
        journal = audit_stream(stream, size, pin)
    authority = docs["operational-ledger/authority.json"]
    handover = docs["operational-ledger/handover.json"]
    summary = docs["operational-ledger/management-summary.json"]
    checkpoint = docs["morgan-batches-20261017/current-checkpoint.json"]
    hashes = {name: value["sha256"] for name, value in pins.items()}
    lineage = {
        "verifiedSourceFiles": len(pins) if journal["pinsMatch"] else len(pins) - 1,
        "initialBaseAuthorityMatches": authority["initialBase"]["sha256"] == hashes["operational-ledger/base-initial-copy.json"],
        "authorityHandoverMatches": handover["authority"]["sha256"] == hashes["operational-ledger/authority.json"],
        "currentBaseHandoverMatches": handover["base"]["sha256"] == hashes["operational-ledger/interim-obligation-index.json"],
        "currentBaseSummaryMatches": summary["sources"]["base"]["sha256"] == hashes["operational-ledger/interim-obligation-index.json"],
        "journalSummaryMatches": summary["sources"]["journal"]["sha256"] == journal["sha256"],
        "handoverJournalPrefixMatches": handover["journal"]["sha256"] == journal["prefix5269Sha256"],
        "handoverSummaryHashMatchesCurrentSummary": handover["managementSummary"]["sha256"] == hashes["operational-ledger/management-summary.json"],
        "handoverEventCount": integer(handover["eventCount"]),
        "summaryEventCount": integer(summary["eventCount"]),
        "summarySourceSequence": integer(summary["sourceSequence"]),
        "transportCheckpointCut": integer(checkpoint["cut"]),
        "summaryEventCountMatchesPhysicalLines": summary["eventCount"] == journal["physicalLines"],
        "summarySequenceMatchesPhysicalLines": summary["sourceSequence"] == journal["physicalLines"],
        "checkpointPrecedesSummary": checkpoint["cut"] < summary["sourceSequence"],
    }
    complete = journal["pinsMatch"] and journal["allJsonValid"] and journal["objectOnly"]
    report = {"schemaVersion": SCHEMA, "sourceCommit": SOURCE_COMMIT,
              "status": "complete" if complete else "failed", "journal": journal, "lineage": lineage,
              "boundaries": dict.fromkeys(sorted(BOUNDARIES), False)}
    if not complete:
        report["errorCode"] = "journal-pin-mismatch" if not journal["pinsMatch"] else "journal-structure-invalid"
    return report


def sanitize_report(value):
    """Strict public-output contract, also used by the runner evidence filter."""
    if not isinstance(value, dict) or len(canonical(value)) > MAX_REPORT_BYTES:
        raise AuditError("report-limit-exceeded")
    if set(value) - {"schemaVersion", "sourceCommit", "status", "errorCode", "journal", "lineage", "boundaries"}:
        raise AuditError("audit-failed")
    if value.get("schemaVersion") != SCHEMA or value.get("sourceCommit") != SOURCE_COMMIT or value.get("status") not in {"complete", "failed"}:
        raise AuditError("audit-failed")
    if "errorCode" in value and value["errorCode"] not in ERROR_CODES:
        raise AuditError("audit-failed")
    if (not isinstance(value.get("boundaries"), dict) or set(value["boundaries"]) != BOUNDARIES or
            any(item is not False for item in value["boundaries"].values())):
        raise AuditError("audit-failed")
    if "journal" not in value:
        if value["status"] != "failed" or "errorCode" not in value or "lineage" in value:
            raise AuditError("audit-failed")
        return value
    journal = value["journal"]
    if not isinstance(journal, dict) or set(journal) != JOURNAL_INTS | JOURNAL_BOOLS | JOURNAL_HASHES | {"topLevelFields"}:
        raise AuditError("audit-failed")
    for key in JOURNAL_INTS:
        integer(journal[key])
    for key in JOURNAL_BOOLS:
        if type(journal[key]) is not bool:
            raise AuditError("audit-failed")
    for key in JOURNAL_HASHES:
        item = journal[key]
        if key == "prefix5269Sha256" and item is None:
            continue
        if not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{" + ("40" if key == "gitBlob" else "64") + r"}", item):
            raise AuditError("audit-failed")
    fields = journal["topLevelFields"]
    if not isinstance(fields, list) or len(fields) > MAX_FIELDS:
        raise AuditError("audit-failed")
    names = set()
    for field in fields:
        if not isinstance(field, dict) or set(field) != {"name", "types"}:
            raise AuditError("audit-failed")
        name, types = field["name"], field["types"]
        if not isinstance(name, str) or name not in SAFE_FIELD_NAMES or name in names:
            raise AuditError("audit-failed")
        names.add(name)
        if not isinstance(types, dict) or not types or set(types) - TYPE_NAMES:
            raise AuditError("audit-failed")
        for number in types.values():
            integer(number)
    lineage = value.get("lineage")
    if not isinstance(lineage, dict) or set(lineage) != LINEAGE_INTS | LINEAGE_BOOLS:
        raise AuditError("audit-failed")
    for key in LINEAGE_INTS:
        integer(lineage[key])
    for key in LINEAGE_BOOLS:
        if type(lineage[key]) is not bool:
            raise AuditError("audit-failed")
    return value


def main(argv=None):
    try:
        if (sys.argv[1:] if argv is None else argv):
            raise AuditError("audit-failed")
        script = Path(__file__).resolve()
        root = script.parent.parent.parent / "ledger-source"
        verify_source_checkout(root)
        pins = strict_json((script.parent / "offmenu-ledger-source-pins.json").read_bytes())
        report = sanitize_report(build_report(root, pins))
    except (AuditError, OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, AuditError) and str(error) in ERROR_CODES else "audit-failed"
        report = {"schemaVersion": SCHEMA, "sourceCommit": SOURCE_COMMIT, "status": "failed",
                  "errorCode": code, "boundaries": dict.fromkeys(sorted(BOUNDARIES), False)}
    print(canonical(report).decode("ascii"))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
