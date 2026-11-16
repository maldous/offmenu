"""Owner-private, create-only OffMenu incident records; no aggregate updates.

Callers supply opaque, nonsecret job identifiers. Never pass commands, logs, raw
errors, credentials, datasets, arbitrary paths or upstream provider responses.
This module uses the existing Windmill job authentication, never a new token.
"""
import hashlib
import os
import re
from datetime import datetime, timezone

INCIDENT_PREFIX = "u/admin/offmenu_platform/incidents/"
_JOB = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CODES = {
    "BUSINESS_FAILED": ("error", False),
    "BUSINESS_TIMED_OUT": ("error", True),
    "OUTCOME_UNKNOWN": ("critical", True),
    "RECONCILIATION_BLOCKED": ("critical", True),
    "JOB_ID_CONFLICT": ("critical", True),
    "HEALTH_FINDINGS": ("error", True),
    "VERIFY_FINDINGS": ("error", True),
    "CHECK_RECEIPT_INVALID": ("error", True),
    "CHECK_TRANSPORT_FAILED": ("error", True),
    "SELFTEST_FAILURE": ("test", False),
}
_PHASES = {"run", "health", "verify", "selftest"}
_FIELDS = {"format", "schema_version", "logical_job_id", "phase", "code", "severity",
           "needs_reconciliation", "path_sha256", "windmill_job_id", "created_at", "test"}
_IDENTITY_FIELDS = ("logical_job_id", "phase", "code", "path_sha256", "test")


class IncidentError(RuntimeError):
    """Fixed safe error codes only; never retain an underlying exception string."""


def _incident_sdk(client=None):
    if client is not None:
        return client
    username = os.environ.get("WM_USERNAME")
    schedule = os.environ.get("WM_SCHEDULE_PATH")
    scheduled_owner = (schedule in ("u/admin/offmenu_platform_health_15m", "u/admin/offmenu_platform_verify_daily")
                       and username == "schedule-" + schedule.replace("/", "-")
                       and os.environ.get("WM_JOB_PATH") == "u/admin/offmenu_platform_check")
    if (os.environ.get("WM_WORKSPACE") != "offmenu"
            or os.environ.get("WM_PERMISSIONED_AS") != "u/admin"
            or not (username == "admin" or scheduled_owner)):
        raise IncidentError("INCIDENT_OWNER_REQUIRED")
    import wmill
    return wmill.Windmill()


def incident_identity(logical_job_id, phase, code, source_path, test=False):
    if not isinstance(logical_job_id, str) or not _JOB.fullmatch(logical_job_id):
        raise IncidentError("INCIDENT_JOB_ID_INVALID")
    if phase not in _PHASES or code not in _CODES or type(test) is not bool:
        raise IncidentError("INCIDENT_CLASS_INVALID")
    if (code == "SELFTEST_FAILURE") != test or (phase == "selftest") != test:
        raise IncidentError("INCIDENT_TEST_CLASS_INVALID")
    if source_path not in ("u/admin/foo_jobs_20261027", "u/admin/offmenu_platform_check",
                           "u/admin/offmenu_incident_selftest"):
        raise IncidentError("INCIDENT_SOURCE_INVALID")
    return {"logical_job_id": logical_job_id, "phase": phase, "code": code,
            "path_sha256": hashlib.sha256(source_path.encode()).hexdigest(), "test": test}


def incident_resource_path(identity):
    import json
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return INCIDENT_PREFIX + hashlib.sha256(encoded).hexdigest()


def _validate_incident(value, identity):
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise IncidentError("INCIDENT_SCHEMA_INVALID")
    if (value.get("format") != "offmenu-incident-v1" or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1
            or any(value.get(k) != identity[k] for k in _IDENTITY_FIELDS)):
        raise IncidentError("INCIDENT_IDENTITY_CONFLICT")
    severity, reconcile = _CODES[identity["code"]]
    if (value.get("severity") != severity or value.get("needs_reconciliation") is not reconcile
            or not _SHA.fullmatch(value.get("path_sha256", ""))):
        raise IncidentError("INCIDENT_METADATA_INVALID")
    wid = value.get("windmill_job_id")
    if wid is not None and (not isinstance(wid, str) or not _UUID.fullmatch(wid)):
        raise IncidentError("INCIDENT_JOB_REFERENCE_INVALID")
    try:
        ts = datetime.fromisoformat(value["created_at"].replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise IncidentError("INCIDENT_TIMESTAMP_INVALID") from None
    return value


def _incident_read(client, path, identity):
    response = client.get(f"/w/offmenu/resources/get/{path}", raise_for_status=False)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise IncidentError("INCIDENT_READ_REFUSED")
    meta = response.json()
    if (not isinstance(meta, dict) or meta.get("path") != path or meta.get("workspace_id") != "offmenu"
            or meta.get("resource_type") != "state" or meta.get("extra_perms") != {}
            or meta.get("created_by") != "admin"):
        raise IncidentError("INCIDENT_OWNER_MISMATCH")
    return _validate_incident(meta.get("value"), identity)


def record_incident(logical_job_id, phase, code, source_path, *, test=False, client=None):
    """Create once, verify owner/privacy/schema, deduplicate concurrent exact identities.

    The first Windmill job ID/time wins. Retries don't overwrite custody metadata;
    no get-modify-set, aggregate state write, notification or mutation retry occurs.
    """
    identity = incident_identity(logical_job_id, phase, code, source_path, test)
    path = incident_resource_path(identity)
    try:
        client = _incident_sdk(client)
        existing = _incident_read(client, path, identity)
        created = False
        if existing is None:
            wid = os.environ.get("WM_JOB_ID", "").lower()
            severity, reconcile = _CODES[code]
            desired = dict(identity, format="offmenu-incident-v1", schema_version=1,
                           severity=severity, needs_reconciliation=reconcile,
                           windmill_job_id=wid if _UUID.fullmatch(wid) else None,
                           created_at=datetime.now(timezone.utc).isoformat())
            response = client.post("/w/offmenu/resources/create", raise_for_status=False,
                                   json={"path": path, "resource_type": "state", "value": desired,
                                         "description": "Sanitized OffMenu incident; create-only per job/code"})
            # Re-read after success or a create race. Do not overwrite or retry.
            existing = _incident_read(client, path, identity)
            if response.status_code not in (200, 201) and existing is None:
                raise IncidentError("INCIDENT_CREATE_REFUSED")
            if existing is None:
                raise IncidentError("INCIDENT_READBACK_MISSING")
            created = response.status_code in (200, 201)
        return {"recorded": True, "created": created, "resource_path": path,
                "code": code, "needs_reconciliation": existing["needs_reconciliation"],
                "test": test}
    except IncidentError:
        raise
    except Exception:
        raise IncidentError("INCIDENT_PERSISTENCE_UNAVAILABLE") from None
