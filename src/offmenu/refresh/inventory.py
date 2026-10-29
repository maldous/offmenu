"""Bounded metadata-only inventory. Never open asset contents or follow links."""
import collections
import hashlib
import os
from pathlib import Path


# These are candidate signatures, not proof of usable data or current releases.
SIGNATURES = {
    "recipes_parsed.json": "wikibooks",
    "openfoodfacts-products.jsonl.gz": "off",
    "fineli-basic2.zip": "fineli",
    "cnf-2015-csv.zip": "cnf",
    "nz-foodfiles-2024.msi": "foodfiles",
    "sweden-20260701.xlsx": "sweden-food",
}
SKIP = {".git", ".aws", ".ssh", ".codex", ".freebuff", "node_modules", ".venv",
        "dev-preview-20261014", "__pycache__"}


def inventory(root, *, max_entries=10000, max_depth=4):
    from .core import safe_path
    root = safe_path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("inventory root must be an existing directory, not a symlink")
    if not 1 <= max_entries <= 1000000 or not 0 <= max_depth <= 20:
        raise ValueError("inventory limits are out of range")
    root = root.resolve()
    pending = [(root, 0)]
    counts = collections.Counter()
    candidates = []
    extensions = collections.Counter()
    stopped = False
    while pending and not stopped:
        directory, depth = pending.pop()
        try:
            # Do not materialize all directory entries: the cap also bounds memory.
            with os.scandir(directory) as entries:
                for entry in entries:
                    if counts["entries"] >= max_entries:
                        stopped = True
                        break
                    counts["entries"] += 1
                    try:
                        if entry.is_symlink():
                            counts["symlinksSkipped"] += 1
                        elif entry.name.startswith(".") or entry.name in SKIP:
                            counts["privateOrRuntimeEntriesSkipped"] += 1
                        elif entry.is_dir(follow_symlinks=False):
                            counts["directories"] += 1
                            if depth < max_depth:
                                pending.append((Path(entry.path), depth + 1))
                            else:
                                counts["depthLimitedDirectories"] += 1
                        elif entry.is_file(follow_symlinks=False):
                            info = entry.stat(follow_symlinks=False)
                            counts["files"] += 1
                            counts["bytesObserved"] += info.st_size
                            ext = Path(entry.name).suffix.lower()
                            extensions[ext if ext in {".json", ".jsonl", ".gz", ".zip", ".csv", ".xlsx", ".sqlite", ".parquet", ".xml", ".msi"} else "other"] += 1
                            if entry.name in SIGNATURES and len(candidates) < 100:
                                relative = str(Path(entry.path).relative_to(root))
                                candidates.append({"assetId": hashlib.sha256(relative.encode()).hexdigest(),
                                                   "sourceId": SIGNATURES[entry.name],
                                                   "bytes": info.st_size,
                                                   "state": "filename-candidate-unverified"})
                        else:
                            counts["specialFilesSkipped"] += 1
                    except OSError:
                        counts["unreadableEntries"] += 1
        except OSError:
            counts["unreadableDirectories"] += 1
    return {"schemaVersion": "offmenu-refresh-inventory/1", "mode": "read-only-metadata",
            "limits": {"maxEntries": max_entries, "maxDepth": max_depth},
            "boundedScanComplete": not stopped,
            "scopeComplete": not stopped and not counts["depthLimitedDirectories"] and not counts["unreadableDirectories"] and not counts["unreadableEntries"] and not counts["privateOrRuntimeEntriesSkipped"] and not counts["symlinksSkipped"],
            "counts": dict(counts), "fileTypes": dict(sorted(extensions.items())),
            "candidates": sorted(candidates, key=lambda c: c["assetId"]),
            "candidateLimit": 100, "contentsRead": False, "assetHashesVerified": False,
            "pathsIncluded": False, "coverageEstablished": False}
