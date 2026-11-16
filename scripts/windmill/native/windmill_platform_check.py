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


import base64
import re
import shlex
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



"""Entrypoint appended to the reviewed incident/SSH helpers by build_native.py."""
_CHECK_PATH = 'u/admin/offmenu_platform_check'
_COUNT_KEYS = {'items_checked', 'items_skipped', 'entries_scanned', 'jobs_checked',
               'markers_checked', 'checkpoints_verified', 'artifact_manifests_verified',
               'artifact_objects_hashed'}
_FINDING_CODES = {'UNSAFE_COLLECTION', 'SYMLINK_ENTRY', 'MISSING_OR_UNSAFE_METADATA',
                  'INVALID_JOB_RECEIPT', 'STALE_ACTIVE_JOB', 'ACTIVE_INFLIGHT_JOB',
                  'UNRESOLVED_INFLIGHT_JOB', 'COMPLETED_NON_SUCCESS', 'UNKNOWN_JOB_STATE',
                  'ROOT_UNAVAILABLE', 'ROOT_OWNERSHIP_OR_MODE', 'INVALID_INFLIGHT_MARKER',
                  'CHECKPOINT_INTEGRITY_FAILED', 'CHECKPOINT_ADVANCED', 'ARTIFACT_INTEGRITY_FAILED',
                  'BUDGET_LIMIT_REACHED', 'CHECK_UNAVAILABLE', 'CHECK_REQUEST_FAILED'}
_SCOPES = {'health': 'recent job metadata and fixed in-flight markers',
           'verify': 'selected current checkpoints and artifact manifests; no history/orphan scan'}


class PlatformCheckFailure(RuntimeError):
    pass


def _check_receipt(value, mode, max_items):
    def require(ok):
        if not ok:
            raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')
    require(isinstance(value, dict) and set(value) == {'schema_version','checked_at','mode','ok',
            'findings','counts','budgets','coverage','status'})
    require(type(value['schema_version']) is int and value['schema_version'] == 1
            and value['mode'] == mode and type(value['ok']) is bool
            and value['status'] in ('ok','findings','incomplete'))
    try:
        stamp = datetime.fromisoformat(value['checked_at'].replace('Z','+00:00'))
        require(stamp.tzinfo is not None)
    except (ValueError,TypeError,AttributeError):
        raise PlatformCheckFailure('CHECK_RECEIPT_INVALID') from None
    counts = value['counts']; budgets = value['budgets']; coverage = value['coverage']
    require(isinstance(counts,dict) and set(counts) == _COUNT_KEYS
            and all(type(n) is int and 0 <= n <= 1000000 for n in counts.values())
            and counts['items_checked'] <= max_items and counts['markers_checked'] <= 2)
    require(isinstance(budgets,dict) and set(budgets) == {'max_items','max_bytes','max_seconds','bytes_read'}
            and type(budgets['max_items']) is int and budgets['max_items'] == max_items
            and type(budgets['max_bytes']) is int and budgets['max_bytes'] == 67108864
            and type(budgets['max_seconds']) in (int,float) and budgets['max_seconds'] == 8
            and type(budgets['bytes_read']) is int and 0 <= budgets['bytes_read'] <= 67108864)
    require(isinstance(coverage,dict) and set(coverage) == {'full_coverage','scope','selection_truncated',
            'stopped_reason','selected_scope_complete'} and coverage['full_coverage'] is False
            and coverage['scope'] == _SCOPES[mode]
            and type(coverage['selection_truncated']) is bool
            and type(coverage['selected_scope_complete']) is bool
            and coverage['stopped_reason'] in (None,'bytes','deadline'))
    require(isinstance(value['findings'],list) and len(value['findings']) <= 110)
    for finding in value['findings']:
        require(isinstance(finding,dict) and set(finding) <= {'code','severity','job_id','status','checkpoint_hash','manifest_hash'}
                and finding.get('code') in _FINDING_CODES and finding.get('severity') in ('info','warning','error'))
        if finding['code'] == 'CHECKPOINT_ADVANCED':
            require(mode == 'verify' and finding['severity'] == 'warning' and counts['items_skipped'] > 0)
        if 'job_id' in finding:
            require(isinstance(finding['job_id'],str) and bool(_JOB.fullmatch(finding['job_id'])))
        if 'status' in finding:
            require(finding['status'] in ('failed','timed_out','supervisor_error'))
        for key in ('checkpoint_hash','manifest_hash'):
            if key in finding:
                require(isinstance(finding[key],str) and bool(_SHA.fullmatch(finding[key])))
    errors = any(f['severity'] == 'error' for f in value['findings'])
    complete = not (coverage['selection_truncated'] or coverage['stopped_reason'] or counts['items_skipped'])
    require(coverage['selected_scope_complete'] is complete)
    require(value['ok'] is (complete and not errors))
    require(value['status'] == ('incomplete' if not complete else ('findings' if errors else 'ok')))
    return value


