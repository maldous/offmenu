#requirements:
#paramiko==5.1.0
#wmill==1.850.0
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
    if os.environ.get("WM_WORKSPACE") != "offmenu" or os.environ.get("WM_USERNAME") != "admin":
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

"""Trusted public installer receipt pinned 2026-10-27; private draft client.
No secret material is accepted as an argument or intentionally emitted. Commands must
remain within the user's authorized checkout scope; output may contain command data.
"""
import base64
import re
import shlex
import math
import io
import json
import time

import paramiko
import wmill

HOST = "192.168.1.3"
PORT = 22
USER = "offmenu-wm"
# Fixed values copied from the user-supplied trusted public installer receipt.
SECRET_PATH = "u/admin/foo_ssh_key_20261027"
HOST_PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAgv17VNww/UZBfIohmz0jg0Xmim5s8FJuPyi4L9qZ0H"  # OpenSSH public key: algorithm base64 [comment]
DEFAULT_COMMAND = "id; pwd; if command -v git >/dev/null 2>&1; then printf 'git_present=true\\n'; else printf 'git_present=false\\n'; fi"
MAX_REQUEST_BYTES = 65536
MAX_OUTPUT_BYTES = 65536  # per stream; excess is drained and discarded
EXECUTION_SECONDS = 60


def _pin(client):
    fields = HOST_PUBLIC_KEY.split()
    key_types = {"ssh-ed25519": paramiko.Ed25519Key,
                 "ssh-rsa": paramiko.RSAKey,
                 "ecdsa-sha2-nistp256": paramiko.ECDSAKey,
                 "ecdsa-sha2-nistp384": paramiko.ECDSAKey,
                 "ecdsa-sha2-nistp521": paramiko.ECDSAKey}
    if len(fields) < 2 or fields[0] not in key_types:
        raise ValueError("Missing trusted host key")
    key = key_types[fields[0]](data=base64.b64decode(fields[1], validate=True))
    if key.get_name() != fields[0]:
        raise ValueError("Host key type mismatch")
    # Do not load system/user known_hosts; trust only the receipt's exact host key.
    client.get_host_keys().add(HOST, key.get_name(), key)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())


def _drain(channel, execution_seconds):
    stdout, stderr = bytearray(), bytearray()
    truncated = {"stdout": False, "stderr": False}
    deadline = time.monotonic() + execution_seconds
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Command deadline")
        progress = False
        # One chunk per stream each pass prevents either stream starving the other.
        for label, ready, receive, target in (
            ("stdout", channel.recv_ready, channel.recv, stdout),
            ("stderr", channel.recv_stderr_ready, channel.recv_stderr, stderr),
        ):
            if ready():
                chunk = receive(16384)
                available = MAX_OUTPUT_BYTES - len(target)
                target.extend(chunk[:available])
                truncated[label] |= len(chunk) > available
                progress = True
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            return {"stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "exit_code": channel.recv_exit_status(),
                    "truncated": truncated}
        if not progress:
            time.sleep(0.01)


class BusinessJobFailure(RuntimeError): pass
class OutcomeUnknown(RuntimeError): pass
class BusinessCancelled(RuntimeError): pass
class JobValidationFailure(ValueError): pass


def _capture_job_incident(job_id, code):
    try:
        return record_incident(job_id, "run", code, "u/admin/foo_jobs_20261027")
    except Exception:
        # Persistence failure must not turn a business failure green or leak SDK text.
        return {"recorded": False, "code": code, "capture_error": "INCIDENT_UNAVAILABLE"}


def _raise_job_failure(job_id, code, exception_type):
    incident = _capture_job_incident(job_id, code)
    state = "recorded" if incident.get("recorded") else "unavailable"
    raise exception_type(code + "; incident=" + state) from None


