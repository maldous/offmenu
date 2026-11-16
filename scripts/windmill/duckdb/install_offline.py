"""Strict single-wheel offline installer: isolated venv and hash-required pip.

Only install the reviewed pinned wheel into a fresh versioned private directory.
Never modifies a system interpreter or existing runtime. Use via the transfer
helper after the sole Foo writer has authorized the host mutation.
"""
import base64
import csv
import email.parser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import zipfile
import venv

VERSION = "1.5.6"
SHA256 = "bc9619ed7d4ffa117b5155d84b44794366bb6635178d78ed5e13a6024845c757"
SIZE = 21568087
FILENAME = "duckdb-1.5.6-cp312-cp312-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl"
ROOT = Path("/offmenu/data/.offmenu-platform/duckdb")
RUNTIME_NAME = "1.5.6-bc9619ed7d4f"
DIST = "duckdb-1.5.6.dist-info"
ALLOWED_TOP = {"duckdb", "_duckdb-stubs", "adbc_driver_duckdb", DIST,
               "_duckdb.cpython-312-x86_64-linux-gnu.so"}


def check_path(path, directory=False):
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("Unsafe path or symlink ancestor")
    st = path.lstat()
    if directory:
        if not stat.S_ISDIR(st.st_mode):
            raise ValueError("Not a directory")
    elif not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise ValueError("Not a singly linked regular file")
    return st


def verify_host():
    libc, version = platform.libc_ver()
    if platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 12):
        raise RuntimeError("CPython 3.12 required")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("Linux x86_64 required")
    if libc != "glibc" or tuple(map(int, version.split(".")[:2])) < (2, 26):
        raise RuntimeError("glibc >= 2.26 required")


def verify_archive(wheel_path, expected_digest=SHA256, expected_size=SIZE):
    st = check_path(wheel_path)
    if st.st_size != expected_size:
        raise ValueError("Wheel size mismatch")
    with wheel_path.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != expected_digest:
            raise ValueError("Wheel digest mismatch")
    with zipfile.ZipFile(wheel_path) as z:
        infos = z.infolist()
        if len(infos) > 1000 or sum(i.file_size for i in infos) > 100 * 1024 * 1024:
            raise ValueError("Archive limits exceeded")
        names = set()
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if (not name or name.startswith("/") or "\\" in name or
                    any(x in {".", "..", ""} for x in name.rstrip("/").split("/")) or
                    path.parts[0] not in ALLOWED_TOP or name in names or
                    ".data" in path.parts or name.endswith(".pth") or info.flag_bits & 1):
                raise ValueError("Unsafe or unexpected archive member")
            mode = info.external_attr >> 16
            if mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ValueError("Archive special file forbidden")
            names.add(name)
        metadata = email.parser.Parser().parsestr(z.read(DIST + "/METADATA").decode())
        if metadata["Name"] != "duckdb" or metadata["Version"] != VERSION:
            raise ValueError("Package identity mismatch")
        dependencies = metadata.get_all("Requires-Dist", [])
        allowed_deps = {x + '; extra == "all"' for x in (
            "ipython", "fsspec", "numpy", "pandas", "pyarrow", "adbc-driver-manager")}
        if not set(dependencies).issubset(allowed_deps):
            raise ValueError("Unexpected dependency; no dependency resolver is permitted")
        wheel = email.parser.Parser().parsestr(z.read(DIST + "/WHEEL").decode())
        expected_tags = {"cp312-cp312-manylinux_2_26_x86_64", "cp312-cp312-manylinux_2_28_x86_64"}
        if wheel["Wheel-Version"] != "1.0" or set(wheel.get_all("Tag", [])) != expected_tags:
            raise ValueError("Wheel platform mismatch")
        license_text = z.read(DIST + "/licenses/LICENSE").decode()
        if "Copyright 2018-2026 Stichting DuckDB Foundation" not in license_text or "Permission is hereby granted, free of charge" not in license_text:
            raise ValueError("Expected MIT license missing")
        record_name = DIST + "/RECORD"
        records = list(csv.reader(io.StringIO(z.read(record_name).decode())))
        recorded = set()
        for row in records:
            if len(row) != 3:
                raise ValueError("Invalid RECORD row")
            name, digest, size = row
            if name in recorded or name not in names:
                raise ValueError("Invalid RECORD member")
            recorded.add(name)
            if name == record_name and not digest and not size:
                continue
            if not digest.startswith("sha256="):
                raise ValueError("Unsupported RECORD hash")
            value = z.read(name)
            want = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode().rstrip("=")
            if digest != "sha256=" + want or size != str(len(value)):
                raise ValueError("RECORD integrity mismatch")
        if recorded != {i.filename for i in infos if not i.is_dir()}:
            raise ValueError("Incomplete RECORD coverage")


def install(stage):
    verify_host()
    check_path(ROOT, directory=True)
    check_path(stage, directory=True)
    if stage.parent != ROOT or not stage.name.startswith("stage-"):
        raise ValueError("Stage must be an exclusive child of the fixed runtime root")
    wheel_path = stage / FILENAME
    verify_archive(wheel_path)
    destination = ROOT / RUNTIME_NAME
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Runtime exists; verify it instead of overwriting")
    # Venvs are not relocatable: install directly in an exclusive versioned path.
    # The missing receipt distinguishes an incomplete install; no global/current
    # pointer or existing environment is changed.
    candidate = destination
    candidate.mkdir(mode=0o700)
    for name in ("runtime.py", "lock.json", "requirements.lock", "LICENSE.duckdb"):
        source = stage / name
        check_path(source)
        with source.open("rb") as src, (candidate / name).open("xb") as out:
            shutil.copyfileobj(src, out)
        (candidate / name).chmod(0o600)
    # Host stdlib ensurepip supplies pip; no registry/bootstrap network access.
    environment = candidate / "venv"
    venv.EnvBuilder(with_pip=True, symlinks=True).create(environment)
    python = environment / "bin" / "python"
    subprocess.run([str(python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
                    "install", "--no-index", "--no-deps", "--no-cache-dir", "--no-compile",
                    "--require-hashes", "--only-binary=:all:", "--find-links", str(stage),
                    "-r", str(candidate / "requirements.lock")],
                   capture_output=True, text=True, timeout=40, check=True,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(candidate), "PIP_CONFIG_FILE": "/dev/null"})
    pip_version = subprocess.check_output([str(python), "-I", "-m", "pip", "--version"], text=True, timeout=5).strip()
    # No shell, no interpreter startup customizations or PYTHONPATH imports.
    result = subprocess.run([sys.executable, "-I", "-S", str(candidate / "runtime.py"), "--smoke"],
                            capture_output=True, text=True, timeout=45, check=True)
    receipt = json.loads(result.stdout)
    receipt.update({"wheel_sha256": SHA256, "wheel_bytes": SIZE,
                    "install_method": "isolated-venv-pip-no-index-no-deps-require-hashes",
                    "pip_bootstrap": pip_version,
                    "runtime_directory": str(destination)})
    with (candidate / "INSTALL-RECEIPT.json").open("x") as f:
        json.dump(receipt, f, sort_keys=True, indent=2)
        f.write("\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: install_offline.py ABSOLUTE_STAGE_DIRECTORY")
    print(json.dumps(install(Path(sys.argv[1])), sort_keys=True))