def _check_native_state():
    client = _incident_sdk()
    response = client.get('/w/offmenu/resources/get/u/admin/offmenu_platform',raise_for_status=False)
    if response.status_code != 200:
        raise PlatformCheckFailure('CHECK_TRANSPORT_FAILED')
    meta = response.json()
    value = meta.get('value',{})
    if (meta.get('path') != 'u/admin/offmenu_platform' or meta.get('workspace_id') != 'offmenu'
            or meta.get('created_by') != 'admin' or meta.get('extra_perms') != {}
            or meta.get('resource_type') != 'state' or not isinstance(value,dict)
            or value.get('format') != 'offmenu-platform-config-v1' or value.get('schema_version') != 1):
        raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')


def _remote_check(mode, max_items):
    client = channel = secret = private_key = None
    try:
        client = paramiko.SSHClient(); _pin(client)
        secret = wmill.get_variable(SECRET_PATH)
        with io.StringIO(secret) as stream:
            private_key = paramiko.Ed25519Key.from_private_key(stream)
        secret = None
        client.connect(HOST,port=PORT,username=USER,pkey=private_key,allow_agent=False,look_for_keys=False,
                       timeout=5,banner_timeout=5,auth_timeout=5,channel_timeout=5)
        private_key = None
        transport = client.get_transport()
        if transport is None or not transport.is_authenticated():
            raise PlatformCheckFailure('CHECK_TRANSPORT_FAILED')
        channel = transport.open_session(timeout=5); channel.settimeout(5)
        command = shlex.join(['python3','/offmenu/scripts/windmill/platform_check.py',
                              '--mode',mode,'--max-items',str(max_items)])
        channel.exec_command('offmenu-exec-v1')
        channel.sendall(json.dumps({'command':command},ensure_ascii=True).encode())
        channel.shutdown_write()
        receipt = _drain(channel,20)
        if any(receipt['truncated'].values()) or receipt['exit_code'] not in (0,1):
            raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')
        value = _check_receipt(json.loads(receipt['stdout']),mode,max_items)
        if receipt['exit_code'] != (0 if value['ok'] else 1):
            raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')
        return value
    finally:
        secret = private_key = None
        for item in (channel,client):
            if item is not None:
                try: item.close()
                except Exception: pass


def _check_incident_failure(code, mode):
    wid = os.environ.get('WM_JOB_ID','').lower()
    logical_id = 'check-' + wid if _UUID.fullmatch(wid) else 'check-without-run-id'
    try:
        receipt = record_incident(logical_id,mode,code,_CHECK_PATH)
        print(json.dumps({'code':code,'incident_resource_path':receipt['resource_path']}))
    except IncidentError:
        print(json.dumps({'code':code,'incident_recorded':False}))
    raise PlatformCheckFailure(code) from None


def main(mode: str = 'health', max_items: int = 100):
    if mode not in ('health','verify') or type(max_items) is not int or not 1 <= max_items <= 100:
        raise ValueError('CHECK_INPUT_INVALID')
    try:
        _check_native_state()
        result = _remote_check(mode,max_items)
    except PlatformCheckFailure as error:
        code = str(error) if str(error) in ('CHECK_RECEIPT_INVALID','CHECK_TRANSPORT_FAILED') else 'CHECK_TRANSPORT_FAILED'
        _check_incident_failure(code,mode)
    except Exception:
        _check_incident_failure('CHECK_TRANSPORT_FAILED',mode)
    if any(f['severity'] == 'error' for f in result['findings']):
        _check_incident_failure('HEALTH_FINDINGS' if mode == 'health' else 'VERIFY_FINDINGS',mode)
    # A bounded partial check is not an integrity failure and is never called healthy.
    # No incident/automatic replay/pruning is generated for coverage-only warnings.
    return dict(result,native_config_private=True)
