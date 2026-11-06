#!/usr/bin/env python3
"""Derive a manifest-pinned normalized partition locally; emit metadata only.

Sidecar data stays beside this script on the existing confined host. This is a
finite selected-partition consumer exercise, NOT full corpus coverage or an app
release check. The input/output roots must be separately approved by the caller.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
from north_star_derivations import derive, query_candidates, VERSION, PROP, REL, TYPE


def sha(b):
    return hashlib.sha256(b).hexdigest()


def selected_file(root, entry):
    key = Path(entry["key"])
    if key.is_absolute() or ".." in key.parts:
        raise ValueError("unsafe selected asset")
    p = root / key
    if root.resolve() not in p.resolve().parents or any((root / Path(*key.parts[:n])).is_symlink() for n in range(1, len(key.parts) + 1)):
        raise ValueError("symlink selected asset")
    b = p.read_bytes()
    if len(b) != entry["bytes"] or sha(b) != entry["sha256"]:
        raise ValueError("selected asset bytes differ")
    return b


def inspect(package, manifest_sha, asset_key, output):
    manifest_bytes = (package / "manifest.json").read_bytes()
    if sha(manifest_bytes) != manifest_sha:
        raise ValueError("selected manifest bytes differ")
    manifest = json.loads(manifest_bytes)
    files = {f["key"]: f for f in manifest["files"]}
    asset = files[asset_key]
    if not asset_key.endswith(".jsonl.gz"):
        raise ValueError("only normalized jsonl gzip packet assets")
    data = selected_file(package, asset)
    contract_bytes = selected_file(package, files["contract.json"])
    schema_bytes = selected_file(package, files["schema.json"])
    contract = json.loads(contract_bytes)
    import jsonschema
    validator = jsonschema.Draft202012Validator(json.loads(schema_bytes), format_checker=jsonschema.FormatChecker())
    if output.exists():
        raise ValueError("immutable output already exists")
    output.mkdir(parents=True)
    types = collections.Counter(); predicates = collections.Counter(); issues = collections.Counter()
    source_ids = collections.Counter(); statuses = collections.Counter(); units = collections.Counter()
    rejected_identifiers = collections.Counter()
    resources = {}; context_subjects = set(); products = set(); edges = []; identifiers = []
    count = derived_assertions = derived_relations = 0
    # At most one selected, manifest-listed partition; never enumerate the raw
    # corpus. Decompression and JSON parsing remain stream-bounded per packet.
    import io
    side_path = output / "derivations.jsonl.gz"
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as source, side_path.open("xb") as target:
        with gzip.GzipFile(fileobj=target, mode="wb", mtime=0) as sink:
            for line in source:
                packet = json.loads(line)
                validator.validate(packet)
                side = derive(packet, contract)
                side["inputSelection"] = {"manifestByteSha256": manifest_sha, "assetKey": asset_key,
                                          "assetSha256": asset["sha256"], "packetOrdinal": count}
                sink.write((json.dumps(side, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
                count += 1
                for r in packet["resources"]:
                    if r["id"] in resources: raise ValueError("duplicate selected resource")
                    citation_map = {c["id"]: c for c in packet["citations"]}
                    resources[r["id"]] = {"type": r["type"], "scope": r["scope"],
                        "sourceReleases": {(citation_map[c]["sourceId"], str(citation_map[c].get("revisionId"))) for c in r["citationIds"]}}
                    types[r["type"]] += 1
                    if r["type"] == TYPE + "FoodProduct": products.add(r["id"])
                for c in packet["citations"]: source_ids[c["sourceId"]] += 1
                for r in packet["relations"]: predicates[r["predicateId"]] += 1
                for a in packet["assertions"]:
                    statuses[a["status"]] += 1
                    if a["value"].get("kind") == "quantity": units[str(a["value"].get("unitId"))] += 1
                    if a["propertyId"] == PROP + "sourceIdentifier":
                        f = a["value"].get("fields", {})
                        system, value = f.get("system", {}).get("value"), f.get("value", {}).get("value")
                        citation_map = {c["id"]: c for c in packet["citations"]}
                        if a["status"] not in {"source-asserted", "candidate", "editor-authored", "reviewed", "verified"}:
                            rejected_identifiers["input-status-not-usable"] += 1; continue
                        if not isinstance(system, str) or not system.strip() or not isinstance(value, str) or not value.strip():
                            rejected_identifiers["namespace-or-lexical-value-missing"] += 1; continue
                        cs = [citation_map[c] for c in a["citationIds"] if c in citation_map]
                        if not cs or len(cs) != len(a["citationIds"]) or any(c.get("revisionId") in (None, "") for c in cs):
                            rejected_identifiers["source-release-binding-missing"] += 1; continue
                        bindings = {(c["sourceId"], str(c["revisionId"])) for c in cs}
                        subject = resources.get(a["subjectId"])
                        if subject is None or subject["scope"] != a["scope"] or any(c["scope"] != a["scope"] for c in cs) or subject["sourceReleases"] != bindings:
                            rejected_identifiers["identifier-resource-evidence-mismatch"] += 1; continue
                        for source_id, release in sorted(bindings):
                            identifiers.append((source_id, release, system, value, a["subjectId"]))
                derived_assertions += len(side["assertions"]); derived_relations += len(side["relations"])
                issues.update(i["code"] for i in side["issues"])
                context_subjects.update(a["subjectId"] for a in side["assertions"])
                for p in packet["resources"]:
                    answer = query_candidates(side, p["id"], include_candidates=True)
                    citation_map = {c["id"]: c for c in packet["citations"]}
                    for edge in answer["relations"]:
                        edge["sourceReleases"] = {(citation_map[c]["sourceId"], str(citation_map[c].get("revisionId"))) for c in edge["citationIds"]}
                        edges.append(edge)
    if count != asset["packets"]:
        raise ValueError("selected partition packet reconciliation failed")
    def resolved(edge):
        a, b = resources.get(edge["subjectId"]), resources.get(edge["objectId"])
        return (a is not None and b is not None and a["type"] in edge["expectedSubjectTypes"]
                and b["type"] == edge["expectedObjectType"] and a["scope"] == b["scope"] == edge["scope"]
                and a["sourceReleases"] == b["sourceReleases"] == edge["sourceReleases"])
    joined = [(edge["subjectId"], edge["objectId"]) for edge in edges if edge["subjectId"] in products and resolved(edge)]
    contexts = [(a, b) for a, b in joined if b in context_subjects]
    index = collections.defaultdict(set)
    for source_id, release, namespace, lexical, subject in identifiers:
        index[(source_id, release, namespace, lexical)].add(subject)
    # A profile may repeat the product's identifier. The caller specifies the
    # resource type; that repeat is not a second product or identity ambiguity.
    product_index = {key: targets & products for key, targets in index.items() if targets & products}
    unique_queries = [targets for targets in product_index.values() if len(targets) == 1]
    joined_products = {a for a, b in joined}; contextual_products = {a for a, b in contexts}
    report = {
        "schemaVersion": "offmenu-north-star-selected-partition-exercise/1", "rulesetVersion": VERSION,
        "status": "selected-normalized-partition-candidate-exercised", "fullCorpusCoverage": False,
        "selectedReleaseId": manifest["releaseId"], "manifestByteSha256": manifest_sha,
        "asset": asset, "schemaByteSha256": sha(schema_bytes), "contractByteSha256": sha(contract_bytes),
        "packets": count, "resourceTypes": dict(types), "sourceCitationCounts": dict(source_ids),
        "selectedPacketsSchemaValidated": count,
        "inputPredicates": dict(predicates), "inputAssertionStatuses": dict(statuses), "inputQuantityUnits": dict(units),
        "derivedAssertions": derived_assertions, "derivedRelations": derived_relations,
        "issues": dict(issues), "sidecarSha256": sha(side_path.read_bytes()), "sidecarBytes": side_path.stat().st_size,
        "diagnosticQueries": {
            "exactSourceReleaseNamespaceLexicalKeys": len(index), "uniqueSourceScopedProductKeys": len(unique_queries),
            "ambiguousProductKeysNotMerged": sum(len(t) != 1 for t in product_index.values()),
            "crossTypeIdentifierRepeatsNotTreatedAsProducts": sum(len(t) > len(t & products) and bool(t & products) for t in index.values()),
            "rejectedIdentifierAssertions": dict(rejected_identifiers),
            "productProfileEdgesResolvedWithinSelectedPartition": len(joined),
            "productProfileNutrientContextJoinsWithinSelectedPartition": len(contexts),
            "identifierProductProfileJoins": sum(bool(t & joined_products) for t in unique_queries),
            "identifierProductProfileNutrientContextJoins": sum(bool(t & contextual_products) for t in unique_queries),
            "acceptedProductIngredientJoins": 0, "acceptedRecipeNutritionJoins": 0,
            "servedAppQueriesExercised": 0,
            "limits": "Selected source-scoped structural diagnostics only; absent joins are unresolved, not proof of absence across the full graph."
        },
        "originalsModified": False, "publicAdmissionGranted": False, "identityAccepted": False,
        "confidence": {"status": "not-calibrated", "probability": None},
        "sourceCodeSha256": {"north_star_derivations.py": sha(Path(__file__).with_name("north_star_derivations.py").read_bytes()),
                             "inspect_north_star_sample.py": sha(Path(__file__).read_bytes())},
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("package", type=Path); ap.add_argument("manifest_sha")
    ap.add_argument("asset_key"); ap.add_argument("output", type=Path); args = ap.parse_args()
    report = inspect(args.package, args.manifest_sha, args.asset_key, args.output)
    print(json.dumps({k: report[k] for k in ("status", "packets", "derivedAssertions", "derivedRelations", "diagnosticQueries")}))
