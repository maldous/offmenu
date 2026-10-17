#!/usr/bin/env python3
"""User-operated setup; default preflight has no network or filesystem mutations."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

REPO = "maldous/offmenu"
RUNNER_USER = "offmenu-runner"
RUNNER_HOME = Path("/srv/offmenu-runner")
RUNNER_DIR = RUNNER_HOME / "actions-runner"
DATA_ROOT = Path("/srv/offmenu-refresh")
CACHE_VIEW = DATA_ROOT / "cache"
OUTPUT_ROOT = DATA_ROOT / "outputs"
SERVICE = "offmenu-runner.service"
VERSION = "2.338.0"
# Verified against official GitHub release asset digests on 2026-10-17.
ASSETS = {
    "x86_64": ("x64", "af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32"),
    "aarch64": ("arm64", "628b4a7258487b80c1d3c221095a7ded349f5ae0175fd3dfab708d07428f041b"),
    "arm64": ("arm64", "628b4a7258487b80c1d3c221095a7ded349f5ae0175fd3dfab708d07428f041b"),
}


class SetupError(Exception):
    pass


def fail(code):
    raise SetupError(code)


def os_release():
    result = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key in {"ID", "VERSION_ID"}:
                value = value.strip('"\'')
                if re.fullmatch(r"[A-Za-z0-9._-]{1,40}", value):
                    result[key] = value
    except OSError:
        pass
    return result


def systemd_version():
    try:
        output = subprocess.run(["systemctl", "--version"], capture_output=True,
                                text=True, timeout=5, check=True).stdout
        match = re.match(r"systemd (\d+)", output)
        return int(match.group(1)) if match else None
    except (OSError, subprocess.SubprocessError):
        return None


def account():
    try:
        return pwd.getpwnam(RUNNER_USER)
    except KeyError:
        return None


def account_valid(entry):
    if not entry:
        return False
    # No supplementary groups at all; no inherited sudo/docker/group access.
    return (entry.pw_uid != 0 and entry.pw_dir == str(RUNNER_HOME)
            and set(os.getgrouplist(RUNNER_USER, entry.pw_gid)) == {entry.pw_gid}
            and grp.getgrgid(entry.pw_gid).gr_name == RUNNER_USER)


def visible_presence(path, directory=False):
    try:
        return path.is_dir() if directory else path.is_file()
    except PermissionError:
        return None


def preflight():
    release = os_release()
    entry = account()
    version = systemd_version()
    supported_os = platform.system() == "Linux"
    return {
        "schemaVersion": 1,
        "reportKind": "offmenu-runner-host-preflight",
        "intendedHostAlias": "foo",
        "hostIdentityVerified": False,
        "repository": REPO,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "linux": supported_os,
        "distribution": release.get("ID", "unknown"),
        "distributionVersion": release.get("VERSION_ID", "unknown"),
        "architecture": platform.machine() if platform.machine() in ASSETS else "unsupported",
        "pythonVersion": ".".join(map(str, sys.version_info[:3])),
        "pythonSupported": sys.version_info >= (3, 10),
        "systemdVersion": version,
        "systemdSupported": version is not None and version >= 247,
        "tools": {name: shutil.which(name) is not None for name in ("curl", "git", "systemctl", "sha256sum")},
        "dedicatedAccountExists": entry is not None,
        "dedicatedAccountValid": account_valid(entry),
        "runnerInstalled": visible_presence(RUNNER_DIR / "config.sh"),
        "runnerRegistrationPresent": visible_presence(RUNNER_DIR / ".runner"),
        "serviceUnitPresent": visible_presence(Path("/etc/systemd/system", SERVICE)),
        "cacheViewPresent": visible_presence(CACHE_VIEW, directory=True),
        "outputDirectoryPresent": visible_presence(OUTPUT_ROOT, directory=True),
        "registrationOrServiceVerified": False,
    }


def require_host():
    report = preflight()
    if not report["linux"] or report["architecture"] == "unsupported":
        fail("unsupported-os-or-architecture")
    if not report["pythonSupported"] or not report["systemdSupported"]:
        fail("requires-python-3.10-and-systemd-247")
    if not all(report["tools"].values()):
        fail("required-host-tool-missing")
    distro = report["distribution"]
    try:
        major = int(report["distributionVersion"].split(".")[0])
    except ValueError:
        fail("unrecognized-distribution-version")
    minimum = {"ubuntu": 20, "debian": 10, "rhel": 8, "centos": 8,
               "ol": 8, "fedora": 29, "linuxmint": 20,
               "opensuse-leap": 15, "sles": 15}.get(distro)
    if minimum is None or major < minimum:
        fail("distribution-requires-manual-support-review")


def require_runner_identity():
    entry = account()
    if not account_valid(entry) or os.getuid() != entry.pw_uid or os.geteuid() != entry.pw_uid:
        fail("run-this-stage-as-dedicated-offmenu-runner-account")
    if os.environ.get("HOME") != str(RUNNER_HOME):
        fail("dedicated-runner-home-required")
    for p in (RUNNER_HOME,):
        info = p.lstat()
        if p.is_symlink() or info.st_uid != entry.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
            fail("runner-home-owner-or-mode-invalid")


def minimal_env():
    return {"HOME": str(RUNNER_HOME), "USER": RUNNER_USER, "LOGNAME": RUNNER_USER,
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}


def cache_source(value):
    path = Path(value)
    # These restrictions avoid shell and systemd unit expansion/injection.
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", value) or ".." in path.parts:
        fail("cache-root-must-be-an-absolute-simple-path")
    if not path.is_dir() or path.resolve() != path:
        fail("cache-root-must-be-an-existing-canonical-directory")
    if path in (Path("/"), Path("/home"), Path("/root"), Path("/srv"), Path("/etc"), Path("/var")):
        fail("cache-root-is-too-broad")
    if path == DATA_ROOT or path == RUNNER_HOME or DATA_ROOT in path.parents or RUNNER_HOME in path.parents:
        fail("cache-root-must-be-separate-from-runner-state-and-outputs")
    return path


def service_text(source):
    return f"""[Unit]
