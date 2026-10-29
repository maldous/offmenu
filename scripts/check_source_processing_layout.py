#!/usr/bin/env python3
"""Check selected source-tool relocation without executing real input processing."""

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "ebc65204c4efc8022ac63ab5dc462cb9bcf3120e"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE, help="Pre-migration source revision")
    args = parser.parse_args()
    source = git("ls-tree", "-r", "--name-only", args.base, "manual-action").decode().splitlines()
    if not source:
        parser.error("No manual-action files at base")
    counts = {"files_relocated": len(source), "guides_renamed": 0,
              "python_modules_parse": 0, "native_fixture_files_unchanged": 0,
              "local_schema_references_resolve": 0}
    issues = []
    for old in source:
        suffix = old.removeprefix("manual-action/")
        if suffix.endswith(".md"):
            target = ROOT / "docs/source-processing" / suffix.lower()
            counts["guides_renamed"] += 1
        else:
            target = ROOT / "tools/source-processing" / suffix.replace(
                "gold_recipe_label_scenario.mjs", "gold-recipe-label-scenario.mjs"
            )
        if not target.is_file():
            issues.append({"path": str(target.relative_to(ROOT)), "error": "missing"})
            continue
        if "tests/fixtures/" in old:
            if target.read_bytes() != git("show", args.base + ":" + old):
                issues.append({"path": old, "error": "pinned fixture changed"})
            else:
                counts["native_fixture_files_unchanged"] += 1
        if target.suffix == ".py":
            ast.parse(target.read_text(), filename=str(target))
            counts["python_modules_parse"] += 1
        if target.name.endswith(".schema.json"):
            for ref in re.findall(r'"\$ref"\s*:\s*"([^"#]+)(?:#[^"]*)?"', target.read_text()):
                if ":" in ref:
                    continue
                if not (target.parent / ref).is_file():
                    issues.append({"path": str(target.relative_to(ROOT)), "error": "missing schema ref", "ref": ref})
                else:
                    counts["local_schema_references_resolve"] += 1
    script = ROOT / "tools/source-processing/gold-recipe-label-scenario.mjs"
    subprocess.run(["node", "--check", str(script)], check=True, timeout=10)
    print(json.dumps({"base": args.base, **counts, "issues": issues}, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
