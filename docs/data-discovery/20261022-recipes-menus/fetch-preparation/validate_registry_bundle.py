"""Bounded local-only checks for the three disabled discovery registries."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("structured-recipes", "multilingual-recipes", "menus")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_bundle(root=ROOT):
    bundle = {}
    for name in NAMES:
        path = root / (name + ".json")
        require(path.stat().st_size <= 2_000_000, "Registry exceeds size budget")
        bundle[name] = json.loads(path.read_text(encoding="utf-8"))
    return bundle


def validate_bundle(bundle):
    counts = {}
    for name in NAMES:
        manifest = bundle[name]
        require(bool(manifest.get("schema_version")), "Missing schema version")
        rows = manifest.get("sources")
        require(isinstance(rows, list) and bool(rows), "Sources required")
        ids = [row.get("id") for row in rows]
        require(all(isinstance(i, str) and i for i in ids), "Source ID required")
        require(len(set(ids)) == len(ids), "Duplicate source IDs")
        counts[name] = len(rows)

    structured = bundle["structured-recipes"]
    require(structured.get("production_fetch_enabled") is False, "Structured enabled")
    require(structured.get("execution_location") == "Foo", "Structured not Foo-only")
    policy = structured.get("activation_policy", {})
    require(policy.get("hard_disabled") is True, "Hard disable missing")
    require(type(policy.get("required_database_count")) is int and policy["required_database_count"] == 8, "Eight-database gate missing")
    for key in ("network_execution_present", "credentials_included", "production_fetch_performed"):
        require(policy.get(key) is False, "Unsafe preparation policy: " + key)
    require(policy.get("requires_explicit_activation_after_readiness") is True, "Activation review missing")
    for row in structured["sources"]:
        require(row.get("enabled") is False and row.get("production_fetch_enabled") is False, "Structured source enabled")
        require(row.get("execution_location") == "Foo", "Source not Foo-only")

    multilingual = bundle["multilingual-recipes"]
    require(multilingual.get("production_fetch_enabled") is False, "Multilingual enabled")
    require(multilingual.get("production_fetch_target") == "Foo", "Multilingual not Foo-only")
    require("eight databases" in multilingual.get("activation_gate", ""), "Multilingual readiness gate missing")
    proposals = multilingual.get("disabled_fetch_proposals")
    require(isinstance(proposals, list) and bool(proposals), "Disabled proposals missing")
    ids = {row["id"] for row in multilingual["sources"]}
    proposal_ids = [proposal.get("source_id") for proposal in proposals]
    require(len(set(proposal_ids)) == len(proposal_ids), "Duplicate proposals")
    for proposal in proposals:
        require(proposal.get("source_id") in ids, "Unknown proposed source")
        require(proposal.get("enabled") is False, "Multilingual proposal enabled")
        require(proposal.get("fetch_images") is False, "Unexpected image acquisition")

    menus = bundle["menus"]
    policy = menus.get("execution_policy", {})
    require(policy.get("enabled") is False and policy.get("production_fetch_allowed") is False, "Menus enabled")
    require(policy.get("target") == "Foo" and policy.get("preparation_only") is True, "Invalid menu execution policy")
    require("eight databases" in policy.get("required_user_gate", ""), "Menu readiness gate missing")
    for row in menus["sources"]:
        registry = row.get("proposed_registry", {})
        require(registry.get("enabled") is False and registry.get("production_fetch_allowed") is False, "Menu source enabled")
        require(registry.get("execution_target") == "Foo", "Menu source not Foo-only")
        require(registry.get("schedule") is None, "Acquisition schedule present")
        gates = registry.get("activation_gates", [])
        require("all_eight_databases_provisioned" in gates, "Provisioning gate missing")
        require("all_eight_databases_relationally_fit_for_existing_data" in gates, "Relational-fit gate missing")
        require(row.get("mapping", {}).get("recipe_reference") is None, "Unsupported menu recipe link")
    return {"source_rows": counts, "all_disabled": True, "production_target": "Foo"}


if __name__ == "__main__":
    print(json.dumps(validate_bundle(load_bundle()), sort_keys=True))