Description=OffMenu repository GitHub Actions runner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={RUNNER_USER}
Group={RUNNER_USER}
WorkingDirectory={RUNNER_DIR}
ExecStart={RUNNER_DIR}/runsvc.sh
Restart=on-failure
RestartSec=10
KillMode=control-group
TimeoutStopSec=60
UMask=0077
Environment=HOME={RUNNER_HOME}
Environment=PATH=/usr/bin:/bin
Environment=PYTHONDONTWRITEBYTECODE=1
NoNewPrivileges=yes
CapabilityBoundingSet=
AmbientCapabilities=
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=tmpfs
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
InaccessiblePaths=-/run/docker.sock -/var/run/docker.sock -/run/podman -/run/containerd
BindReadOnlyPaths={source}:{CACHE_VIEW}
ReadWritePaths={RUNNER_HOME} {OUTPUT_ROOT}
TasksMax=256
MemoryMax=3G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
"""


def validate_privileged_destination(path, expected=None, directory=False, mode=None):
    # Existing root-owned ancestors must not be symlinks or writable by others.
    for ancestor in reversed(path.parents):
        if ancestor.exists() or ancestor.is_symlink():
            info = ancestor.lstat()
            if ancestor.is_symlink() or not ancestor.is_dir() or info.st_uid != 0 or info.st_mode & 0o022:
                fail("privileged-destination-parent-unsafe")
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            fail("privileged-destination-unsafe")
        if mode is not None and stat.S_IMODE(info.st_mode) != mode:
            fail("privileged-destination-mode-differs-review-locally")
        if directory:
            if not path.is_dir():
                fail("privileged-destination-not-directory")
        elif not path.is_file() or expected is None or path.read_bytes() != expected:
            fail("existing-privileged-file-differs-no-overwrite")


def validate_host_directory(path, owner, group, mode, empty=False):
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if path.is_symlink() or not path.is_dir() or owner is None or info.st_uid != owner or info.st_gid != group:
            fail("existing-host-path-conflicts-review-it-manually")
        if stat.S_IMODE(info.st_mode) != mode:
            fail("existing-host-directory-mode-differs-review-locally")
        if empty and any(path.iterdir()):
            fail("existing-cache-view-is-not-empty-review-locally")


def admin_plan(source):
    require_host()
    source = cache_source(source)
    entry = account()
    if entry and not account_valid(entry):
        fail("existing-account-conflicts-do-not-modify-it-automatically")
    for p, owner, group, mode, empty in [
        (RUNNER_HOME, entry.pw_uid if entry else None, entry.pw_gid if entry else None, 0o700, False),
        (DATA_ROOT, 0, 0, 0o755, False),
        (CACHE_VIEW, 0, 0, 0o755, True),
        (OUTPUT_ROOT, entry.pw_uid if entry else None, entry.pw_gid if entry else None, 0o700, False),
    ]:
        validate_host_directory(p, owner, group, mode, empty)
    script_root = Path(__file__).resolve().parent
    installed_helpers = Path("/usr/local/lib/offmenu-runner")
    validate_privileged_destination(installed_helpers, directory=True, mode=0o755)
    if installed_helpers.exists() and set(p.name for p in installed_helpers.iterdir()) - {"setup-foo-runner.sh", "runner_host_setup.py"}:
        fail("existing-helper-directory-has-unrelated-content")
    for name in ("setup-foo-runner.sh", "runner_host_setup.py"):
        validate_privileged_destination(installed_helpers / name, (script_root / name).read_bytes(), mode=0o755)
    validate_privileged_destination(Path("/etc/systemd/system", SERVICE), service_text(source).encode(), mode=0o644)
    # /srv is a privileged destination too, even before its children exist.
    validate_privileged_destination(DATA_ROOT, directory=True)
    q = shlex.quote
    print("# Review these exact administrative steps. This command has not executed them.")
    print("# Stop here if the source tree contains credentials or non-dataset files.")
    print("set -eu")
    if not entry:
        print(f"sudo useradd --system --user-group --create-home --home-dir {RUNNER_HOME} --shell /usr/sbin/nologin {RUNNER_USER}")
    print(f"sudo install -d -o {RUNNER_USER} -g {RUNNER_USER} -m 0700 {RUNNER_HOME} {OUTPUT_ROOT}")
    print(f"sudo install -d -o root -g root -m 0755 {DATA_ROOT} {CACHE_VIEW} /usr/local/lib/offmenu-runner")
    for name in ("setup-foo-runner.sh", "runner_host_setup.py"):
        print(f"sudo install -o root -g root -m 0755 {q(str(script_root / name))} /usr/local/lib/offmenu-runner/{name}")
    print("UNIT=$(mktemp)")
    print("trap 'rm -f -- \"$UNIT\"' EXIT")
    print("cat >\"$UNIT\" <<'OFFMENU_SYSTEMD_UNIT'")
    print(service_text(source), end="")
    print("OFFMENU_SYSTEMD_UNIT")
    print(f"if [ -e /etc/systemd/system/{SERVICE} ]; then")
    print(f"  cmp -s \"$UNIT\" /etc/systemd/system/{SERVICE} || {{ echo 'Existing service differs; review it rather than overwriting.' >&2; exit 1; }}")
    print("else")
    print(f"  sudo install -o root -g root -m 0644 \"$UNIT\" /etc/systemd/system/{SERVICE}")
    print("fi")
    print("sudo systemctl daemon-reload")
    print("# Service is intentionally NOT started or enabled by these steps.")
    print("# Confirm the dedicated account can traverse/read the selected source without broadening unrelated access.")
    print(f"sudo -u {RUNNER_USER} test -r {q(str(source))}")
    print("# Follow docs/foo-runner.md for install, local token registration, and explicit start.")


def safe_extract(archive, dest):
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        for member in members:
            p = Path(member.name)
            if p.is_absolute() or ".." in p.parts or member.isdev():
                fail("unsafe-runner-archive-member")
            if member.issym() or member.islnk():
                target = (dest / p.parent / member.linkname).resolve()
                if not target.is_relative_to(dest.resolve()):
                    fail("unsafe-runner-archive-link")
        # Archive bytes have already matched the exact official SHA-256.
        tf.extractall(dest, members=members)


def install_runner():
    require_host()
    require_runner_identity()
    arch, expected = ASSETS[platform.machine()]
    marker = RUNNER_DIR / ".offmenu-install.json"
    lock = os.open(RUNNER_HOME / ".setup.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock, "r+") as held:
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("another-setup-is-running")
        if RUNNER_DIR.exists() or RUNNER_DIR.is_symlink():
            if RUNNER_DIR.is_symlink() or not marker.is_file():
                fail("existing-install-unrecognized-no-files-replaced")
            info = json.loads(marker.read_text())
            if info != {"repository": REPO, "initialVersion": VERSION, "sha256": expected}:
                fail("existing-install-marker-differs-no-files-replaced")
            if not (RUNNER_DIR / "config.sh").is_file() or not (RUNNER_DIR / "runsvc.sh").is_file():
                fail("existing-install-incomplete-no-files-replaced")
            print(json.dumps({"status": "already-installed", "automaticUpdatesPreserved": True}))
            return
        archive_name = f"actions-runner-linux-{arch}-{VERSION}.tar.gz"
        url = f"https://github.com/actions/runner/releases/download/v{VERSION}/{archive_name}"
        with tempfile.TemporaryDirectory(prefix=".install-", dir=RUNNER_HOME) as temporary:
            temp = Path(temporary)
            archive = temp / archive_name
            subprocess.run(["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https", "--tlsv1.2",
                            "--retry", "2", "--connect-timeout", "20", "--max-time", "900",
                            "--output", str(archive), url], check=True, env=minimal_env())
            digest = hashlib.sha256()
            with archive.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                fail("runner-archive-checksum-mismatch-nothing-extracted")
            extracted = temp / "runner"
            extracted.mkdir(mode=0o700)
            safe_extract(archive, extracted)
            (extracted / ".offmenu-install.json").write_text(json.dumps({"repository": REPO, "initialVersion": VERSION, "sha256": expected}) + "\n")
            extracted.rename(RUNNER_DIR)
        print(json.dumps({"status": "installed", "initialVersion": VERSION, "checksumVerified": True}))


def register_runner():
    require_runner_identity()
    if not (RUNNER_DIR / ".offmenu-install.json").is_file():
        fail("install-the-verified-runner-first")
    if (RUNNER_DIR / ".runner").exists():
        print(json.dumps({"status": "registration-already-present", "action": "verify-repository-and-runner-name-in-github-ui"}))
        return
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        fail("registration-requires-your-interactive-local-terminal")
    print("Open https://github.com/maldous/offmenu/settings/actions/runners/new in your own browser.")
    print("Enter its short-lived registration token ONLY in the runner's local prompt. Never paste it into chat, a command argument, a report, or a GitHub issue.")
    print("This registers persistent repository runner credentials under the dedicated account. It does not start the runner.")
    subprocess.run(["./config.sh", "--url", f"https://github.com/{REPO}", "--name", "foo-offmenu",
                    "--labels", "offmenu-foo", "--work", "_work"], cwd=RUNNER_DIR,
                   env=minimal_env(), check=True)
    print("Registration finished. Do not run run.sh directly; use the sandboxed service after reviewing its settings.")


def publish_report(issue):
    entry = account()
    if os.getuid() == 0 or (entry and os.getuid() == entry.pw_uid):
        fail("publish-only-as-your-existing-ordinary-github-cli-account")
    if not shutil.which("gh"):
        fail("existing-gh-cli-required-no-login-or-token-creation-attempted")
    subprocess.run(["gh", "auth", "status", "--hostname", "github.com"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
    report = preflight()
    with tempfile.NamedTemporaryFile("w", prefix="offmenu-safe-report-", suffix=".md") as f:
        f.write("OffMenu foo runner setup preflight (sanitized; no credentials, source paths, or dataset contents).\n\n")
        f.write("```json\n" + json.dumps(report, indent=2, sort_keys=True) + "\n```\n")
        f.flush()
        subprocess.run(["gh", "issue", "comment", str(issue), "--repo", REPO, "--body-file", f.name], check=True, timeout=60)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="preflight",
                        choices=("preflight", "admin-plan", "render-service", "install", "register", "publish-report"))
    parser.add_argument("--cache-root", help="Exact existing dataset-only directory; never a home or credentials directory")
    parser.add_argument("--issue", type=int, help="Existing issue/PR number in maldous/offmenu for one sanitized report")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.stage == "preflight":
            print(json.dumps(preflight(), indent=2, sort_keys=True))
        elif args.stage == "admin-plan":
            if not args.cache_root:
                fail("admin-plan-requires-cache-root")
            admin_plan(args.cache_root)
        elif args.stage == "render-service":
            if not args.cache_root:
                fail("render-service-requires-cache-root")
            print(service_text(cache_source(args.cache_root)), end="")
        elif args.stage == "install":
            install_runner()
        elif args.stage == "register":
            register_runner()
        elif args.stage == "publish-report":
            if args.issue is None or args.issue < 1:
                fail("publish-report-requires-positive-existing-issue-number")
            publish_report(args.issue)
    except SetupError as exc:
        print(json.dumps({"status": "blocked", "errorCode": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError):
        # No exception repr, environment dump, subprocess stderr, or file contents.
        print(json.dumps({"status": "failed", "errorCode": "local-stage-failed-review-locally"}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
