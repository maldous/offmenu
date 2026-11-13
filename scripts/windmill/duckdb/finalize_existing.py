"""Finalize the known existing venv after reviewed runtime-only correction.

Never reinstalls or overwrites files. Verifies the original pinned wheel and every
installed wheel file (except pip-generated RECORD), the exact corrected runtime,
then executes a real bounded synthetic smoke before creating the sole receipt.
Run only through the designated Foo writer, with the existing stage directory.
"""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

ROOT = Path("/offmenu/data/.offmenu-platform/duckdb")
DEST = ROOT / "1.5.6-bc9619ed7d4f"
FILENAME = "duckdb-1.5.6-cp312-cp312-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl"
WHEEL_SHA = "bc9619ed7d4ffa117b5155d84b44794366bb6635178d78ed5e13a6024845c757"
RUNTIME_SHA = "a894d076d7adc6d349a229d417094f7fc7a5b08aab43f83049ed1e7f3662abd0"
SIZE = 21568087


def file_sha(path):
    if path.resolve() != path:
        raise ValueError("Symlink path forbidden")
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
        raise ValueError("Expected singly linked regular file")
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main(stage):
    if stage.parent != ROOT or not stage.name.startswith("stage-") or stage.resolve() != stage:
        raise ValueError("Unexpected stage")
    if DEST.resolve() != DEST or not DEST.is_dir():
        raise ValueError("Unexpected existing runtime")
    receipt_file = DEST / "INSTALL-RECEIPT.json"
    if receipt_file.exists() or receipt_file.is_symlink():
        raise FileExistsError("Never overwrite an installation receipt")
    wheel = stage / FILENAME
    if wheel.stat().st_size != SIZE or file_sha(wheel) != WHEEL_SHA:
        raise ValueError("Pinned wheel verification failed")
    if file_sha(DEST / "runtime.py") != RUNTIME_SHA:
        raise ValueError("Corrected runtime hash mismatch")
    site = DEST / "venv/lib/python3.12/site-packages"
    count = 0
    with zipfile.ZipFile(wheel) as z:
        for name, digest, size in csv.reader(io.StringIO(z.read("duckdb-1.5.6.dist-info/RECORD").decode())):
            if name == "duckdb-1.5.6.dist-info/RECORD":
                continue  # pip legitimately rewrites RECORD to include INSTALLER etc.
            # Exact official wheel hash above authenticates these RECORD paths.
            target = site / name
            if not target.is_relative_to(site) or ".." in Path(name).parts or Path(name).is_absolute():
                raise ValueError("Unsafe RECORD path")
            got = base64.urlsafe_b64encode(bytes.fromhex(file_sha(target))).decode().rstrip("=")
            if digest != "sha256=" + got or target.stat().st_size != int(size):
                raise ValueError("Installed package differs from pinned wheel")
            count += 1
    result = subprocess.run([sys.executable, "-I", "-S", str(DEST / "runtime.py"), "--smoke"],
                            capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Synthetic smoke failed: " + result.stderr[-8000:])
    receipt = json.loads(result.stdout)
    if receipt.get("ok") is not True or receipt.get("rows") != 10000 or receipt.get("group_count") != 8:
        raise ValueError("Synthetic smoke did not establish expected results")
    settings = receipt["settings"]
    expected = {"threads":"4", "autoinstall_known_extensions":"false",
                "autoload_known_extensions":"false", "enable_external_access":"false",
                "lock_configuration":"true"}
    if any(str(settings.get(k)).lower() != v for k, v in expected.items()):
        raise ValueError("Expected final locked restrictions were not effective")
    pip_version = subprocess.check_output([str(DEST / "venv/bin/python"), "-I", "-m", "pip", "--version"],
                                          text=True, timeout=5).strip()
    receipt.update({"wheel_sha256": WHEEL_SHA, "wheel_bytes": SIZE,
                    "runtime_source_sha256": RUNTIME_SHA, "verified_installed_wheel_files": count,
                    "install_method": "isolated-venv-pip-no-index-no-deps-require-hashes",
                    "pip_bootstrap": pip_version, "runtime_directory": str(DEST),
                    "correction": "Allowlist configured before disabling external access; final restrictions unchanged"})
    with receipt_file.open("x") as f:
        json.dump(receipt, f, sort_keys=True, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: finalize_existing.py ABSOLUTE_EXISTING_STAGE")
    main(Path(sys.argv[1]))