def _safe_receipt(job_id, receipt):
    if not isinstance(receipt, dict) or receipt.get("job_id") != job_id:
        raise ValueError("RECEIPT_ID_INVALID")
    states = {"starting", "running", "queued", "succeeded", "failed", "timed_out", "cancelled", "supervisor_error", "unknown", "busy", "blocked_reconciliation", "id_conflict", "request_error", "not_found", "cancellation_requested"}
    if receipt.get("status") not in states: raise ValueError("RECEIPT_STATE_INVALID")
    safe = {"job_id": job_id, "status": receipt["status"]}
    for key, value in receipt.items():
        if key in safe: continue
        valid = False
        if key in {"command_sha256", "request_sha256", "runner_sha256", "capacity_policy_sha256"}:
            valid = isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        elif key in {"created_at", "started_at", "finished_at", "heartbeat_at", "heartbeat_age_seconds"}:
            valid = type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 2**53
        elif key in {"reconcile_required", "child_tree_gone", "reserved", "terminal_verified"}:
            valid = type(value) is bool
        elif key == "version": valid = type(value) is int and value in (1, 3)
        elif key == "timeout_seconds": valid = type(value) is int and 1 <= value <= 1800
        elif key == "exit_code": valid = value is None or type(value) is int and -255 <= value <= 255
        elif key == "mode": valid = value in ("read", "write")
        elif key == "reason": valid = value in {"long_job_active", "incompatible_job_active", "two_slots_active", "unresolved_inflight_marker", "unresolved_long_job_marker", "no_safe_slot", "capacity_admission_busy", "capacity_pool_active", "capacity_legacy_active", "capacity_slots_active", "capacity_cpu_reserved", "capacity_memory_reserved", "capacity_processes_reserved", "capacity_disk_reserved", "capacity_io_reserved", "capacity_paths_conflict"}
        elif key == "error_class": valid = isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", value) is not None
        elif key == "unresolved_jobs":
            valid = isinstance(value, list) and len(value) <= 64 and all(isinstance(x,str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}",x) for x in value)
        elif key == "logs":
            valid = value == {name:"/offmenu/data/.offmenu-platform/jobs/"+job_id+"/"+name+".log" for name in ("stdout","stderr")}
        elif key in {"log_bytes", "output_bytes"}:
            valid = isinstance(value,dict) and set(value)=={"stdout","stderr"} and all(type(x) is int and 0<=x<=2**63-1 for x in value.values())
        elif key == "logs_truncated":
            valid = isinstance(value,dict) and set(value)=={"stdout","stderr"} and all(type(x) is bool for x in value.values())
        else: continue  # Never return arbitrary log/error/data fields from host state.
        if not valid: raise ValueError("RECEIPT_FIELD_INVALID")
        safe[key] = value
    return safe


def _job_result(action, job_id, receipt):
    try:
        receipt = _safe_receipt(job_id, receipt)
    except Exception:
        if action == "run": _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        raise OutcomeUnknown("RECEIPT_INVALID") from None
    state = receipt.get("status")
    incident = None
    if state in ("succeeded", "failed", "timed_out", "cancelled") and receipt.get("child_tree_gone") is not True:
        if action == "run": _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        raise OutcomeUnknown("CLEANUP_UNVERIFIED") from None
    if state == "succeeded" and receipt.get("exit_code") != 0:
        if action == "run": _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        raise OutcomeUnknown("SUCCESS_UNVERIFIED") from None
    if action == "run":
        if state == "failed": _raise_job_failure(job_id, "BUSINESS_FAILED", BusinessJobFailure)
        if state == "timed_out": _raise_job_failure(job_id, "BUSINESS_TIMED_OUT", BusinessJobFailure)
        if state in ("unknown", "supervisor_error"):
            _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        if state in ("blocked_reconciliation", "id_conflict"):
            incident = _capture_job_incident(job_id, "RECONCILIATION_BLOCKED" if state == "blocked_reconciliation" else "JOB_ID_CONFLICT")
        elif state in ("request_error", "not_found"):
            raise JobValidationFailure("JOB_REQUEST_REFUSED") from None
        elif state == "cancelled":
            raise BusinessCancelled("JOB_CANCELLED") from None
        elif state in ("running", "starting", "queued"):
            # Existing-ID retries are valid observations, not new submissions.
            if receipt.get("reconcile_required"):
                _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        elif state == "succeeded":
            if receipt.get("exit_code") != 0 or receipt.get("child_tree_gone") is not True:
                _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        elif state != "busy":
            _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
    result = {"ok": state == "succeeded", "transport_ok": True,
              "job_succeeded": state == "succeeded",
              "admitted": False if state in ("busy", "blocked_reconciliation", "request_error", "id_conflict", "not_found") else (None if state in ("unknown", "cancellation_requested") else True),
              "job_id": job_id, "receipt": receipt}
    if incident is not None: result["incident"] = incident
    return result


def main(action: str = "status", job_id: str = "", command: str = "",
         mode: str = "write", timeout_seconds: int = 45, resources: dict = None):
    """Use Windmill background runs for long jobs, then read run/job-ID receipts.
    read mode is a trusted scheduling promise, not a read-only filesystem boundary.
    Do not retry an unknown outcome under a new job ID without reconciliation.
    """
    client = None
    channel = None
    secret = None
    private_key = None
    try:
        if action not in ("run", "status", "cancel"):
            raise JobValidationFailure("INVALID_ACTION") from None
        if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", job_id):
            raise JobValidationFailure("INVALIDJOBID") from None
        if mode not in ("read", "write") or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1800:
            raise JobValidationFailure("INVALIDLIMITS") from None
        argv = ["python3", "/offmenu/tools/delivery/windmill_runner.py", action, "--job-id", job_id]
        if action == "run":
            if not isinstance(command, str) or not command or "\x00" in command or len(command.encode()) > 32000:
                raise JobValidationFailure("INVALIDCOMMAND") from None
            argv += ["--mode", mode, "--timeout", str(timeout_seconds)]
            request = base64.b64encode(json.dumps({"command": command, **({"resources": resources} if resources is not None else {})}).encode()).decode("ascii")
            remote_command = "printf %s " + shlex.quote(request) + " | base64 -d | " + shlex.join(argv)
        else:
            remote_command = shlex.join(argv)
        payload = json.dumps({"command": remote_command}, ensure_ascii=True).encode("utf-8")
        if len(payload) > MAX_REQUEST_BYTES:
            raise JobValidationFailure("REQUESTTOOLARGE") from None
        client = paramiko.SSHClient()
        _pin(client)
        secret = wmill.get_variable(SECRET_PATH)
        with io.StringIO(secret) as key_stream:
            private_key = paramiko.Ed25519Key.from_private_key(key_stream)
        secret = None
        client.connect(HOST, port=PORT, username=USER, pkey=private_key,
                       allow_agent=False, look_for_keys=False,
                       timeout=5, banner_timeout=5, auth_timeout=5,
                       channel_timeout=5)
        private_key = None
        transport = client.get_transport()
        if transport is None or not transport.is_authenticated():
            raise ConnectionError("Unauthenticated transport")
        channel = transport.open_session(timeout=5)
        channel.settimeout(5)
        channel.exec_command("offmenu-exec-v1")
        channel.sendall(payload)
        channel.shutdown_write()
        result = _drain(channel, timeout_seconds + 20 if action == "run" else 20)
        if result["exit_code"] != 0 or any(result["truncated"].values()):
            if action == "run": _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
            raise OutcomeUnknown("REMOTE_RECEIPT_UNAVAILABLE") from None
        receipt = json.loads(result["stdout"])
        return _job_result(action, job_id, receipt)
    except (BusinessJobFailure, OutcomeUnknown, BusinessCancelled, JobValidationFailure):
        raise
    except Exception:
        if action == "run" and isinstance(job_id, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", job_id):
            _raise_job_failure(job_id, "OUTCOME_UNKNOWN", OutcomeUnknown)
        raise OutcomeUnknown("TRANSPORT_OR_RECEIPT_UNAVAILABLE") from None
    finally:
        secret = None
        private_key = None
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


