#!/usr/bin/env python3
"""Build source discovery and coverage registers from pinned repository records.

This is deliberately an offline projection: it never fetches a source or turns a
research lead into permission, custody, a type binding, or proven coverage.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/collection-selections/global-comprehensive-manifest.json"
COUNTRY_REGISTER = ROOT / "docs/country-delivery-matrix.json"
DELIVERY_LEDGER = ROOT / "docs/source-delivery-ledger.json"
ENRICHMENT_REGISTER = ROOT / "research/OffMenu_Enrichment_Source_Register_249.json"
OUTPUT = ROOT / "docs/coverage-register/2026-10-19"
BINDING_FIELDS = ("bindings", "canonicalBindings", "candidateBindings", "sourceContractBindings")
TYPE_TERMS = {
    "barcodes_products": ("barcode", "gtin", "product", "sku", "plu", "food identity", "brand", "packaged food"),
    "food_composition": ("composition", "nutrition", "nutrient", "food database", "food table", "ingredient table"),
    "food_identity": ("food identity", "food name", "food taxonomy", "foodon", "ingredient identity"),
    "recipes": ("recipe", "cookbook", "culinary", "food use", "dietary pattern", "consumption", "food habit"),
    "menus_venues": ("menu", "venue", "restaurant", "food service", "food-place", "places", "cafe", "catering"),
    "retailers_prices": ("price", "retail", "retailer", "market price", "grocery", "supermarket", "consumer price", "basket price"),
    "companies_ownership": ("company", "companies", "ownership", "business register", "business registry", "manufacturer", "enterprise", "corporate"),
    "origin_supply_chain": ("origin", "supply chain", "producer", "grower", "import", "export", "traceability", "agriculture"),
    "diet_certification": ("certification", "certified", "halal", "kosher", "vegan", "organic", "gluten-free", "certifier"),
    "recalls_regulation": ("recall", "food safety", "food alert", "regulation", "regulatory", "food standard", "inspection"),
    "baskets": ("basket", "minimum basket", "food basket", "market basket", "food expenditure"),
    "health_integrations": ("health integration", "health data", "health survey", "health and nutrition", "clinical", "micronutrient", "nutrition survey"),
    "locale_accessibility": ("locale", "accessibility", "language", "localization", "translation", "regional terminology"),
}
CATEGORY_TERMS = {
    "food_composition": ("food composition", "nutrition", "nutrient", "composition table", "food table", "food databases"),
    "food_identity": ("product identity", "product", "barcode", "identifier", "food identity", "plu"),
    "recipes": ("recipe", "food use", "food consumption", "culinary", "food habits", "dietary patterns"),
    "menus_venues": ("restaurant", "menu", "food service", "venue", "places"),
    "retailers_prices": ("retail", "price", "market", "basket", "grocery", "supermarket", "consumer prices"),
    "companies_ownership": ("company", "companies", "business", "ownership", "enterprise", "manufactur"),
    "origin_supply_chain": ("producer", "grower", "supply chain", "origin", "agriculture", "import", "export"),
    "diet_certification": ("certification", "certified", "halal", "kosher", "vegan", "organic", "gluten-free"),
    "recalls_regulation": ("recall", "food safety", "regulation", "food standard", "food alert"),
    "baskets": ("basket", "food expenditure", "minimum basket", "consumption basket"),
    "health_integrations": ("health", "clinical", "micronutrient", "nutrition survey", "public health"),
    "locale_accessibility": ("locale", "accessibility", "translation", "language", "localization"),
    "barcodes_products": ("barcode", "gtin", "plu", "product identity", "product"),
}


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def classify(text: str, *, global_source: bool = False) -> list[str]:
    value = norm(text)
    hits = []
    for kind in TYPE_TERMS:
        terms = CATEGORY_TERMS[kind] if global_source else TYPE_TERMS[kind]
        if any(norm(term) in value for term in terms):
            hits.append(kind)
    # Generic "product" leads are too broad unless their exact language names
    # identity/barcodes. Product source families from the research categories
    # may still be retained as proposed, never as an admitted type binding.
    return hits


def release_of(asset: dict) -> list[dict]:
    return asset.get("releases") or []


def asset_source_records(manifest: dict, ledger: dict, research: dict):
    assets = {a["assetId"]: dict(a) for a in manifest["assets"]}
    aliases: dict[str, set[str]] = collections.defaultdict(set)
    for asset in assets.values():
        for value in [asset["assetId"], asset.get("sourceKey"), *(asset.get("registryDescriptorIds") or []), *(asset.get("assetIdAliases") or [])]:
            if value:
                aliases[value].add(asset["assetId"])
    ledger_by_id = {row["sourceId"]: row for row in ledger["sources"]}
    research_by_id = {row["source_id"]: row for row in research["source_catalog"]}
    global_by_id = {row["source_id"]: row for row in research["global_sources"]}
    # All source aliases discovered via official country and global registers
    # remain in the unique asset register even where they have no baseline
    # runtime manifest descriptor yet.
    for sid, row in ledger_by_id.items():
        if sid not in aliases:
            assets[sid] = {
                "assetId": sid, "sourceURLs": [row.get("url")] if row.get("url") else [],
                "sourceKey": sid, "discoveryOnly": True,
            }
            aliases[sid].add(sid)
    for sid, row in {**research_by_id, **global_by_id}.items():
        if sid not in aliases:
            url = row.get("canonical_url") or row.get("url")
            assets[sid] = {"assetId": sid, "sourceURLs": [url] if url else [], "sourceKey": sid, "discoveryOnly": True}
            aliases[sid].add(sid)
    return assets, aliases, ledger_by_id, research_by_id, global_by_id


def binding_map(asset: dict) -> dict[tuple[str, str], set[str]]:
    result: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for field in BINDING_FIELDS:
        for item in asset.get(field) or []:
            if isinstance(item, dict) and item.get("country") and item.get("type"):
                result[(item["country"], item["type"])].add(field)
    return result


def source_status(asset: dict, ledger_row: dict | None) -> str:
    if ledger_row and ledger_row.get("globalRoute") and not asset.get("discoveryOnly"):
        return "discovered-unbound"
    if asset.get("discoveryOnly"):
        return "discovery-only"
    disposition = asset.get("sourceUseDisposition")
    if disposition and str(disposition).startswith("held-"):
        return "externally-restricted"
    if asset.get("retainedOriginals") or asset.get("retainedOriginal"):
        return "identified-not-verified"
    if asset.get("sourceURLs"):
        return "identified-not-fetched"
    if asset.get("bindings") or asset.get("countryHints") or asset.get("typeHints"):
        return "candidate-evidence-only"
    return "no-source-found"


def build():
    manifest_raw = MANIFEST.read_bytes()
    matrix_raw = COUNTRY_REGISTER.read_bytes()
    ledger_raw = DELIVERY_LEDGER.read_bytes()
    research_raw = ENRICHMENT_REGISTER.read_bytes()
    manifest, matrix, ledger, research = map(json.loads, (manifest_raw, matrix_raw, ledger_raw, research_raw))
    countries = {row["iso2"]: row["name"] for row in matrix["countries"]}
    if len(countries) != 249 or set(countries) != set(manifest["countries"]):
        raise ValueError("country catalog mismatch")
    types = list(manifest["types"])
    if len(types) != 13 or len(set(types)) != 13:
        raise ValueError("required type vocabulary mismatch")
    assets, aliases, ledger_by_id, catalog, globals_ = asset_source_records(manifest, ledger, research)
    manifest_assets = {a["assetId"]: a for a in manifest["assets"]}
    cells = {(c["country"], c["type"]): c for c in manifest["cells"]}
    country_origins = ["GLOBAL", *sorted(countries)]
    origins = {"GLOBAL": {"name": "Global shared scope", "scope": "shared", "evidence": "globalRoute records from source-delivery-ledger.json; no country fan-out implied"}}
    origins.update({c: {"name": countries[c], "scope": "country", "evidence": "ISO-3166-1 alpha-2 country catalog in docs/country-delivery-matrix.json"} for c in sorted(countries)})

    asset_rows = []
    links: dict[str, set[str]] = collections.defaultdict(set)
    discovery: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for aid, asset in sorted(assets.items()):
        ledger_row = ledger_by_id.get(aid)
        research_row = catalog.get(aid) or globals_.get(aid)
        # Keep every inventory and discovery-registry asset, including records
        # without a URL; absence of a URL is explicit source-discovery work.
        if research_row is not None and aid in globals_:
            research_row = globals_[aid]
        names = (ledger_row or {}).get("names") or (research_row or {}).get("names") or [aid]
        if isinstance(names, str): names = [names]
        citation = {
            "name": names[0] if names else aid,
            "ledgerSourceId": aid if ledger_row else None,
            "researchReference": (ledger_row or {}).get("researchReference"),
            "researchReportId": (research_row or {}).get("report_id"),
            "publisher": (research_row or {}).get("publisher"),
            "use": (research_row or {}).get("use"),
            "limits": (research_row or {}).get("limits"),
        }
        urls = sorted({u for u in [*((asset.get("sourceURLs") or [])), (ledger_row or {}).get("url"), (research_row or {}).get("url"), (research_row or {}).get("canonical_url"), *((research_row or {}).get("observed_urls") or [])] if isinstance(u, str) and u.startswith(("http://", "https://"))})
        hints = set(asset.get("countryHints") or [])
        exact_binding_pairs = set(binding_map(asset))
        contexts = (research_row or {}).get("contexts") or []
        for context in contexts:
            if context.get("scope") == "country" and context.get("iso2") in countries:
                hints.add(context["iso2"])
        if ledger_row:
            hints.update(c for c in ledger_row.get("countries", []) if c in countries)
        is_global = bool((ledger_row or {}).get("globalRoute") or any(c.get("scope") == "global" for c in contexts))
        explicit_type_hints = set(asset.get("typeHints") or [])
        research_text = " ".join(str(x) for x in [*(names or []), (research_row or {}).get("group"), (research_row or {}).get("use"), (research_row or {}).get("limits")])
        proposal_types = explicit_type_hints | set(classify(research_text, global_source=is_global))
        # Only hints/candidate classifications are represented as leads. They
        # never populate canonical links or prove applicable source contents.
        descriptor_ids = set(asset.get("registryDescriptorIds") or [])
        if aid in manifest_assets:
            descriptor_ids.add(aid)
        releases = release_of(asset)
        formats = asset.get("recordedFormats") or []
        if isinstance(formats, str): formats = [formats]
        expected_access = (research_row or {}).get("access")
        custody = asset.get("currentCustody")
        transfer = asset.get("transfer")
        for country in hints:
            if country in countries:
                for kind in proposal_types:
                    discovery[(country, kind)].append({"assetId": aid, "status": "discovery-lead-unbound", "evidence": "manifest country/type hint or research register country context plus scoped type text; not an accepted binding", "nextAction": (ledger_row or {}).get("nextAction") or "Review source applicability and release scope; confirm rights and a complete acquisition contract before any fetch."})
        if is_global:
            for kind in proposal_types:
                discovery[("GLOBAL", kind)].append({"assetId": aid, "status": "global-lead-unbound", "evidence": "source register explicitly marks a global route; country membership/content is not implied", "nextAction": (ledger_row or {}).get("nextAction") or "Establish exact source scope, release assets, permissions, and country/type applicability before acquisition."})
        asset_rows.append({
            "assetId": aid,
            "identityBasis": "runtime-manifest-asset-id" if aid in manifest_assets else "source-register-id; distinct until release/content identity is established",
            "aliases": sorted(a for a, ids in aliases.items() if aid in ids and a != aid),
            "publisher": (research_row or {}).get("publisher"),
            "citation": citation,
            "sourceURLs": urls,
            "assetIdentity": {"publisherSourceIds": sorted({aid, *descriptor_ids}), "releaseKeys": releases, "requestVariants": sorted({json.dumps({"url": url, "query": urlsplit(url).query}, sort_keys=True) for url in urls}), "contentHashes": sorted({value for value in [*((asset.get("retainedOriginal") or {}).get("sha256"),), *[(x.get("sha256") if isinstance(x, dict) else None) for x in (asset.get("retainedOriginals") or [])]] if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)}), "identityCaveat": "description and URL are not sufficient asset identity; source ID, release and request parameters are retained; content hash joins require exact verified evidence"},
            "release": releases,
            "format": formats,
            "accessConditions": {"accessLabel": expected_access, "sourceUseDisposition": asset.get("sourceUseDisposition"), "holds": sorted({json.dumps(value, ensure_ascii=False, sort_keys=True) for value in [*(asset.get("holds") or []), *(asset.get("sourceStageHolds") or [])]}), "researchReuseClearance": (research_row or {}).get("reuse_clearance")},
            "downloadMethod": {"method": "not-established", "evidence": (ledger_row or {}).get("accessEvidence"), "nextAction": (ledger_row or {}).get("nextAction") or "Identify permitted bulk export/API/download contract; a landing-page check is not a dataset download."},
            "custody": {"state": custody or ("not-in-manifest" if aid not in manifest_assets else "unverified-current"), "freshness": asset.get("custodyFreshness"), "retainedOriginals": asset.get("retainedOriginals") or ([asset["retainedOriginal"]] if asset.get("retainedOriginal") else []), "transfer": transfer, "verification": asset.get("freshCustodyEvidence")},
            "manifestDisposition": asset.get("disposition"),
            "manifestBindings": {field: asset.get(field) or [] for field in BINDING_FIELDS},
            "countryHints": sorted(hints),
            "typeHints": sorted(explicit_type_hints),
            "proposedTypes": sorted(proposal_types),
            "scope": "global-shared-candidate" if is_global else "country-or-unbound-candidate",
            "countryFanoutAllowed": False,
            "sourceStatus": source_status(asset, ledger_row),
            "evidence": {"ledgerDeliveryStatus": (ledger_row or {}).get("deliveryStatus"), "landingPageEvidence": (ledger_row or {}).get("accessEvidence"), "researchContexts": contexts, "manifestEvidenceRefs": asset.get("evidenceRefs") or [], "registryDescriptorIds": sorted(descriptor_ids)},
            "gaps": sorted(set(asset.get("missingContractFields") or []) | set(asset.get("explicitContractGaps") or [])),
            "nextAction": "1) verify type and geographic/data coverage from publisher evidence; 2) resolve the concrete release/download or API location and exact request parameters; 3) establish applicable permissions/access terms; 4) define and validate a bounded fetch contract; 5) acquire once per distinct asset with pagination/multipart completion and hash verification; 6) parse to source-faithful records and reconcile scope. Current evidence: " + ((ledger_row or {}).get("nextAction") or ("URL present; release/applicability/permissions and contract still require evidence." if urls else "No concrete URL; search official and original-language sources and record search outcomes.")),
        })

    asset_index = {a["assetId"]: a for a in asset_rows}
    cell_rows = []
    for origin in country_origins:
        for kind in types:
            baseline = cells.get((origin, kind)) if origin != "GLOBAL" else None
            bound_ids = set()
            if baseline:
                bound_ids.update(baseline.get("assetIds") or [])
                bound_ids.update(baseline.get("canonicalAssetIds") or [])
                bound_ids.update(baseline.get("candidateAssetIds") or [])
                bound_ids.update(baseline.get("sourceContractAssetIds") or [])
            for aid, asset in manifest_assets.items():
                if (origin, kind) in binding_map(asset):
                    bound_ids.add(aid)
            for aid in sorted(bound_ids):
                if aid in asset_index: links[aid].add(f"{origin}/{kind}")
            leads = sorted(discovery.get((origin, kind), []), key=lambda r: r["assetId"])
            exact = [aid for aid in sorted(bound_ids) if aid in manifest_assets and (origin, kind) in binding_map(manifest_assets[aid])]
            candidates = sorted({r["assetId"] for r in leads if r["assetId"] in asset_index} - set(exact))
            unresolved_refs = sorted(set(bound_ids) - set(asset_index))
            known_assets = {aid for aid in bound_ids if aid in asset_index}
            row_bound_ids = sorted(known_assets)
            cell_rows.append({
                "origin": origin, "type": kind, "requirementId": f"{origin}/{kind}",
                "sources": {"boundAssetIds": row_bound_ids, "unresolvedAssetReferences": unresolved_refs, "candidateAssetIds": candidates, "allSourceAssetIds": sorted(known_assets | set(candidates)), "sourceURLs": sorted({url for aid in known_assets | set(candidates) for url in asset_index.get(aid, {}).get("sourceURLs", [])}), "sharedSourceAssetIds": sorted(aid for aid in candidates if asset_index.get(aid, {}).get("scope") == "global-shared-candidate")},
                "discoveryStatus": "identified-candidates" if candidates else ("identified-bound" if bound_ids else "discovery-required"),
                "acquisitionStatus": "verified-original-evidence" if any(asset_index.get(aid, {}).get("custody", {}).get("state") == "verified-current" for aid in bound_ids) else ("identified-not-fetched" if candidates or bound_ids else "not-started"),
                "parseStatus": "no-usable-record-evidence-in-current-register",
                "parsedRecordIds": [], "applicability": "unresolved" if origin == "GLOBAL" else (baseline.get("retainedStatus", "unknown") if baseline else "unknown"),
                "evidence": {"baselineCell": baseline, "exactTypeBindings": exact, "discoveryLeads": leads[:60], "discoveryLeadCount": len(leads), "leadsTruncated": len(leads) > 60, "coverageNotInferred": True},
                "gaps": (["No reviewed source candidate is bound to this origin/type."] if not candidates and not bound_ids else []) + (["Applicable content, release scope, rights, and actual parsed records have not been established by the inventory projection."] if not exact else []),
                "nextActions": ["Verify the candidate's type and described countries/markets against publisher release documentation; reject URL-hosting-country inference.", "Resolve actual files, bulk exports or permitted API routes; record request parameters, release and every relevant mirror without conflating releases.", "Establish the applicable access/licence conditions and required attribution; implement the bounded acquisition contract without clearing existing holds.", "Fetch the authorized unique release (complete pagination/multipart; reuse only verified originals), hash-verify the local original, then parse source-faithful records and link their IDs/citations here."],
            })
    # Asset inverse links are generated from all manifest evidence-backed bindings
    # and baseline cells, with GLOBAL omitted unless a record explicitly binds it.
    for row in asset_rows:
        row["coverageLinks"] = sorted(links.get(row["assetId"], set()))

    # Add unresolved cell references as explicit source-discovery work. Their
    # identifiers can be joined by a future pinned register refresh, but do not
    # fabricate an asset record or assert source identity from the ID alone.
    for (country, kind), baseline in cells.items():
        for aid in sorted(set(baseline.get("assetIds", [])) | set(baseline.get("canonicalAssetIds", [])) | set(baseline.get("candidateAssetIds", [])) | set(baseline.get("sourceContractAssetIds", []))):
            if aid not in asset_index:
                discovery[(country, kind)].append({"assetId": aid, "status": "unresolved-reference", "evidence": "reference occurs in the pinned requirement cell but does not resolve to the runtime asset inventory or delivery-ledger IDs", "nextAction": "Resolve this reference against pinned source registry records and publisher/release/request parameters; do not merge by description or URL alone."})
    blockers = []
    for row in asset_rows:
        if row["sourceStatus"] in {"externally-restricted", "identified-not-fetched", "discovery-only", "discovered-unbound", "candidate-evidence-only"} or row["gaps"]:
            blockers.append({"assetId": row["assetId"], "publisher": row["publisher"], "citation": row["citation"], "sourceURLs": row["sourceURLs"], "status": row["sourceStatus"], "manifestDisposition": row["manifestDisposition"], "accessConditions": row["accessConditions"], "evidence": row["evidence"], "gaps": row["gaps"] or ["Not yet admitted as an acquisition/parse asset."], "requiredNextAction": row["nextAction"], "affectedCoverageLinks": row["coverageLinks"]})
    cell_counts = collections.Counter(row["discoveryStatus"] for row in cell_rows)
    type_counts = {kind: sum(row["type"] == kind for row in cell_rows) for kind in types}
    asset_counts = collections.Counter(row["sourceStatus"] for row in asset_rows)
    report = {
        "schemaVersion": "offmenu-origin-type-coverage-register/1",
        "generatedBy": "scripts/build-origin-type-register.py",
        "sourcePins": {str(path.relative_to(ROOT)): {"sha256": digest(raw), "bytes": len(raw)} for path, raw in ((MANIFEST, manifest_raw), (COUNTRY_REGISTER, matrix_raw), (DELIVERY_LEDGER, ledger_raw), (ENRICHMENT_REGISTER, research_raw))},
        "requirements": {"origins": 250, "countryOrigins": 249, "globalScopes": 1, "globalIsSharedNotCountry": True, "types": types, "typeCount": len(types), "requiredEntries": 3250, "coverageDefinition": "A covered entry requires at least one applicable, cited source asset and actual source-faithful parsed record IDs, with scope and rights established. URL presence, landing-page access, source binding, retained metadata, or parse-ready status alone do not satisfy it."},
        "status": "complete-matrix-discovery-incomplete-coverage-not-established",
        "counts": {"originTypeEntries": len(cell_rows), "entriesByDiscoveryStatus": dict(sorted(cell_counts.items())), "entriesWithEvidenceBoundAssets": sum(bool(r["sources"]["boundAssetIds"]) for r in cell_rows), "entriesWithDiscoveryCandidates": sum(bool(r["sources"]["candidateAssetIds"]) for r in cell_rows), "entriesWithParsedRecords": sum(bool(r["parsedRecordIds"]) for r in cell_rows), "entriesComplete": 0, "uniqueAssetsInRegister": len(asset_rows), "assetsByStatus": dict(sorted(asset_counts.items())), "uniqueAssetsFetchedAndVerified": 0, "uniqueAssetsReusedAndVerified": 0, "uniqueAssetsParsedWithUsableRecords": 0, "uniqueAssetsFailed": sum(a.get("disposition") == "held" for a in asset_rows), "uniqueAssetsExternallyBlocked": sum(a["sourceStatus"] == "externally-restricted" for a in asset_rows), "uniqueSourceURLs": len({url for a in asset_rows for url in a["sourceURLs"]}), "manyToManyCoverageLinks": sum(len(a["coverageLinks"]) for a in asset_rows), "distinctAssetIdentityPolicy": "runtime asset IDs remain separate releases; registry URL aliases are preserved, not collapsed by URL or hostname"},
        "coverageByType": {kind: {"entries": type_counts[kind], "entriesWithBoundAssets": sum(r["type"] == kind and bool(r["sources"]["boundAssetIds"]) for r in cell_rows), "entriesWithCandidates": sum(r["type"] == kind and bool(r["sources"]["candidateAssetIds"]) for r in cell_rows), "entriesWithParsedRecords": 0, "complete": 0} for kind in types},
        "origins": origins,
        "types": [{"type": kind, "discoveryTerms": list(TYPE_TERMS[kind])} for kind in types],
        "coverage": cell_rows,
        "assets": asset_rows,
        "blockers": blockers,
        "limitations": ["This deterministic offline build reconciles current repository records only; it is not fresh web discovery.", "Discovery classification is a candidate-generation heuristic and is never treated as a reviewed binding or a permission grant.", "The baseline snapshot includes 249 countries × 13 types (3,237 cells); GLOBAL is represented separately and each GLOBAL/type cell intentionally remains unbound until geographic applicability is evidenced.", "Runtime asset IDs, ledger source IDs, and the separate older research catalog IDs are not joined by description; the complete research catalog is retained as distinct registered source leads until publisher/release/request and hash evidence permits identity reconciliation.", "A missing discovery candidate means no matching candidate exists in the reconciled inputs, not a finding that the source does not exist; all such entries remain queued for explicit discovery.", "No source bodies were fetched, no network access was performed, and no new local originals or parsed records were created by this generator."],
    }
    validate(report, manifest)
    return report


def validate(report: dict, manifest: dict | None = None):
    origins, types, rows, assets = report["origins"], report["requirements"]["types"], report["coverage"], report["assets"]
    if len(origins) != 250 or "GLOBAL" not in origins or origins["GLOBAL"]["scope"] != "shared": raise ValueError("origin matrix invalid")
    expected = {(origin, kind) for origin in origins for kind in types}
    actual = [(row["origin"], row["type"]) for row in rows]
    if len(rows) != 3250 or set(actual) != expected or len(set(actual)) != len(actual): raise ValueError("origin/type cardinality invalid")
    aids = [a["assetId"] for a in assets]
    if len(aids) != len(set(aids)): raise ValueError("asset IDs not unique")
    by_id = {a["assetId"]: a for a in assets}
    for row in rows:
        for aid in row["sources"]["allSourceAssetIds"]:
            if aid not in by_id: raise ValueError(f"unknown linked asset {aid}")
        if row["origin"] == "GLOBAL" and row["sources"]["sharedSourceAssetIds"]:
            for aid in row["sources"]["sharedSourceAssetIds"]:
                if by_id[aid]["countryFanoutAllowed"] is not False: raise ValueError("global fanout must remain disabled")
        if row["parsedRecordIds"] and row["parseStatus"] not in {"parsed-usable", "parsed-partial"}: raise ValueError("record evidence/status mismatch")
    for asset in assets:
        if not set(asset["coverageLinks"]) <= {f"{o}/{t}" for o, t in expected}: raise ValueError("unknown inverse coverage link")
        if asset["scope"] == "global-shared-candidate" and asset["countryFanoutAllowed"] is not False: raise ValueError("global fanout invalid")
    if report["counts"]["originTypeEntries"] != len(rows) or report["counts"]["uniqueAssetsInRegister"] != len(assets): raise ValueError("reported count mismatch")
    if manifest and len(manifest["cells"]) != 3237: raise ValueError("baseline country matrix mismatch")
    return True


def write_outputs(report: dict, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    (out / "coverage-register.json").write_bytes(canonical(report))
    # Convenient independently consumable flat files, preserving full records.
    (out / "origin-type-coverage.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in report["coverage"]), encoding="utf-8")
    (out / "unique-assets.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in report["assets"]), encoding="utf-8")
    (out / "source-blockers.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in report["blockers"]), encoding="utf-8")
    return {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())} for p in sorted(out.iterdir()) if p.is_file()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="validate existing output against a fresh deterministic build")
    args = parser.parse_args(argv)
    report = build()
    if args.check:
        path = args.output_dir / "coverage-register.json"
        existing = json.loads(path.read_text(encoding="utf-8"))
        validate(existing)
        if canonical(existing) != canonical(report): raise SystemExit("coverage register is stale; rerun without --check")
        print(json.dumps({"status": "verified", "coverageEntries": len(report["coverage"]), "uniqueAssets": len(report["assets"]), "files": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())} for p in sorted(args.output_dir.iterdir()) if p.is_file()}}, sort_keys=True))
        return 0
    print(json.dumps({"status": "written", "files": write_outputs(report, args.output_dir), "counts": report["counts"]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(f"register-build-failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
