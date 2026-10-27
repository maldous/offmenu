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


"""Pure command builders for bounded offmenu-exec-v1 offline transfer.

No SSH credentials, socket operations or host writes occur in this module.
Every generated command uses the jail's Python stdlib and fixed private root.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex

ROOT = "/offmenu/data/.offmenu-platform/duckdb"
FILENAME = "duckdb-1.5.6-cp312-cp312-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl"
SHA256 = "bc9619ed7d4ffa117b5155d84b44794366bb6635178d78ed5e13a6024845c757"
SIZE = 21568087
CHUNK_SIZE = 40960
MAX_REQUEST_BYTES = 65536


def command(code):
    value = "python3 -I -S -c " + shlex.quote(code)
    if len(json.dumps({"command": value}, ensure_ascii=True).encode()) > MAX_REQUEST_BYTES:
        raise ValueError("Command exceeds SSH protocol request bound")
    return value


def stage_path(stage_id):
    if not isinstance(stage_id, str) or not re.fullmatch(r"[0-9a-f]{32}", stage_id):
        raise ValueError("Expected 32 lowercase hex characters")
    return ROOT + "/stage-" + stage_id


def preamble(stage_id):
    return "\n".join([
        "import os,stat,json,base64,hashlib",
        "from pathlib import Path",
        "p=Path(" + repr(stage_path(stage_id)) + ")",
        "if p.resolve()!=p or not p.is_dir(): raise ValueError('Unsafe stage')",
        "if p.stat().st_uid != os.geteuid(): raise ValueError('Unexpected stage owner')",
        "if p.stat().st_mode & 0o077: raise ValueError('Stage must be private')",
    ]) + "\n"


def prepare_command(stage_id, files):
    allowed = {"install_offline.py", "runtime.py", "lock.json", "requirements.lock", "LICENSE.duckdb"}
    if set(files) != allowed:
        raise ValueError("Exact reviewed helper file set required")
    payload = {name: {"base64": base64.b64encode(value).decode(),
                       "sha256": hashlib.sha256(value).hexdigest()} for name, value in files.items()}
    code = "\n".join([
        "import os,stat,subprocess,json,base64,hashlib",
        "from pathlib import Path",
        "root=Path(" + repr(ROOT) + ")",
        "p=Path(" + repr(stage_path(stage_id)) + ")",
        "r=subprocess.run(['git','-C','/offmenu','check-ignore','-q','data/.offmenu-platform/duckdb/'])",
        "if r.returncode != 0: raise ValueError('Runtime root is not git-ignored')",
        "for node in (Path('/offmenu'),Path('/offmenu/data')):",
        " if node.resolve()!=node or not node.is_dir(): raise ValueError('Unsafe root ancestor')",
        "for node in (root.parent,root):",
        " if node.is_symlink(): raise ValueError('Symlink runtime root')",
        " node.mkdir(mode=0o700,exist_ok=True)",
        " if node.resolve()!=node or not node.is_dir(): raise ValueError('Unsafe runtime root')",
        " if node.stat().st_uid != os.geteuid() or node.stat().st_mode & 0o077: raise ValueError('Runtime root must be private and owned')",
        "p.mkdir(mode=0o700)",
        "files=" + repr(payload),
        "for name,entry in files.items():",
        " value=base64.b64decode(entry['base64'],validate=True)",
        " if hashlib.sha256(value).hexdigest()!=entry['sha256']: raise ValueError('Helper digest mismatch')",
        " fd=os.open(p/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)",
        " with os.fdopen(fd,'wb') as f: f.write(value)",
        "fd=os.open(p/" + repr(FILENAME) + ",os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)",
        "os.close(fd)",
        "print(json.dumps({'stage_id':" + repr(stage_id) + ",'offset':0,'prepared':True}))",
    ])
    return command(code)


def status_command(stage_id):
    code = preamble(stage_id) + "\n".join([
        "f=p/" + repr(FILENAME),
        "s=f.lstat()",
        "if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1: raise ValueError('Unsafe wheel')",
        "print(json.dumps({'offset':s.st_size,'stage_id':" + repr(stage_id) + "}))",
    ])
    return command(code)


def chunk_command(stage_id, offset, data):
    if type(offset) is not int or offset < 0 or offset > SIZE:
        raise ValueError("Invalid offset")
    if not isinstance(data, bytes) or not data or len(data) > CHUNK_SIZE or offset + len(data) > SIZE:
        raise ValueError("Invalid chunk")
    code = preamble(stage_id) + "\n".join([
        "value=base64.b64decode(" + repr(base64.b64encode(data).decode()) + ",validate=True)",
        "if hashlib.sha256(value).hexdigest()!=" + repr(hashlib.sha256(data).hexdigest()) + ": raise ValueError('Chunk digest mismatch')",
        "offset=" + str(offset),
        "fd=os.open(p/" + repr(FILENAME) + ",os.O_RDWR|os.O_NOFOLLOW)",
        "with os.fdopen(fd,'r+b') as f:",
        " s=os.fstat(f.fileno())",
        " if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1: raise ValueError('Unsafe wheel')",
        " if s.st_size == offset:",
        "  f.seek(offset); f.write(value); f.flush()",
        " elif s.st_size == offset+len(value):",
        "  f.seek(offset)",
        "  if f.read(len(value)) != value: raise ValueError('Retry data mismatch')",
        " else: raise ValueError('Offset mismatch')",
        "print(json.dumps({'offset':offset+len(value)}))",
    ])
    return command(code)


def install_command(stage_id):
    stage = stage_path(stage_id)
    code = preamble(stage_id) + "\n".join([
        "import subprocess,sys",
        "f=p/" + repr(FILENAME),
        "s=f.lstat()",
        "if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size!=" + str(SIZE) + ": raise ValueError('Incomplete or unsafe wheel')",
        "with f.open('rb') as h: digest=hashlib.file_digest(h,'sha256').hexdigest()",
        "if digest!=" + repr(SHA256) + ": raise ValueError('Final wheel digest mismatch')",
        "r=subprocess.run([sys.executable,'-I','-S',str(p/'install_offline.py'),str(p)],capture_output=True,text=True,timeout=55)",
        "sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); raise SystemExit(r.returncode)",
    ])
    return command(code)

FILES = {'install_offline.py': 'IiIiU3RyaWN0IHNpbmdsZS13aGVlbCBvZmZsaW5lIGluc3RhbGxlcjogaXNvbGF0ZWQgdmVudiBhbmQgaGFzaC1yZXF1aXJlZCBwaXAuCgpPbmx5IGluc3RhbGwgdGhlIHJldmlld2VkIHBpbm5lZCB3aGVlbCBpbnRvIGEgZnJlc2ggdmVyc2lvbmVkIHByaXZhdGUgZGlyZWN0b3J5LgpOZXZlciBtb2RpZmllcyBhIHN5c3RlbSBpbnRlcnByZXRlciBvciBleGlzdGluZyBydW50aW1lLiBVc2UgdmlhIHRoZSB0cmFuc2ZlcgpoZWxwZXIgYWZ0ZXIgdGhlIHNvbGUgRm9vIHdyaXRlciBoYXMgYXV0aG9yaXplZCB0aGUgaG9zdCBtdXRhdGlvbi4KIiIiCmltcG9ydCBiYXNlNjQKaW1wb3J0IGNzdgppbXBvcnQgZW1haWwucGFyc2VyCmltcG9ydCBoYXNobGliCmltcG9ydCBpbwppbXBvcnQganNvbgppbXBvcnQgb3MKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoLCBQdXJlUG9zaXhQYXRoCmltcG9ydCBwbGF0Zm9ybQppbXBvcnQgc2h1dGlsCmltcG9ydCBzdGF0CmltcG9ydCBzdWJwcm9jZXNzCmltcG9ydCBzeXMKaW1wb3J0IHppcGZpbGUKaW1wb3J0IHZlbnYKClZFUlNJT04gPSAiMS41LjYiClNIQTI1NiA9ICJiYzk2MTllZDdkNGZmYTExN2I1MTU1ZDg0YjQ0Nzk0MzY2YmI2NjM1MTc4ZDc4ZWQ1ZTEzYTYwMjQ4NDVjNzU3IgpTSVpFID0gMjE1NjgwODcKRklMRU5BTUUgPSAiZHVja2RiLTEuNS42LWNwMzEyLWNwMzEyLW1hbnlsaW51eF8yXzI2X3g4Nl82NC5tYW55bGludXhfMl8yOF94ODZfNjQud2hsIgpST09UID0gUGF0aCgiL29mZm1lbnUvZGF0YS8ub2ZmbWVudS1wbGF0Zm9ybS9kdWNrZGIiKQpSVU5USU1FX05BTUUgPSAiMS41LjYtYmM5NjE5ZWQ3ZDRmIgpESVNUID0gImR1Y2tkYi0xLjUuNi5kaXN0LWluZm8iCkFMTE9XRURfVE9QID0geyJkdWNrZGIiLCAiX2R1Y2tkYi1zdHVicyIsICJhZGJjX2RyaXZlcl9kdWNrZGIiLCBESVNULAogICAgICAgICAgICAgICAiX2R1Y2tkYi5jcHl0aG9uLTMxMi14ODZfNjQtbGludXgtZ251LnNvIn0KCgpkZWYgY2hlY2tfcGF0aChwYXRoLCBkaXJlY3Rvcnk9RmFsc2UpOgogICAgaWYgbm90IHBhdGguaXNfYWJzb2x1dGUoKSBvciBwYXRoLnJlc29sdmUoKSAhPSBwYXRoOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlVuc2FmZSBwYXRoIG9yIHN5bWxpbmsgYW5jZXN0b3IiKQogICAgc3QgPSBwYXRoLmxzdGF0KCkKICAgIGlmIGRpcmVjdG9yeToKICAgICAgICBpZiBub3Qgc3RhdC5TX0lTRElSKHN0LnN0X21vZGUpOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJOb3QgYSBkaXJlY3RvcnkiKQogICAgZWxpZiBub3Qgc3RhdC5TX0lTUkVHKHN0LnN0X21vZGUpIG9yIHN0LnN0X25saW5rICE9IDE6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiTm90IGEgc2luZ2x5IGxpbmtlZCByZWd1bGFyIGZpbGUiKQogICAgcmV0dXJuIHN0CgoKZGVmIHZlcmlmeV9ob3N0KCk6CiAgICBsaWJjLCB2ZXJzaW9uID0gcGxhdGZvcm0ubGliY192ZXIoKQogICAgaWYgcGxhdGZvcm0ucHl0aG9uX2ltcGxlbWVudGF0aW9uKCkgIT0gIkNQeXRob24iIG9yIHN5cy52ZXJzaW9uX2luZm9bOjJdICE9ICgzLCAxMik6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJDUHl0aG9uIDMuMTIgcmVxdWlyZWQiKQogICAgaWYgcGxhdGZvcm0uc3lzdGVtKCkgIT0gIkxpbnV4IiBvciBwbGF0Zm9ybS5tYWNoaW5lKCkgIT0gIng4Nl82NCI6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJMaW51eCB4ODZfNjQgcmVxdWlyZWQiKQogICAgaWYgbGliYyAhPSAiZ2xpYmMiIG9yIHR1cGxlKG1hcChpbnQsIHZlcnNpb24uc3BsaXQoIi4iKVs6Ml0pKSA8ICgyLCAyNik6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJnbGliYyA+PSAyLjI2IHJlcXVpcmVkIikKCgpkZWYgdmVyaWZ5X2FyY2hpdmUod2hlZWxfcGF0aCwgZXhwZWN0ZWRfZGlnZXN0PVNIQTI1NiwgZXhwZWN0ZWRfc2l6ZT1TSVpFKToKICAgIHN0ID0gY2hlY2tfcGF0aCh3aGVlbF9wYXRoKQogICAgaWYgc3Quc3Rfc2l6ZSAhPSBleHBlY3RlZF9zaXplOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIldoZWVsIHNpemUgbWlzbWF0Y2giKQogICAgd2l0aCB3aGVlbF9wYXRoLm9wZW4oInJiIikgYXMgZjoKICAgICAgICBpZiBoYXNobGliLmZpbGVfZGlnZXN0KGYsICJzaGEyNTYiKS5oZXhkaWdlc3QoKSAhPSBleHBlY3RlZF9kaWdlc3Q6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIldoZWVsIGRpZ2VzdCBtaXNtYXRjaCIpCiAgICB3aXRoIHppcGZpbGUuWmlwRmlsZSh3aGVlbF9wYXRoKSBhcyB6OgogICAgICAgIGluZm9zID0gei5pbmZvbGlzdCgpCiAgICAgICAgaWYgbGVuKGluZm9zKSA+IDEwMDAgb3Igc3VtKGkuZmlsZV9zaXplIGZvciBpIGluIGluZm9zKSA+IDEwMCAqIDEwMjQgKiAxMDI0OgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJBcmNoaXZlIGxpbWl0cyBleGNlZWRlZCIpCiAgICAgICAgbmFtZXMgPSBzZXQoKQogICAgICAgIGZvciBpbmZvIGluIGluZm9zOgogICAgICAgICAgICBuYW1lID0gaW5mby5maWxlbmFtZQogICAgICAgICAgICBwYXRoID0gUHVyZVBvc2l4UGF0aChuYW1lKQogICAgICAgICAgICBpZiAobm90IG5hbWUgb3IgbmFtZS5zdGFydHN3aXRoKCIvIikgb3IgIlxcIiBpbiBuYW1lIG9yCiAgICAgICAgICAgICAgICAgICAgYW55KHggaW4geyIuIiwgIi4uIiwgIiJ9IGZvciB4IGluIG5hbWUucnN0cmlwKCIvIikuc3BsaXQoIi8iKSkgb3IKICAgICAgICAgICAgICAgICAgICBwYXRoLnBhcnRzWzBdIG5vdCBpbiBBTExPV0VEX1RPUCBvciBuYW1lIGluIG5hbWVzIG9yCiAgICAgICAgICAgICAgICAgICAgIi5kYXRhIiBpbiBwYXRoLnBhcnRzIG9yIG5hbWUuZW5kc3dpdGgoIi5wdGgiKSBvciBpbmZvLmZsYWdfYml0cyAmIDEpOgogICAgICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVW5zYWZlIG9yIHVuZXhwZWN0ZWQgYXJjaGl2ZSBtZW1iZXIiKQogICAgICAgICAgICBtb2RlID0gaW5mby5leHRlcm5hbF9hdHRyID4+IDE2CiAgICAgICAgICAgIGlmIG1vZGUgYW5kIHN0YXQuU19JRk1UKG1vZGUpIG5vdCBpbiB7MCwgc3RhdC5TX0lGUkVHLCBzdGF0LlNfSUZESVJ9OgogICAgICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiQXJjaGl2ZSBzcGVjaWFsIGZpbGUgZm9yYmlkZGVuIikKICAgICAgICAgICAgbmFtZXMuYWRkKG5hbWUpCiAgICAgICAgbWV0YWRhdGEgPSBlbWFpbC5wYXJzZXIuUGFyc2VyKCkucGFyc2VzdHIoei5yZWFkKERJU1QgKyAiL01FVEFEQVRBIikuZGVjb2RlKCkpCiAgICAgICAgaWYgbWV0YWRhdGFbIk5hbWUiXSAhPSAiZHVja2RiIiBvciBtZXRhZGF0YVsiVmVyc2lvbiJdICE9IFZFUlNJT046CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlBhY2thZ2UgaWRlbnRpdHkgbWlzbWF0Y2giKQogICAgICAgIGRlcGVuZGVuY2llcyA9IG1ldGFkYXRhLmdldF9hbGwoIlJlcXVpcmVzLURpc3QiLCBbXSkKICAgICAgICBhbGxvd2VkX2RlcHMgPSB7eCArICc7IGV4dHJhID09ICJhbGwiJyBmb3IgeCBpbiAoCiAgICAgICAgICAgICJpcHl0aG9uIiwgImZzc3BlYyIsICJudW1weSIsICJwYW5kYXMiLCAicHlhcnJvdyIsICJhZGJjLWRyaXZlci1tYW5hZ2VyIil9CiAgICAgICAgaWYgbm90IHNldChkZXBlbmRlbmNpZXMpLmlzc3Vic2V0KGFsbG93ZWRfZGVwcyk6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlVuZXhwZWN0ZWQgZGVwZW5kZW5jeTsgbm8gZGVwZW5kZW5jeSByZXNvbHZlciBpcyBwZXJtaXR0ZWQiKQogICAgICAgIHdoZWVsID0gZW1haWwucGFyc2VyLlBhcnNlcigpLnBhcnNlc3RyKHoucmVhZChESVNUICsgIi9XSEVFTCIpLmRlY29kZSgpKQogICAgICAgIGV4cGVjdGVkX3RhZ3MgPSB7ImNwMzEyLWNwMzEyLW1hbnlsaW51eF8yXzI2X3g4Nl82NCIsICJjcDMxMi1jcDMxMi1tYW55bGludXhfMl8yOF94ODZfNjQifQogICAgICAgIGlmIHdoZWVsWyJXaGVlbC1WZXJzaW9uIl0gIT0gIjEuMCIgb3Igc2V0KHdoZWVsLmdldF9hbGwoIlRhZyIsIFtdKSkgIT0gZXhwZWN0ZWRfdGFnczoKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiV2hlZWwgcGxhdGZvcm0gbWlzbWF0Y2giKQogICAgICAgIGxpY2Vuc2VfdGV4dCA9IHoucmVhZChESVNUICsgIi9saWNlbnNlcy9MSUNFTlNFIikuZGVjb2RlKCkKICAgICAgICBpZiAiQ29weXJpZ2h0IDIwMTgtMjAyNiBTdGljaHRpbmcgRHVja0RCIEZvdW5kYXRpb24iIG5vdCBpbiBsaWNlbnNlX3RleHQgb3IgIlBlcm1pc3Npb24gaXMgaGVyZWJ5IGdyYW50ZWQsIGZyZWUgb2YgY2hhcmdlIiBub3QgaW4gbGljZW5zZV90ZXh0OgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJFeHBlY3RlZCBNSVQgbGljZW5zZSBtaXNzaW5nIikKICAgICAgICByZWNvcmRfbmFtZSA9IERJU1QgKyAiL1JFQ09SRCIKICAgICAgICByZWNvcmRzID0gbGlzdChjc3YucmVhZGVyKGlvLlN0cmluZ0lPKHoucmVhZChyZWNvcmRfbmFtZSkuZGVjb2RlKCkpKSkKICAgICAgICByZWNvcmRlZCA9IHNldCgpCiAgICAgICAgZm9yIHJvdyBpbiByZWNvcmRzOgogICAgICAgICAgICBpZiBsZW4ocm93KSAhPSAzOgogICAgICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiSW52YWxpZCBSRUNPUkQgcm93IikKICAgICAgICAgICAgbmFtZSwgZGlnZXN0LCBzaXplID0gcm93CiAgICAgICAgICAgIGlmIG5hbWUgaW4gcmVjb3JkZWQgb3IgbmFtZSBub3QgaW4gbmFtZXM6CiAgICAgICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJJbnZhbGlkIFJFQ09SRCBtZW1iZXIiKQogICAgICAgICAgICByZWNvcmRlZC5hZGQobmFtZSkKICAgICAgICAgICAgaWYgbmFtZSA9PSByZWNvcmRfbmFtZSBhbmQgbm90IGRpZ2VzdCBhbmQgbm90IHNpemU6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBpZiBub3QgZGlnZXN0LnN0YXJ0c3dpdGgoInNoYTI1Nj0iKToKICAgICAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlVuc3VwcG9ydGVkIFJFQ09SRCBoYXNoIikKICAgICAgICAgICAgdmFsdWUgPSB6LnJlYWQobmFtZSkKICAgICAgICAgICAgd2FudCA9IGJhc2U2NC51cmxzYWZlX2I2NGVuY29kZShoYXNobGliLnNoYTI1Nih2YWx1ZSkuZGlnZXN0KCkpLmRlY29kZSgpLnJzdHJpcCgiPSIpCiAgICAgICAgICAgIGlmIGRpZ2VzdCAhPSAic2hhMjU2PSIgKyB3YW50IG9yIHNpemUgIT0gc3RyKGxlbih2YWx1ZSkpOgogICAgICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiUkVDT1JEIGludGVncml0eSBtaXNtYXRjaCIpCiAgICAgICAgaWYgcmVjb3JkZWQgIT0ge2kuZmlsZW5hbWUgZm9yIGkgaW4gaW5mb3MgaWYgbm90IGkuaXNfZGlyKCl9OgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJJbmNvbXBsZXRlIFJFQ09SRCBjb3ZlcmFnZSIpCgoKZGVmIGluc3RhbGwoc3RhZ2UpOgogICAgdmVyaWZ5X2hvc3QoKQogICAgY2hlY2tfcGF0aChST09ULCBkaXJlY3Rvcnk9VHJ1ZSkKICAgIGNoZWNrX3BhdGgoc3RhZ2UsIGRpcmVjdG9yeT1UcnVlKQogICAgaWYgc3RhZ2UucGFyZW50ICE9IFJPT1Qgb3Igbm90IHN0YWdlLm5hbWUuc3RhcnRzd2l0aCgic3RhZ2UtIik6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiU3RhZ2UgbXVzdCBiZSBhbiBleGNsdXNpdmUgY2hpbGQgb2YgdGhlIGZpeGVkIHJ1bnRpbWUgcm9vdCIpCiAgICB3aGVlbF9wYXRoID0gc3RhZ2UgLyBGSUxFTkFNRQogICAgdmVyaWZ5X2FyY2hpdmUod2hlZWxfcGF0aCkKICAgIGRlc3RpbmF0aW9uID0gUk9PVCAvIFJVTlRJTUVfTkFNRQogICAgaWYgZGVzdGluYXRpb24uZXhpc3RzKCkgb3IgZGVzdGluYXRpb24uaXNfc3ltbGluaygpOgogICAgICAgIHJhaXNlIEZpbGVFeGlzdHNFcnJvcigiUnVudGltZSBleGlzdHM7IHZlcmlmeSBpdCBpbnN0ZWFkIG9mIG92ZXJ3cml0aW5nIikKICAgICMgVmVudnMgYXJlIG5vdCByZWxvY2F0YWJsZTogaW5zdGFsbCBkaXJlY3RseSBpbiBhbiBleGNsdXNpdmUgdmVyc2lvbmVkIHBhdGguCiAgICAjIFRoZSBtaXNzaW5nIHJlY2VpcHQgZGlzdGluZ3Vpc2hlcyBhbiBpbmNvbXBsZXRlIGluc3RhbGw7IG5vIGdsb2JhbC9jdXJyZW50CiAgICAjIHBvaW50ZXIgb3IgZXhpc3RpbmcgZW52aXJvbm1lbnQgaXMgY2hhbmdlZC4KICAgIGNhbmRpZGF0ZSA9IGRlc3RpbmF0aW9uCiAgICBjYW5kaWRhdGUubWtkaXIobW9kZT0wbzcwMCkKICAgIGZvciBuYW1lIGluICgicnVudGltZS5weSIsICJsb2NrLmpzb24iLCAicmVxdWlyZW1lbnRzLmxvY2siLCAiTElDRU5TRS5kdWNrZGIiKToKICAgICAgICBzb3VyY2UgPSBzdGFnZSAvIG5hbWUKICAgICAgICBjaGVja19wYXRoKHNvdXJjZSkKICAgICAgICB3aXRoIHNvdXJjZS5vcGVuKCJyYiIpIGFzIHNyYywgKGNhbmRpZGF0ZSAvIG5hbWUpLm9wZW4oInhiIikgYXMgb3V0OgogICAgICAgICAgICBzaHV0aWwuY29weWZpbGVvYmooc3JjLCBvdXQpCiAgICAgICAgKGNhbmRpZGF0ZSAvIG5hbWUpLmNobW9kKDBvNjAwKQogICAgIyBIb3N0IHN0ZGxpYiBlbnN1cmVwaXAgc3VwcGxpZXMgcGlwOyBubyByZWdpc3RyeS9ib290c3RyYXAgbmV0d29yayBhY2Nlc3MuCiAgICBlbnZpcm9ubWVudCA9IGNhbmRpZGF0ZSAvICJ2ZW52IgogICAgdmVudi5FbnZCdWlsZGVyKHdpdGhfcGlwPVRydWUsIHN5bWxpbmtzPVRydWUpLmNyZWF0ZShlbnZpcm9ubWVudCkKICAgIHB5dGhvbiA9IGVudmlyb25tZW50IC8gImJpbiIgLyAicHl0aG9uIgogICAgc3VicHJvY2Vzcy5ydW4oW3N0cihweXRob24pLCAiLUkiLCAiLW0iLCAicGlwIiwgIi0taXNvbGF0ZWQiLCAiLS1kaXNhYmxlLXBpcC12ZXJzaW9uLWNoZWNrIiwKICAgICAgICAgICAgICAgICAgICAiaW5zdGFsbCIsICItLW5vLWluZGV4IiwgIi0tbm8tZGVwcyIsICItLW5vLWNhY2hlLWRpciIsICItLW5vLWNvbXBpbGUiLAogICAgICAgICAgICAgICAgICAgICItLXJlcXVpcmUtaGFzaGVzIiwgIi0tb25seS1iaW5hcnk9OmFsbDoiLCAiLS1maW5kLWxpbmtzIiwgc3RyKHN0YWdlKSwKICAgICAgICAgICAgICAgICAgICAiLXIiLCBzdHIoY2FuZGlkYXRlIC8gInJlcXVpcmVtZW50cy5sb2NrIildLAogICAgICAgICAgICAgICAgICAgY2FwdHVyZV9vdXRwdXQ9VHJ1ZSwgdGV4dD1UcnVlLCB0aW1lb3V0PTQwLCBjaGVjaz1UcnVlLAogICAgICAgICAgICAgICAgICAgZW52PXsiUEFUSCI6ICIvdXNyL2JpbjovYmluIiwgIkhPTUUiOiBzdHIoY2FuZGlkYXRlKSwgIlBJUF9DT05GSUdfRklMRSI6ICIvZGV2L251bGwifSkKICAgIHBpcF92ZXJzaW9uID0gc3VicHJvY2Vzcy5jaGVja19vdXRwdXQoW3N0cihweXRob24pLCAiLUkiLCAiLW0iLCAicGlwIiwgIi0tdmVyc2lvbiJdLCB0ZXh0PVRydWUsIHRpbWVvdXQ9NSkuc3RyaXAoKQogICAgIyBObyBzaGVsbCwgbm8gaW50ZXJwcmV0ZXIgc3RhcnR1cCBjdXN0b21pemF0aW9ucyBvciBQWVRIT05QQVRIIGltcG9ydHMuCiAgICByZXN1bHQgPSBzdWJwcm9jZXNzLnJ1bihbc3lzLmV4ZWN1dGFibGUsICItSSIsICItUyIsIHN0cihjYW5kaWRhdGUgLyAicnVudGltZS5weSIpLCAiLS1zbW9rZSJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgY2FwdHVyZV9vdXRwdXQ9VHJ1ZSwgdGV4dD1UcnVlLCB0aW1lb3V0PTQ1LCBjaGVjaz1UcnVlKQogICAgcmVjZWlwdCA9IGpzb24ubG9hZHMocmVzdWx0LnN0ZG91dCkKICAgIHJlY2VpcHQudXBkYXRlKHsid2hlZWxfc2hhMjU2IjogU0hBMjU2LCAid2hlZWxfYnl0ZXMiOiBTSVpFLAogICAgICAgICAgICAgICAgICAgICJpbnN0YWxsX21ldGhvZCI6ICJpc29sYXRlZC12ZW52LXBpcC1uby1pbmRleC1uby1kZXBzLXJlcXVpcmUtaGFzaGVzIiwKICAgICAgICAgICAgICAgICAgICAicGlwX2Jvb3RzdHJhcCI6IHBpcF92ZXJzaW9uLAogICAgICAgICAgICAgICAgICAgICJydW50aW1lX2RpcmVjdG9yeSI6IHN0cihkZXN0aW5hdGlvbil9KQogICAgd2l0aCAoY2FuZGlkYXRlIC8gIklOU1RBTEwtUkVDRUlQVC5qc29uIikub3BlbigieCIpIGFzIGY6CiAgICAgICAganNvbi5kdW1wKHJlY2VpcHQsIGYsIHNvcnRfa2V5cz1UcnVlLCBpbmRlbnQ9MikKICAgICAgICBmLndyaXRlKCJcbiIpCiAgICByZXR1cm4gcmVjZWlwdAoKCmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6CiAgICBpZiBsZW4oc3lzLmFyZ3YpICE9IDI6CiAgICAgICAgcmFpc2UgU3lzdGVtRXhpdCgiVXNhZ2U6IGluc3RhbGxfb2ZmbGluZS5weSBBQlNPTFVURV9TVEFHRV9ESVJFQ1RPUlkiKQogICAgcHJpbnQoanNvbi5kdW1wcyhpbnN0YWxsKFBhdGgoc3lzLmFyZ3ZbMV0pKSwgc29ydF9rZXlzPVRydWUpKQo=', 'runtime.py': 'IiIiT2ZmbGluZS1vbmx5IGJvdW5kZWQgRHVja0RCIGNvbm5lY3Rpb24gZmFjdG9yeSBhbmQgc3ludGhldGljIHZlcmlmaWNhdGlvbi4KCkludm9rZSB3aXRoIHB5dGhvbjMgLUkgLVMgPGluc3RhbGxlZD4vcnVudGltZS5weSAtLXNtb2tlLiBGb3IgYXBwbGljYXRpb24gY29kZSwKZXhwbGljaXRseSBpbXBvcnQgdGhpcyBtb2R1bGUgYW5kIHBhc3MgYXV0aG9yaXplZCBsb2NhbCByZWFkL3dyaXRlIGRpcmVjdG9yaWVzLgpUaGUgY29udGFpbmluZyBwcm9jZXNzL2phaWwgaXMgdGhlIHNlY3VyaXR5IGJvdW5kYXJ5LCBub3QgRHVja0RCIHNldHRpbmdzIGFsb25lLgoiIiIKaW1wb3J0IGFyZ3BhcnNlCmltcG9ydCBoYXNobGliCmltcG9ydCBqc29uCmltcG9ydCBvcwpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgKaW1wb3J0IHJlc291cmNlCmltcG9ydCBzeXMKaW1wb3J0IHRlbXBmaWxlCmltcG9ydCB0aW1lCgpWRVJTSU9OID0gIjEuNS42IgpST09UID0gUGF0aChfX2ZpbGVfXykucmVzb2x2ZSgpLnBhcmVudAoKCmRlZiB2YWxpZGF0ZWRfYnVkZ2V0KG92ZXJyaWRlcz1Ob25lKToKICAgICIiIlJldmlld2VkIGV4cGxpY2l0IG92ZXJyaWRlcyBtYXkgcmVkdWNlLCBuZXZlciBleGNlZWQsIGJhc2VsaW5lIGJ1ZGdldHMuIiIiCiAgICBidWRnZXQgPSB7InRocmVhZHMiOiA0LCAibWVtb3J5X2dpYiI6IDgsICJ0ZW1wX2dpYiI6IDIwfQogICAgZm9yIG5hbWUsIHZhbHVlIGluIChvdmVycmlkZXMgb3Ige30pLml0ZW1zKCk6CiAgICAgICAgaWYgbmFtZSBub3QgaW4gYnVkZ2V0IG9yIHR5cGUodmFsdWUpIGlzIG5vdCBpbnQgb3Igbm90IDEgPD0gdmFsdWUgPD0gYnVkZ2V0W25hbWVdOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJCdWRnZXQgbXVzdCBiZSBhbiBpbnRlZ2VyIHdpdGhpbiB0aGUgYXBwcm92ZWQgYmFzZWxpbmUgY2VpbGluZyIpCiAgICAgICAgYnVkZ2V0W25hbWVdID0gdmFsdWUKICAgIHJldHVybiBidWRnZXQKCgpkZWYgY29ubmVjdChhbGxvd2VkX2RpcmVjdG9yaWVzLCB0ZW1wX2RpcmVjdG9yeSwgKiwgYnVkZ2V0PU5vbmUpOgogICAgIiIiVXNlIG9ubHkgY2FsbGVyLWF1dGhvcml6ZWQgZGlyZWN0b3JpZXM7IG5ldmVyIGF1dG9tYXRpYyByZW1vdGUgYWNjZXNzLiIiIgogICAgaWYgbm90IGFsbG93ZWRfZGlyZWN0b3JpZXM6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiRXhwbGljaXQgYXV0aG9yaXplZCBsb2NhbCBkaXJlY3RvcmllcyBhcmUgcmVxdWlyZWQiKQogICAgZGlycyA9IFtdCiAgICBmb3IgdmFsdWUgaW4gYWxsb3dlZF9kaXJlY3RvcmllczoKICAgICAgICBwYXRoID0gUGF0aCh2YWx1ZSkKICAgICAgICBpZiBub3QgcGF0aC5pc19hYnNvbHV0ZSgpIG9yIG5vdCBwYXRoLmlzX2RpcigpIG9yIHBhdGguaXNfc3ltbGluaygpOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJFeHBlY3RlZCBleGlzdGluZyBhYnNvbHV0ZSBub24tc3ltbGluayBkaXJlY3RvcnkiKQogICAgICAgIGlmIHBhdGgucmVzb2x2ZSgpICE9IHBhdGg6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIkRpcmVjdG9yeSBhbmNlc3RvcnMgbXVzdCBub3QgYmUgc3ltbGlua3MiKQogICAgICAgIGRpcnMuYXBwZW5kKHN0cihwYXRoKSArIG9zLnNlcCkKICAgIHRlbXAgPSBQYXRoKHRlbXBfZGlyZWN0b3J5KQogICAgaWYgbm90IHRlbXAuaXNfYWJzb2x1dGUoKSBvciBub3QgdGVtcC5pc19kaXIoKSBvciB0ZW1wLnJlc29sdmUoKSAhPSB0ZW1wOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIkV4cGVjdGVkIGV4aXN0aW5nIGFic29sdXRlIG5vbi1zeW1saW5rIHRlbXAgZGlyZWN0b3J5IikKICAgIGlmIG5vdCBhbnkodGVtcC5pc19yZWxhdGl2ZV90byhQYXRoKGQpKSBmb3IgZCBpbiBkaXJzKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUZW1wIGRpcmVjdG9yeSBtdXN0IGxpZSBpbnNpZGUgYW4gYXV0aG9yaXplZCBkaXJlY3RvcnkiKQogICAgbGltaXRzID0gdmFsaWRhdGVkX2J1ZGdldChidWRnZXQpCiAgICBzeXMucGF0aC5pbnNlcnQoMCwgc3RyKFJPT1QgLyAidmVudiIgLyAibGliIiAvICJweXRob24zLjEyIiAvICJzaXRlLXBhY2thZ2VzIikpCiAgICBpbXBvcnQgZHVja2RiCiAgICBpZiBkdWNrZGIuX192ZXJzaW9uX18gIT0gVkVSU0lPTjoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoIlVuZXhwZWN0ZWQgRHVja0RCIHZlcnNpb24iKQogICAgY29uID0gZHVja2RiLmNvbm5lY3QoIjptZW1vcnk6IiwgY29uZmlnPXsKICAgICAgICAidGhyZWFkcyI6IHN0cihsaW1pdHNbInRocmVhZHMiXSksCiAgICAgICAgIm1lbW9yeV9saW1pdCI6IHN0cihsaW1pdHNbIm1lbW9yeV9naWIiXSkgKyAiR2lCIiwKICAgICAgICAibWF4X3RlbXBfZGlyZWN0b3J5X3NpemUiOiBzdHIobGltaXRzWyJ0ZW1wX2dpYiJdKSArICJHaUIiLAogICAgICAgICJ0ZW1wX2RpcmVjdG9yeSI6IHN0cih0ZW1wKSwKICAgICAgICAiYXV0b2luc3RhbGxfa25vd25fZXh0ZW5zaW9ucyI6ICJmYWxzZSIsCiAgICAgICAgImF1dG9sb2FkX2tub3duX2V4dGVuc2lvbnMiOiAiZmFsc2UiLAogICAgICAgICJhbGxvd19jb21tdW5pdHlfZXh0ZW5zaW9ucyI6ICJmYWxzZSIsCiAgICAgICAgImFsbG93X3Vuc2lnbmVkX2V4dGVuc2lvbnMiOiAiZmFsc2UiLAogICAgfSkKICAgICMgRHVja0RCJ3MgY29uZmlnLW1hcCBhcHBsaWNhdGlvbiBvcmRlciBpcyBub3QgUHl0aG9uIGluc2VydGlvbiBvcmRlci4KICAgICMgU2V0IHRoZSBhbGxvd2xpc3Qgd2hpbGUgY29uZmlndXJhdGlvbiBpcyBvcGVuLCB0aGVuIGRpc2FibGUgYWxsIG90aGVyCiAgICAjIGV4dGVybmFsIGFjY2VzcyBhbmQgbG9jaywgYmVmb3JlIHJldHVybmluZyBvciBleGVjdXRpbmcgYW55IHdvcmtsb2FkLgogICAgdHJ5OgogICAgICAgICMgVmVyaWZpZWQgb24gcGlubmVkIER1Y2tEQjogYWxsb3dlZF9kaXJlY3RvcmllcyBpcyBwb3N0LXN0YXJ0IG9ubHk7CiAgICAgICAgIyBiaW5kIHRoZSBsaXN0IGFzIGRhdGEsIGJlZm9yZSBkaXNhYmxpbmcgZXh0ZXJuYWwgYWNjZXNzIGFuZCBsb2NraW5nLgogICAgICAgIGNvbi5leGVjdXRlKCJTRVQgYWxsb3dlZF9kaXJlY3RvcmllcyA9ID8iLCBbZGlyc10pCiAgICAgICAgY29uLmV4ZWN1dGUoIlNFVCBlbmFibGVfZXh0ZXJuYWxfYWNjZXNzID0gZmFsc2UiKQogICAgICAgIGNvbi5leGVjdXRlKCJTRVQgbG9ja19jb25maWd1cmF0aW9uID0gdHJ1ZSIpCiAgICBleGNlcHQgQmFzZUV4Y2VwdGlvbjoKICAgICAgICBjb24uY2xvc2UoKQogICAgICAgIHJhaXNlCiAgICByZXR1cm4gY29uCgoKZGVmIHNtb2tlKCk6CiAgICAiIiJUZW4gdGhvdXNhbmQgZ2VuZXJhdGVkIHJvd3M7IG5ldmVyIG9wZW5zIGNvcnB1cyBvciByYXcgZGF0YSBmaWxlcy4iIiIKICAgIHN0YXJ0ZWQgPSB0aW1lLm1vbm90b25pYygpCiAgICBzY3JhdGNoID0gUk9PVCAvICJzY3JhdGNoIgogICAgc2NyYXRjaC5ta2Rpcihtb2RlPTBvNzAwLCBleGlzdF9vaz1UcnVlKQogICAgaWYgc2NyYXRjaC5pc19zeW1saW5rKCkgb3Igc2NyYXRjaC5yZXNvbHZlKCkgIT0gc2NyYXRjaDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJVbnNhZmUgc2NyYXRjaCBkaXJlY3RvcnkiKQogICAgd2l0aCB0ZW1wZmlsZS5UZW1wb3JhcnlEaXJlY3RvcnkocHJlZml4PSJzeW50aGV0aWMtIiwgZGlyPXNjcmF0Y2gpIGFzIHRkOgogICAgICAgIGRpcmVjdG9yeSA9IFBhdGgodGQpCiAgICAgICAgdGVtcCA9IGRpcmVjdG9yeSAvICJzcGlsbCIKICAgICAgICB0ZW1wLm1rZGlyKG1vZGU9MG83MDApCiAgICAgICAgY29uID0gY29ubmVjdChbZGlyZWN0b3J5XSwgdGVtcCkKICAgICAgICB0aW1pbmdzID0geyJzdGFydHVwX3NlY29uZHMiOiByb3VuZCh0aW1lLm1vbm90b25pYygpIC0gc3RhcnRlZCwgNil9CiAgICAgICAgdHJ5OgogICAgICAgICAgICBzdGVwID0gdGltZS5tb25vdG9uaWMoKQogICAgICAgICAgICBjb24uZXhlY3V0ZSgiQ1JFQVRFIFRBQkxFIHN5bnRoZXRpYyBBUyBTRUxFQ1QgaTo6QklHSU5UIEFTIGlkLCAiCiAgICAgICAgICAgICAgICAgICAgICAgICIoJ2NhdGVnb3J5LScgfHwgKGkgJSA4KTo6VkFSQ0hBUikgQVMgY2F0ZWdvcnksICIKICAgICAgICAgICAgICAgICAgICAgICAgIihpICUgOTcpOjpET1VCTEUgLyAxMCBBUyBhbW91bnQgRlJPTSByYW5nZSgxMDAwMCkgdChpKSIpCiAgICAgICAgICAgIHRpbWluZ3NbImdlbmVyYXRlX3NlY29uZHMiXSA9IHJvdW5kKHRpbWUubW9ub3RvbmljKCkgLSBzdGVwLCA2KQogICAgICAgICAgICBwYXJxdWV0ID0gZGlyZWN0b3J5IC8gInN5bnRoZXRpYy5wYXJxdWV0IgogICAgICAgICAgICAjIFBhcmFtZXRlciBiaW5kaW5nIGlzIHN1cHBvcnRlZCBmb3IgQ09QWSB0YXJnZXQgcGF0aHMuCiAgICAgICAgICAgIHN0ZXAgPSB0aW1lLm1vbm90b25pYygpCiAgICAgICAgICAgIGNvbi5leGVjdXRlKCJDT1BZIHN5bnRoZXRpYyBUTyA/IChGT1JNQVQgUEFSUVVFVCwgQ09NUFJFU1NJT04gWlNURCkiLCBbc3RyKHBhcnF1ZXQpXSkKICAgICAgICAgICAgdGltaW5nc1sicGFycXVldF93cml0ZV9zZWNvbmRzIl0gPSByb3VuZCh0aW1lLm1vbm90b25pYygpIC0gc3RlcCwgNikKICAgICAgICAgICAgc3RlcCA9IHRpbWUubW9ub3RvbmljKCkKICAgICAgICAgICAgZ290ID0gY29uLmV4ZWN1dGUoIlNFTEVDVCBjb3VudCgqKSwgc3VtKGlkKSwgY291bnQoRElTVElOQ1QgY2F0ZWdvcnkpIEZST00gcmVhZF9wYXJxdWV0KD8pIiwgW3N0cihwYXJxdWV0KV0pLmZldGNob25lKCkKICAgICAgICAgICAgdGltaW5nc1sicGFycXVldF9yZWFkYmFja19zZWNvbmRzIl0gPSByb3VuZCh0aW1lLm1vbm90b25pYygpIC0gc3RlcCwgNikKICAgICAgICAgICAgaWYgZ290ICE9ICgxMDAwMCwgNDk5OTUwMDAsIDgpOgogICAgICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJQYXJxdWV0IHJvdW5kdHJpcCBtaXNtYXRjaCIpCiAgICAgICAgICAgIHN0ZXAgPSB0aW1lLm1vbm90b25pYygpCiAgICAgICAgICAgIGdyb3VwcyA9IGNvbi5leGVjdXRlKCJTRUxFQ1QgY2F0ZWdvcnksIGNvdW50KCopLCByb3VuZChzdW0oYW1vdW50KSwzKSBGUk9NIHJlYWRfcGFycXVldCg/KSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJHUk9VUCBCWSBjYXRlZ29yeSBPUkRFUiBCWSBjYXRlZ29yeSIsIFtzdHIocGFycXVldCldKS5mZXRjaGFsbCgpCiAgICAgICAgICAgIHRpbWluZ3NbInBhcnF1ZXRfZ3JvdXBieV9zZWNvbmRzIl0gPSByb3VuZCh0aW1lLm1vbm90b25pYygpIC0gc3RlcCwgNikKICAgICAgICAgICAgaWYgbGVuKGdyb3VwcykgIT0gOCBvciBhbnkocm93WzFdICE9IDEyNTAgZm9yIHJvdyBpbiBncm91cHMpOgogICAgICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJTeW50aGV0aWMgZ3JvdXBpbmcgbWlzbWF0Y2giKQogICAgICAgICAgICBzZXR0aW5ncyA9IGRpY3QoY29uLmV4ZWN1dGUoIlNFTEVDVCBuYW1lLCB2YWx1ZSBGUk9NIGR1Y2tkYl9zZXR0aW5ncygpIFdIRVJFIG5hbWUgSU4gIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiKCd0aHJlYWRzJywnbWVtb3J5X2xpbWl0JywnbWF4X3RlbXBfZGlyZWN0b3J5X3NpemUnLCIKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIidhdXRvaW5zdGFsbF9rbm93bl9leHRlbnNpb25zJywnYXV0b2xvYWRfa25vd25fZXh0ZW5zaW9ucycsIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiJ2VuYWJsZV9leHRlcm5hbF9hY2Nlc3MnLCdsb2NrX2NvbmZpZ3VyYXRpb24nKSIpLmZldGNoYWxsKCkpCiAgICAgICAgICAgIHJldHVybiB7CiAgICAgICAgICAgICAgICAib2siOiBUcnVlLCAiZGF0YXNldCI6ICJzeW50aGV0aWMtb25seSIsICJkdWNrZGJfdmVyc2lvbiI6IFZFUlNJT04sCiAgICAgICAgICAgICAgICAicm93cyI6IGdvdFswXSwgInN1bV9pZCI6IGdvdFsxXSwgImRpc3RpbmN0X2NhdGVnb3JpZXMiOiBnb3RbMl0sCiAgICAgICAgICAgICAgICAicGFycXVldF9ieXRlcyI6IHBhcnF1ZXQuc3RhdCgpLnN0X3NpemUsCiAgICAgICAgICAgICAgICAicGFycXVldF9zaGEyNTYiOiBoYXNobGliLnNoYTI1NihwYXJxdWV0LnJlYWRfYnl0ZXMoKSkuaGV4ZGlnZXN0KCksCiAgICAgICAgICAgICAgICAiZ3JvdXBlZF9yZXN1bHRfc2hhMjU2IjogaGFzaGxpYi5zaGEyNTYoanNvbi5kdW1wcyhncm91cHMsIHNlcGFyYXRvcnM9KCIsIiwgIjoiKSkuZW5jb2RlKCkpLmhleGRpZ2VzdCgpLAogICAgICAgICAgICAgICAgImdyb3VwX2NvdW50IjogbGVuKGdyb3VwcyksICJ0aW1pbmdzIjogdGltaW5ncywKICAgICAgICAgICAgICAgICJlbGFwc2VkX3NlY29uZHMiOiByb3VuZCh0aW1lLm1vbm90b25pYygpIC0gc3RhcnRlZCwgNiksCiAgICAgICAgICAgICAgICAibWF4X3Jzc19raWIiOiByZXNvdXJjZS5nZXRydXNhZ2UocmVzb3VyY2UuUlVTQUdFX1NFTEYpLnJ1X21heHJzcywKICAgICAgICAgICAgICAgICJzZXR0aW5ncyI6IHNldHRpbmdzLAogICAgICAgICAgICAgICAgIm5vdGUiOiAiU2luZ2xlIHN5bnRoZXRpYyB2ZXJpZmljYXRpb24gdHJpYWwsIG5vdCBhIHRocm91Z2hwdXQvc3BlZWR1cC9vcHRpbXVtIGNsYWltLiBCdWZmZXIvc3BpbGwvdGhyZWFkIHNldHRpbmdzIGFyZSBub3QgT1MtbGV2ZWwgdG90YWwgcHJvY2VzcyBsaW1pdHMuIiwKICAgICAgICAgICAgfQogICAgICAgIGZpbmFsbHk6CiAgICAgICAgICAgIGNvbi5jbG9zZSgpCgoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIHBhcnNlciA9IGFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyKCkKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tc21va2UiLCBhY3Rpb249InN0b3JlX3RydWUiLCByZXF1aXJlZD1UcnVlKQogICAgcGFyc2VyLnBhcnNlX2FyZ3MoKQogICAgcHJpbnQoanNvbi5kdW1wcyhzbW9rZSgpLCBzb3J0X2tleXM9VHJ1ZSkpCg==', 'lock.json': 'ewogICJzY2hlbWFfdmVyc2lvbiI6IDEsCiAgIm5hbWUiOiAiZHVja2RiIiwKICAidmVyc2lvbiI6ICIxLjUuNiIsCiAgImZpbGVuYW1lIjogImR1Y2tkYi0xLjUuNi1jcDMxMi1jcDMxMi1tYW55bGludXhfMl8yNl94ODZfNjQubWFueWxpbnV4XzJfMjhfeDg2XzY0LndobCIsCiAgInVybCI6ICJodHRwczovL2ZpbGVzLnB5dGhvbmhvc3RlZC5vcmcvcGFja2FnZXMvNGMvOTkvYmU3NWM3ODhhNDkyZjhkNzdiN2ExY2RjMWIxOTkzOWFlN2JlMDAwN2YyMDI4NjkxYWQzNzFhMWEzM2VlL2R1Y2tkYi0xLjUuNi1jcDMxMi1jcDMxMi1tYW55bGludXhfMl8yNl94ODZfNjQubWFueWxpbnV4XzJfMjhfeDg2XzY0LndobCIsCiAgInNoYTI1NiI6ICJiYzk2MTllZDdkNGZmYTExN2I1MTU1ZDg0YjQ0Nzk0MzY2YmI2NjM1MTc4ZDc4ZWQ1ZTEzYTYwMjQ4NDVjNzU3IiwKICAic2l6ZV9ieXRlcyI6IDIxNTY4MDg3LAogICJ1bmNvbXByZXNzZWRfc2l6ZV9ieXRlcyI6IDYxMDQzNjg2LAogICJsaWNlbnNlIjogIk1JVCIsCiAgImxpY2Vuc2VfcGF0aCI6ICJkdWNrZGItMS41LjYuZGlzdC1pbmZvL2xpY2Vuc2VzL0xJQ0VOU0UiLAogICJkZXBlbmRlbmNpZXMiOiBbXSwKICAiZXh0cmFzIjogW10sCiAgImV4Y2x1ZGVkX29wdGlvbmFsX2RlcGVuZGVuY2llcyI6IFsiaXB5dGhvbiIsICJmc3NwZWMiLCAibnVtcHkiLCAicGFuZGFzIiwgInB5YXJyb3ciLCAiYWRiYy1kcml2ZXItbWFuYWdlciJdLAogICJweXRob25faW1wbGVtZW50YXRpb24iOiAiQ1B5dGhvbiIsCiAgInB5dGhvbl92ZXJzaW9uIjogIjMuMTIiLAogICJhcmNoaXRlY3R1cmUiOiAieDg2XzY0IiwKICAibWluaW11bV9nbGliYyI6ICIyLjI2IiwKICAibWV0YWRhdGFfc291cmNlIjogImh0dHBzOi8vcHlwaS5vcmcvcHlwaS9kdWNrZGIvMS41LjYvanNvbiIsCiAgInBhY2thZ2Vfc291cmNlIjogImh0dHBzOi8vcHlwaS5vcmcvcHJvamVjdC9kdWNrZGIvMS41LjYvIiwKICAidmVyaWZpY2F0aW9uX3J1biI6ICJodHRwczovL3dpbmRtaWxsLmFsZG91cy5pbmZvL3J1bi8wMWExN2Y3MS03YjdjLTMyMzQtZWUyNS04OTU5NDg4MDU2Nzk/d29ya3NwYWNlPW9mZm1lbnUiLAogICJ2ZXJpZmllZF9hdF91dGMiOiAiMjAyNi0xMC0yN1QyMjoxODoyN1oiLAogICJweXBpX3VwbG9hZF90aW1lX3V0YyI6ICIyMDI2LTA5LTI4VDEzOjM3OjU4LjE5MTAzNFoiLAogICJweXBpX3JlcG9ydGVkX3B1Ymxpc2hlcl9jb21taXQiOiAiODAyYTM0NWJiNjI3NDM1ZDJhMDVkNjNjYjc0NDU0ZmE5OGI2MGI1ZSIsCiAgInB1Ymxpc2hlcl9hdHRlc3RhdGlvbl9ub3RlIjogIlB5UEkgcmVwb3J0cyBUcnVzdGVkIFB1Ymxpc2hpbmc7IG5vIGluZGVwZW5kZW50IFNpZ3N0b3JlIHZlcmlmaWNhdGlvbiBjbGFpbWVkLiIKfQo=', 'requirements.lock': 'IyBDUHl0aG9uIDMuMTIsIExpbnV4IHg4Nl82NCwgZ2xpYmMgPj0yLjI2OyBubyBleHRyYXMgb3IgdGhpcmQtcGFydHkgZGVwZW5kZW5jaWVzLgpkdWNrZGI9PTEuNS42IC0taGFzaD1zaGEyNTY6YmM5NjE5ZWQ3ZDRmZmExMTdiNTE1NWQ4NGI0NDc5NDM2NmJiNjYzNTE3OGQ3OGVkNWUxM2E2MDI0ODQ1Yzc1Nwo=', 'LICENSE.duckdb': 'Q29weXJpZ2h0IDIwMTgtMjAyNiBTdGljaHRpbmcgRHVja0RCIEZvdW5kYXRpb24KClBlcm1pc3Npb24gaXMgaGVyZWJ5IGdyYW50ZWQsIGZyZWUgb2YgY2hhcmdlLCB0byBhbnkgcGVyc29uIG9idGFpbmluZyBhIGNvcHkgb2YgdGhpcyBzb2Z0d2FyZSBhbmQgYXNzb2NpYXRlZCBkb2N1bWVudGF0aW9uIGZpbGVzICh0aGUgIlNvZnR3YXJlIiksIHRvIGRlYWwgaW4gdGhlIFNvZnR3YXJlIHdpdGhvdXQgcmVzdHJpY3Rpb24sIGluY2x1ZGluZyB3aXRob3V0IGxpbWl0YXRpb24gdGhlIHJpZ2h0cyB0byB1c2UsIGNvcHksIG1vZGlmeSwgbWVyZ2UsIHB1Ymxpc2gsIGRpc3RyaWJ1dGUsIHN1YmxpY2Vuc2UsIGFuZC9vciBzZWxsIGNvcGllcyBvZiB0aGUgU29mdHdhcmUsIGFuZCB0byBwZXJtaXQgcGVyc29ucyB0byB3aG9tIHRoZSBTb2Z0d2FyZSBpcyBmdXJuaXNoZWQgdG8gZG8gc28sIHN1YmplY3QgdG8gdGhlIGZvbGxvd2luZyBjb25kaXRpb25zOgoKVGhlIGFib3ZlIGNvcHlyaWdodCBub3RpY2UgYW5kIHRoaXMgcGVybWlzc2lvbiBub3RpY2Ugc2hhbGwgYmUgaW5jbHVkZWQgaW4gYWxsIGNvcGllcyBvciBzdWJzdGFudGlhbCBwb3J0aW9ucyBvZiB0aGUgU29mdHdhcmUuCgpUSEUgU09GVFdBUkUgSVMgUFJPVklERUQgIkFTIElTIiwgV0lUSE9VVCBXQVJSQU5UWSBPRiBBTlkgS0lORCwgRVhQUkVTUyBPUiBJTVBMSUVELCBJTkNMVURJTkcgQlVUIE5PVCBMSU1JVEVEIFRPIFRIRSBXQVJSQU5USUVTIE9GIE1FUkNIQU5UQUJJTElUWSwgRklUTkVTUyBGT1IgQSBQQVJUSUNVTEFSIFBVUlBPU0UgQU5EIE5PTklORlJJTkdFTUVOVC4gSU4gTk8gRVZFTlQgU0hBTEwgVEhFIEFVVEhPUlMgT1IgQ09QWVJJR0hUIEhPTERFUlMgQkUgTElBQkxFIEZPUiBBTlkgQ0xBSU0sIERBTUFHRVMgT1IgT1RIRVIgTElBQklMSVRZLCBXSEVUSEVSIElOIEFOIEFDVElPTiBPRiBDT05UUkFDVCwgVE9SVCBPUiBPVEhFUldJU0UsIEFSSVNJTkcgRlJPTSwgT1VUIE9GIE9SIElOIENPTk5FQ1RJT04gV0lUSCBUSEUgU09GVFdBUkUgT1IgVEhFIFVTRSBPUiBPVEhFUiBERUFMSU5HUyBJTiBUSEUgU09GVFdBUkUuCg=='}
LOCK = {'schema_version': 1, 'name': 'duckdb', 'version': '1.5.6', 'filename': 'duckdb-1.5.6-cp312-cp312-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl', 'url': 'https://files.pythonhosted.org/packages/4c/99/be75c788a492f8d77b7a1cdc1b19939ae7be0007f2028691ad371a1a33ee/duckdb-1.5.6-cp312-cp312-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl', 'sha256': 'bc9619ed7d4ffa117b5155d84b44794366bb6635178d78ed5e13a6024845c757', 'size_bytes': 21568087, 'uncompressed_size_bytes': 61043686, 'license': 'MIT', 'license_path': 'duckdb-1.5.6.dist-info/licenses/LICENSE', 'dependencies': [], 'extras': [], 'excluded_optional_dependencies': ['ipython', 'fsspec', 'numpy', 'pandas', 'pyarrow', 'adbc-driver-manager'], 'python_implementation': 'CPython', 'python_version': '3.12', 'architecture': 'x86_64', 'minimum_glibc': '2.26', 'metadata_source': 'https://pypi.org/pypi/duckdb/1.5.6/json', 'package_source': 'https://pypi.org/project/duckdb/1.5.6/', 'verification_run': 'https://windmill.aldous.info/run/01a17f71-7b7c-3234-ee25-895948805679?workspace=offmenu', 'verified_at_utc': '2026-10-27T22:18:27Z', 'pypi_upload_time_utc': '2026-09-28T13:37:58.191034Z', 'pypi_reported_publisher_commit': '802a345bb627435d2a05d63cb74454fa98b60b5e', 'publisher_attestation_note': 'PyPI reports Trusted Publishing; no independent Sigstore verification claimed.'}

import tempfile
import urllib.request
import urllib.parse
import uuid

PACKAGE_URL = LOCK["url"]

def _get(url, limit):
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError("HTTPS required")
    with urllib.request.urlopen(url, timeout=60) as response:
        parsed = urllib.parse.urlparse(response.url)
        if parsed.scheme != "https" or parsed.hostname not in {"pypi.org", "files.pythonhosted.org"}:
            raise ValueError("Unexpected registry redirect")
        blob = response.read(limit+1)
    if len(blob)>limit:
        raise ValueError("Registry response exceeds bound")
    return blob


def _verified_wheel():
    metadata = json.loads(_get("https://pypi.org/pypi/duckdb/1.5.6/json", 2*1024*1024))
    selected = next(x for x in metadata["urls"] if x["filename"] == FILENAME)
    if selected["yanked"] or selected["size"] != SIZE or selected["url"] != PACKAGE_URL or selected["digests"]["sha256"] != SHA256:
        raise ValueError("Official registry metadata no longer agrees with reviewed pin")
    blob = _get(PACKAGE_URL, SIZE)
    if len(blob)!=SIZE or hashlib.sha256(blob).hexdigest()!=SHA256:
        raise ValueError("Downloaded artifact integrity mismatch")
    # Use exactly the same reviewed archive validator on the worker before transfer.
    namespace = {"__name__": "duckdb_offline_validator"}
    exec(base64.b64decode(FILES["install_offline.py"]), namespace)
    with tempfile.TemporaryDirectory(prefix="offmenu-duckdb-") as td:
        p = Path(td)/FILENAME
        p.write_bytes(blob)
        namespace["verify_archive"](p)
    return blob


def main(action: str = "verify_registry", stage_id: str = "", max_chunks: int = 128):
    # verify_registry is read-only with respect to Foo and never loads the SSH secret.
    if action not in {"verify_registry", "prepare", "transfer", "status", "install"}:
        raise ValueError("Unsupported action")
    if type(max_chunks) is not int or not 1 <= max_chunks <= 600:
        raise ValueError("max_chunks must be 1..600")
    blob = None
    if action in {"verify_registry", "transfer"}:
        blob = _verified_wheel()
    if action == "verify_registry":
        return {"ok":True,"sha256":SHA256,"bytes":len(blob),"archive_verified":True,"foo_writes":False}
    if action == "prepare":
        if stage_id:
            raise ValueError("prepare generates an exclusive random stage_id")
        stage_id = uuid.uuid4().hex
    stage_path(stage_id)
    client = None
    secret = None
    private_key = None
    try:
        client = paramiko.SSHClient()
        _pin(client)
        secret = wmill.get_variable(SECRET_PATH)
        with io.StringIO(secret) as key_stream:
            private_key = paramiko.Ed25519Key.from_private_key(key_stream)
        secret = None
        client.connect(HOST, port=PORT, username=USER, pkey=private_key,
                       allow_agent=False, look_for_keys=False,
                       timeout=5, banner_timeout=5, auth_timeout=5, channel_timeout=5)
        private_key = None
        transport = client.get_transport()
        if transport is None or not transport.is_authenticated():
            raise ConnectionError("Unauthenticated transport")
        def remote(cmd):
            payload = json.dumps({"command":cmd}, ensure_ascii=True).encode()
            if len(payload)>MAX_REQUEST_BYTES:
                raise ValueError("Request bound exceeded")
            channel = transport.open_session(timeout=5)
            try:
                channel.settimeout(5)
                channel.exec_command("offmenu-exec-v1")
                channel.sendall(payload)
                channel.shutdown_write()
                result = _drain(channel, 60)
                if result["exit_code"] or any(result["truncated"].values()):
                    return {"ok":False,"stage_id":stage_id,"remote":result}
                return json.loads(result["stdout"])
            finally:
                channel.close()
        if action=="prepare":
            return remote(prepare_command(stage_id,{name:base64.b64decode(value) for name,value in FILES.items()}))
        if action=="status":
            return remote(status_command(stage_id))
        if action=="install":
            return remote(install_command(stage_id))
        status = remote(status_command(stage_id))
        if status.get("ok") is False:
            return status
        offset = status["offset"]
        if type(offset) is not int or offset<0 or offset>SIZE or (offset != SIZE and offset%CHUNK_SIZE):
            raise ValueError("Invalid remote offset; incomplete chunk requires manual diagnosis")
        initial = offset
        for _ in range(max_chunks):
            if offset == SIZE:
                break
            chunk = blob[offset:offset+CHUNK_SIZE]
            result = remote(chunk_command(stage_id,offset,chunk))
            if result.get("ok") is False:
                return result
            if result["offset"] != offset+len(chunk):
                raise ValueError("Unexpected receiver offset")
            offset = result["offset"]
        return {"ok":True,"stage_id":stage_id,"offset":offset,"transferred_this_run":offset-initial,
                "total_bytes":SIZE,"transfer_complete":offset==SIZE,"installed":False,"sha256_pin":SHA256}
    except Exception as error:
        # No credential, payload, secret-provider exception text or traceback output.
        return {"ok":False,"stage_id":stage_id,"error_class":type(error).__name__[:64]}
    finally:
        secret = None
        private_key = None
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
