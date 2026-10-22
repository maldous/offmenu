"""Offline validation only. There is deliberately no network/acquisition path."""
import json
import sys
from pathlib import Path


def validate_manifest(manifest):
    if manifest.get("production_fetch_enabled") is not False:
        raise ValueError("Preparation must keep production_fetch_enabled false")
    if manifest.get("execution_location") != "Foo":
        raise ValueError("Future production execution is Foo-only")
    policy = manifest.get("activation_policy", {})
    required = {
        "hard_disabled": True,
        "network_execution_present": False,
        "requires_explicit_activation_after_readiness": True,
        "required_database_count": 8,
        "credentials_included": False,
        "production_fetch_performed": False,
    }
    for key, expected in required.items():
        if type(policy.get(key)) is not type(expected) or policy.get(key) != expected:
            raise ValueError(f"Invalid preparation policy: {key}")
    ids = set()
    for source in manifest.get("sources", []):
        if source.get("id") in ids or not source.get("id"):
            raise ValueError("Source IDs must be present and unique")
        ids.add(source["id"])
        if source.get("enabled") is not False or source.get("production_fetch_enabled") is not False:
            raise ValueError(f"Source must remain disabled: {source['id']}")
        if source.get("execution_location") != "Foo":
            raise ValueError("Every future source execution is Foo-only")
        if source.get("tier") not in {"A", "B", "C"}:
            raise ValueError("Unknown rights-review tier")
        if not source.get("source_urls") or not source.get("blockers"):
            raise ValueError("Source evidence URLs and unresolved gates are required")
        for count in source.get("counts", []):
            if not all(key in count for key in ("value", "unit", "basis", "qualifier")):
                raise ValueError("Counts must distinguish basis, units and caveats")
    if not ids:
        raise ValueError("No sources")
    baseline = manifest["baseline"]
    if sum(baseline["accepted_families"].values()) != baseline["retained_total"]:
        raise ValueError("Baseline family total mismatch")
    return {"source_count": len(ids), "all_disabled": True, "execution_location": "Foo"}


def production_fetch(*args, **kwargs):
    """Hard refusal, including when callers supply eight apparent ready flags."""
    raise PermissionError(
        "Disabled preparation artifact: production may run on Foo only after all eight "
        "databases are provisioned and relationally fit for existing data, with reviewed "
        "readiness evidence and a separately authorized activation. No fetch is implemented."
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python validate_manifest.py <local-manifest.json>")
    path = Path(sys.argv[1])
    if path.stat().st_size > 2_000_000:
        raise SystemExit("Manifest exceeds offline validation size budget")
    print(json.dumps(validate_manifest(json.loads(path.read_text(encoding="utf-8"))), sort_keys=True))
