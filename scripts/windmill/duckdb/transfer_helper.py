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
