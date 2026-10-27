#requirements:
#paramiko==5.1.0
#wmill==1.850.0
"""Trusted public installer receipt pinned 2026-10-27; private draft client.
No secret material is accepted as an argument or intentionally emitted. Commands must
remain within the user's authorized checkout scope; output may contain command data.
"""
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


def main(action: str = "status", job_id: str = "", command: str = "",
         mode: str = "write", timeout_seconds: int = 45):
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
            return {"ok": False, "error_class": "InvalidAction"}
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", job_id):
            return {"ok": False, "error_class": "InvalidJobId"}
        if mode not in ("read", "write") or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1800:
            return {"ok": False, "error_class": "InvalidLimits"}
        argv = ["python3", "/offmenu/scripts/windmill/job_runner.py", action, "--job-id", job_id]
        if action == "run":
            if not isinstance(command, str) or not command or "\x00" in command or len(command.encode()) > 32000:
                return {"ok": False, "error_class": "InvalidCommand"}
            argv += ["--mode", mode, "--timeout", str(timeout_seconds)]
            request = base64.b64encode(json.dumps({"command": command}).encode()).decode("ascii")
            remote_command = "printf %s " + shlex.quote(request) + " | base64 -d | " + shlex.join(argv)
        else:
            remote_command = shlex.join(argv)
        payload = json.dumps({"command": remote_command}, ensure_ascii=True).encode("utf-8")
        if len(payload) > MAX_REQUEST_BYTES:
            return {"ok": False, "error_class": "RequestTooLarge"}
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
            return {"ok": False, "error_class": "RemoteReceiptUnavailable",
                    "transport_exit_code": result["exit_code"], "job_id": job_id,
                    "reconcile_required": True}
        receipt = json.loads(result["stdout"])
        state = receipt.get("status")
        return {"ok": state == "succeeded", "transport_ok": True,
                "job_succeeded": state == "succeeded",
                "admitted": False if state in ("busy", "blocked_reconciliation", "request_error", "id_conflict", "not_found") else (None if state in ("unknown", "cancellation_requested") else True),
                "job_id": job_id, "receipt": receipt}
    except Exception as error:
        return {"ok": False, "error_class": type(error).__name__[:64],
                "job_id": job_id, "reconcile_required": action == "run"}
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
