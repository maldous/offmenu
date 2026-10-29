#!/usr/bin/env python3
"""Verify the test-layout migration against its immutable pre-migration tree."""

import argparse
import json
import posixpath
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "366c3710eeb9f732197250b217d412cd9e3b5d7e"
MAPPINGS = {"tests-web": "tests/web", "tests-edge": "tests/edge", "tests-compat": "tests/compat"}
RELATIVE_LITERAL = re.compile(r"['\"](\.\.(?:/[^'\"\n]*)?|\./[^'\"\n]*)['\"]")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE, help="Immutable pre-migration revision")
    args = parser.parse_args()
    tracked = set(git("ls-tree", "-r", "--name-only", args.base).decode().splitlines())
    selected = sorted(name for name in tracked if name.split("/", 1)[0] in MAPPINGS)
    if not selected:
        parser.error("Base revision contains no legacy test roots")
    issues = []
    counts = {"files_relocated": len(selected), "literal_tracked_file_dependencies": 0,
              "fixtures_unchanged": 0, "top_level_modules_parse": 0}
    for old in selected:
        prefix, suffix = old.split("/", 1)
        new = MAPPINGS[prefix] + "/" + suffix
        target = ROOT / new
        if not target.is_file():
            issues.append({"path": new, "error": "relocated file missing"})
            continue
        raw = git("show", args.base + ":" + old)
        now = target.read_bytes()
        if "/fixtures/" in old:
            if raw == now:
                counts["fixtures_unchanged"] += 1
            elif suffix != "fixtures/off-photos/context.mjs" or now != raw.replace(
                b"'../../../public/", b"'../../../../public/"
            ):
                issues.append({"path": new, "error": "unexpected fixture byte change"})
        if not old.endswith(".mjs"):
            continue
        before = RELATIVE_LITERAL.findall(raw.decode())
        after = RELATIVE_LITERAL.findall(now.decode())
        if len(before) != len(after):
            issues.append({"path": new, "error": "relative literal count changed"})
            continue
        for source, destination in zip(before, after):
            old_target = posixpath.normpath(posixpath.join(posixpath.dirname(old), source))
            if old_target in tracked:
                counts["literal_tracked_file_dependencies"] += 1
                if not (target.parent / destination).exists():
                    issues.append({"path": new, "error": "relative dependency missing",
                                   "dependency": destination})
        if len(Path(new).parts) == 3:
            result = subprocess.run(["node", "--check", str(target)], capture_output=True,
                                    text=True, timeout=10, check=False)
            if result.returncode:
                issues.append({"path": new, "error": result.stderr})
            else:
                counts["top_level_modules_parse"] += 1
    print(json.dumps({"base": args.base, **counts, "issues": issues}, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
