"""Bounded manifest-locator recipe -> explicit ingredient mention -> quantity."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import io
import json
from pathlib import Path
import time

T = "urn:offmenu:type:"
R = "urn:offmenu:relation:"
P = "urn:offmenu:property:"
CORE_MANIFEST = "c15005b224ae18c1e660837c6ac9fab88beb0b4d53ce34db6a5a87f12f6d919d"
CORE_CONTRACT = "c7d1ff1646848b8df2fda3672058c534da63ecae539df338b3f2e9aba01fb749"
CORE_PROOF = "9ab94d1566f9a3c784baea3621059a954736dd9b08899d718ebb6d7f5c38fbec"
INSPECTOR_CODE = "55cc3e67bd01fd887b2d1375bb3ed4439c330e56686b3ed4e6be4ffde66b8d31"
SELECTED_MANIFEST = "8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e"
SCHEMA = "89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c"
CONTRACT = "b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa"
BASE = Path("/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1")
PACKAGE = Path("/offmenu-corpus/common-data-reviewed-package-20261014")
MAX_ASSET = 5235571
MAX_PACKETS = 500
MAX_PACKET = 8 * 1024 * 1024
BLOCKED_EDGE = {"superseded", "conflicting", "needs-transcription", "unknown"}
BLOCKED_QUANTITY = {"superseded", "conflicting", "needs-transcription"}


class EvidenceError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise EvidenceError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def decode(data):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(_):
        raise EvidenceError("nonfinite JSON")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def checked(root, entry, cap):
    key = Path(entry["key"])
    require(not key.is_absolute() and ".." not in key.parts
            and str(key) == entry["key"] and key.parts, "unsafe asset key")
    path = root / key
    require(path.is_absolute() and path.resolve(strict=True) == path, "aliased input forbidden")
    require(type(entry["bytes"]) is int and 0 <= entry["bytes"] <= cap
            and path.stat().st_size == entry["bytes"], "asset size differs/exceeds bound")
    data = path.read_bytes()
    require(len(data) == entry["bytes"] and hashlib.sha256(data).hexdigest() == entry["sha256"],
            "asset byte digest differs")
    return data


def pinned_json(path, pin):
    require(path.is_absolute() and path.resolve(strict=True) == path, "aliased metadata forbidden")
    require(path.stat().st_size <= 16 * 1024 * 1024, "metadata bound exceeded")
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == pin, "metadata byte digest differs")
    return decode(data)


def indexed(rows):
    require(isinstance(rows, list), "row array required")
    result = {}
    for row in rows:
        identity = row["id"]
        require(isinstance(identity, str) and identity and identity not in result, "ambiguous row identity")
        result[identity] = row
    return result


def envelope(status):
    return {"schemaVersion": "offmenu-recipe-component-consumer/1", "status": status,
            "records": [], "acceptedIngredientIdentityJoins": 0,
            "identityEffect": "none", "nutritionAggregationEligible": False,
            "automaticPlanningEligible": False, "servedApplicationActivation": False,
            "publicationEligible": False, "portionScalingPerformed": False,
            "magnitudeConversionPerformed": False, "inferredStepIngredientMembership": False,
            "confidence": {"status": "not-calibrated", "probability": None}}


def adapt_recipe(packet, recipe_id, source_id, release, selection, *, include_candidates=False):
    """Exact source-normalized edges only. Input packets must be schema validated."""
    out = envelope("candidate-opt-in-required")
    if include_candidates is not True:
        return out
    require(all(isinstance(v, str) and v for v in (recipe_id, source_id, release)),
            "exact resource/source/release key required")
    require(packet["schemaVersion"] == "offmenu-common/1", "selected packet schema differs")
    resources = indexed(packet["resources"]); facts = indexed(packet["assertions"])
    edges = indexed(packet["relations"]); citations = indexed(packet["citations"])
    recipe = resources.get(recipe_id)
    if recipe is None or recipe["type"] != T + "RecipeVariant":
        return envelope("recipe-resource-not-found")
    cid_set = set(recipe["citationIds"])
    require(cid_set and len(cid_set) == len(recipe["citationIds"]), "unique recipe citations required")
    require(all(cid in citations for cid in cid_set), "recipe citation unresolved")
    originals = [citations[cid] for cid in recipe["citationIds"]]
    if any(c["sourceId"] != source_id or c.get("revisionId") is None
           or str(c["revisionId"]) != release for c in originals):
        return envelope("source-release-key-not-found")
    scope = recipe["scope"]
    require(scope.get("visibility") == "public", "selected public recipe required")
    def bound(row):
        require(row["scope"] == scope and row["citationIds"]
                and len(row["citationIds"]) == len(set(row["citationIds"]))
                and set(row["citationIds"]) == cid_set, "exact citation/scope binding differs")
        require(all(citations[cid]["scope"] == scope for cid in row["citationIds"]),
                "citation scope differs")
    bound(recipe)
    selected = [e for e in edges.values()
                if e["subjectId"] == recipe_id and e["predicateId"] == R + "usesIngredient"]
    if not selected:
        return envelope("no-source-declared-component-edge")
    if len({e["objectId"] for e in selected}) != len(selected):
        return envelope("ambiguous-component-edge")
    output = []
    for edge in sorted(selected, key=lambda row: row["id"]):
        bound(edge)
        if edge["status"] in BLOCKED_EDGE:
            return envelope("declared-component-edge-unresolved")
        component = resources.get(edge["objectId"])
        if component is None or component["type"] != T + "IngredientMention":
            return envelope("declared-component-endpoint-unresolved")
        bound(component)
        quantities = [a for a in facts.values()
                      if a["subjectId"] == component["id"] and a["propertyId"] == P + "requiredQuantity"]
        if len(quantities) != 1:
            return envelope("required-quantity-not-supplied" if not quantities else "ambiguous-component-quantity")
        assertion = quantities[0]; bound(assertion)
        q = assertion["value"]
        if assertion["status"] in BLOCKED_QUANTITY or q.get("kind") != "quantity":
            return envelope("required-quantity-unresolved")
        require(q["value"] is None or type(q["value"]) in (int, float), "numeric/unknown quantity required")
        preparation_markers = [v for v in q["qualifiers"] if v.startswith("state:")]
        # Keep each complete source object; do not interpret labels, units, state
        # or normalized candidate membership as accepted culinary identity.
        row = {"recipeId": recipe_id, "componentId": component["id"],
               "relationshipEvidenceKind": "copied-source-normalized-explicit-edge",
               "sourceEdge": deepcopy(edge), "sourceComponent": deepcopy(component),
               "quantityAssertion": deepcopy(assertion), "quantity": deepcopy(q),
               "quantityValueStatus": "unknown" if q["value"] is None else "reported",
               "sourceEdgeCanonicalSha256": digest(edge),
               "sourceComponentCanonicalSha256": digest(component),
               "quantityAssertionCanonicalSha256": digest(assertion),
               "preparation": {"status": "source-carried-not-qualified" if q.get("preparationStateId") or preparation_markers else "not-supplied",
                               "sourcePreparationStateId": q.get("preparationStateId"),
                               "sourceQualifiers": deepcopy(q["qualifiers"]),
                               "acceptedCanonicalPreparation": None},
               "ingredientIdentity": {"status": "not-accepted-by-this-consumer", "canonicalIngredientId": None}}
        row["id"] = "urn:offmenu:recipe-component-context:" + digest(row)
        output.append(row)
    yields = [a for a in facts.values() if a["subjectId"] == recipe_id and a["propertyId"] == P + "yield"]
    for assertion in yields:
        bound(assertion)
    out.update(status="source-declared-component-candidates", records=output,
               recipeResource=deepcopy(recipe), citations=deepcopy(originals),
               recipeResourceCanonicalSha256=digest(recipe),
               citationCanonicalSha256={c["id"]: digest(c) for c in originals},
               recipeYield={"status": "not-supplied" if not yields else "ambiguous" if len(yields) > 1 else "source-reported-not-qualified",
                            "assertions": deepcopy(sorted(yields, key=lambda row: row["id"]))},
               sourceSelection=deepcopy(selection),
               inputPacketCanonicalSha256=digest(packet),
               scope=deepcopy(scope))
    return out


class RecipeComponentConsumer:
    """A bounded reader, consumed by lookup; never imports or runs the old scan."""
    def __init__(self, package=PACKAGE, base=BASE):
        self.package, self.base = Path(package), Path(base)
        self.entries = None; self.validator = None; self._cache = None

    def _prepare(self):
        if self.entries is not None:
            return
        manifest = pinned_json(self.package / "manifest.json", CORE_MANIFEST)
        derived = self.base / "north-star-derived-20261028"
        proof = pinned_json(derived / "core-recipe-verified-v2/report.json", CORE_PROOF)
        require(proof["manifestByteSha256"] == CORE_MANIFEST
                and proof["sourceCodeSha256"] == INSPECTOR_CODE
                and proof["selectedSchemaSha256"] == SCHEMA and proof["identityAdmissionGranted"] is False,
                "retained recipe proof binding differs")
        entries = {e["key"]: e for e in manifest["files"]}
        require(len(entries) == len(manifest["files"]), "duplicate manifest entry")
        recipe_entries = [e for e in manifest["files"] if e["key"].startswith("recipes/") and "packets" in e]
        require(recipe_entries == proof["selectedAssets"] and len(recipe_entries) == 51,
                "accepted recipe asset selection differs")
        for entry in recipe_entries:
            require(entry["key"].endswith(".jsonl.gz") and type(entry["packets"]) is int
                    and 1 <= entry["packets"] <= MAX_PACKETS
                    and 0 <= entry["bytes"] <= MAX_ASSET, "recipe asset bounds differ")
        selected_root = self.base / "bulk-parallel"
        selected = pinned_json(selected_root / "manifest.json", SELECTED_MANIFEST)
        selected_entries = {e["key"]: e for e in selected["files"]}
        require(len(selected_entries) == len(selected["files"]), "duplicate selected manifest entry")
        contracts = []
        for root, table, contract_pin in ((self.package, entries, CORE_CONTRACT),
                                          (selected_root, selected_entries, CONTRACT)):
            for key, pin in (("schema.json", SCHEMA), ("contract.json", contract_pin)):
                require(table[key]["sha256"] == pin, "manifest-listed schema/contract pin differs")
                value = decode(checked(root, table[key], 128 * 1024))
                if key == "contract.json":
                    contracts.append(value)
                elif root == selected_root:
                    schema = value
        for category, names in (("types", ("RecipeVariant", "IngredientMention")),
                                ("relationshipVocabulary", ("usesIngredient",)),
                                ("sharedProperties", ("requiredQuantity", "yield"))):
            for name in names:
                require(contracts[0][category][name] == contracts[1][category][name],
                        "recipe/component definition differs between bound contracts")
        try:
            import jsonschema_rs
            validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
        except ImportError:
            import jsonschema
            validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        self.validator, self.entries = validator, {e["key"]: e for e in recipe_entries}

    def _packet(self, asset_key, ordinal):
        self._prepare()
        entry = self.entries.get(asset_key)
        require(entry is not None and type(ordinal) is int and 0 <= ordinal < entry["packets"],
                "exact manifest-listed packet locator required")
        if self._cache is not None and self._cache[:2] == (asset_key, ordinal):
            return self._cache[2]
        data = checked(self.package, entry, MAX_ASSET)
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            packet = None
            for n in range(ordinal + 1):
                line = stream.readline(MAX_PACKET + 1)
                require(line and len(line) <= MAX_PACKET, "packet missing/exceeds 8 MiB bound")
                if n == ordinal:
                    packet = decode(line)
        self.validator.validate(packet)
        self._cache = (asset_key, ordinal, packet)
        return packet

    def lookup(self, asset_key, packet_ordinal, recipe_id, source_id, release, *, include_candidates=False):
        if include_candidates is not True:
            return envelope("candidate-opt-in-required")
        packet = self._packet(asset_key, packet_ordinal)
        entry = self.entries[asset_key]
        selection = {"manifestByteSha256": CORE_MANIFEST, "assetKey": asset_key,
                     "assetSha256": entry["sha256"], "packetOrdinal": packet_ordinal,
                     "schemaByteSha256": SCHEMA, "sourceContractByteSha256": CORE_CONTRACT,
                     "selectedContractByteSha256": CONTRACT, "retainedCoreProofSha256": CORE_PROOF}
        return adapt_recipe(packet, recipe_id, source_id, release, selection, include_candidates=True)

    def _first_packet_locator(self):
        """Select at most one recipe from one packet of one pinned asset."""
        self._prepare()
        key = sorted(self.entries)[0]; packet = self._packet(key, 0)
        candidates = [r for r in packet["resources"] if r["type"] == T + "RecipeVariant"]
        if len(candidates) != 1:
            return None
        recipe = candidates[0]; citations = indexed(packet["citations"])
        originals = [citations[cid] for cid in recipe["citationIds"]]
        binding = {(c["sourceId"], str(c["revisionId"])) for c in originals if c.get("revisionId") is not None}
        if len(binding) != 1 or not all(c.get("revisionId") is not None for c in originals):
            return None
        source, release = next(iter(binding))
        return key, 0, recipe["id"], source, release


def exercise_one(consumer):
    started = time.monotonic()
    locator = consumer._first_packet_locator()
    require(locator is not None, "first selected packet has no unambiguous source recipe locator")
    result = consumer.lookup(*locator, include_candidates=True)
    require(result["status"] == "source-declared-component-candidates" and result["records"],
            "selected recipe has no complete explicit component/quantity path")
    rows = result["records"]
    return {"schemaVersion": "offmenu-recipe-component-proof/1", "status": "one-source-recipe-component-path-exercised",
            "recipeQueries": 1, "componentQuantityRecords": len(rows),
            "unknownQuantityCount": sum(r["quantity"]["value"] is None for r in rows),
            "zeroQuantityCount": sum(r["quantity"]["value"] == 0 for r in rows),
            "sourceAssertedEdgeCount": sum(r["sourceEdge"]["status"] == "source-asserted" for r in rows),
            "candidateEdgeCount": sum(r["sourceEdge"]["status"] == "candidate" for r in rows),
            "yieldAssertionCount": len(result["recipeYield"]["assertions"]),
            "missingPreparationCount": sum(r["preparation"]["status"] == "not-supplied" for r in rows),
            "sourceManifestSha256": CORE_MANIFEST, "retainedCoreProofSha256": CORE_PROOF,
            "schemaByteSha256": SCHEMA, "sourceContractByteSha256": CORE_CONTRACT,
            "selectedContractByteSha256": CONTRACT, "outputCanonicalSha256": digest(result),
            "acceptedIngredientIdentityJoins": 0, "nutritionAggregationEligible": False,
            "automaticPlanningEligible": False, "servedApplicationActivation": False,
            "publicationEligible": False, "candidateOptIn": True,
            "rawRowsExported": False, "lexicalIdentifiersExported": False,
            "elapsedSeconds": round(time.monotonic() - started, 6)}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--package", type=Path, default=PACKAGE)
    p.add_argument("--base", type=Path, default=BASE)
    p.add_argument("--proof-root", type=Path, required=True)
    args = p.parse_args(argv); root = args.proof_root
    require(root.is_absolute() and root.parent == args.base / "north-star-derived-20261028"
            and root.name.startswith("recipe-component-proof-v1-")
            and root.parent.resolve(strict=True) == root.parent and not root.exists(),
            "fresh disjoint proof root required")
    result = exercise_one(RecipeComponentConsumer(args.package, args.base))
    root.mkdir(mode=0o700)
    with (root / "integration-proof.json").open("x", encoding="utf-8") as handle:
        handle.write(canonical(result).decode() + "\n")
    print(canonical(result).decode())


if __name__ == "__main__":
    main()
