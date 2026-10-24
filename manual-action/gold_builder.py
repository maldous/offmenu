"""Pure bounded common-data to relational proposal. No admission or I/O authority."""
import copy
import hashlib
import json
from fractions import Fraction

DOMAINS = ("barcodes", "ingredients", "recipes", "dietary", "suppliers", "citations")
TABLE_COLUMNS = {
 "gold_runs": ("run_id", "packet_sha256", "qualification_sha256", "data_class", "watermark_json"),
 "gold_citations": ("citation_id", "payload_json"),
 "gold_entities": ("entity_id", "resource_id", "domain", "entity_type", "state", "payload_json"),
 "gold_occurrences": ("occurrence_id", "domain", "source_key", "source_version", "record_id", "content_sha256", "normalized_artifact_sha256", "committed_watermark", "state", "payload_json"),
 "gold_entity_occurrences": ("entity_id", "occurrence_id"),
 "gold_texts": ("text_id", "source_text_id", "entity_id", "occurrence_id", "language", "original_text", "english_text", "state", "evidence_json"),
 "gold_claims": ("claim_id", "assertion_id", "entity_id", "property_id", "state", "payload_json"),
 "gold_edges": ("edge_id", "relation_id", "subject_id", "predicate_id", "object_id", "state", "payload_json"),
 "gold_metrics": ("metric_id", "name_en", "dimension", "canonical_unit_id", "state"),
 "gold_observations": ("observation_id", "claim_id", "metric_id", "entity_id", "kind", "state", "context_json", "original_json", "comparable_json", "payload_json"),
 "gold_support": ("support_id", "target_kind", "target_id", "citation_id", "support_scope", "evidence_sha256"),
 "gold_unbound_support": ("reference_id", "target_kind", "target_id", "citation_id", "reason"),
 "gold_comparisons": ("comparison_id", "disposition", "reason", "evidence_sha256"),
 "gold_comparison_observations": ("comparison_id", "observation_id"),
 "gold_holds": ("hold_id", "target_kind", "target_id", "reason"),
}
INSERT_ORDER = tuple(TABLE_COLUMNS)
CONTEXT_FIELDS = ("country", "cut", "fat", "preparation", "raw_cooked", "basis", "source_date", "method", "uncertainty")
RELATION_TYPES = {"mentions", "canonical_ingredient", "represents", "contains", "brand", "manufacturer", "parent", "retailer", "provider", "recall_applies_to", "nutrition_of"}
SOURCE_NUMERATOR_UNITS = {"kg": "mass", "g": "mass", "mg": "mass", "µg": "mass",
                          "L": "volume", "mL": "volume",
                          "J": "energy", "kJ": "energy", "kcal": "energy"}

def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def _bound(value, depth=0, budget=None):
    if budget is None:
        budget = [100000]
    budget[0] -= 1
    if depth > 32 or budget[0] < 0:
        raise ValueError("JSON depth/node bound")
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            raise ValueError("JSON keys must be strings")
        for item in value.values():
            _bound(item, depth + 1, budget)
    elif type(value) is list:
        for item in value:
            _bound(item, depth + 1, budget)
    elif type(value) not in (str, int, float, bool, type(None)):
        raise ValueError("native JSON only")

def digest(value):
    _bound(value)
    return hashlib.sha256(_json(value).encode()).hexdigest()

def _pin(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)

ALTERNATIVE_SCOPE_FIELDS = {"recipeId", "mentionId", "sourceKey", "sourceVersion", "recordId", "contentSha256"}
LEGACY_ALTERNATIVE_FIELDS = {"alternativeGroupId", "branchId", "groupId"}


def alternative_scope_valid(scope):
    return (type(scope) is dict and set(scope) == ALTERNATIVE_SCOPE_FIELDS
            and all(type(v) is str and bool(v.strip()) for v in scope.values())
            and _pin(scope["contentSha256"]))


def relation_condition(relation):
    """None means absent; malformed/present-null conditions never mean unconditional."""
    if LEGACY_ALTERNATIVE_FIELDS.intersection(relation):
        raise ValueError("untyped alternative metadata")
    if "condition" not in relation:
        return None
    c = relation["condition"]
    if (type(c) is not dict or set(c) != {"kind", "groupId", "branchId", "sourceScope"}
        or c["kind"] != "selected-alternative"
        or any(type(c[k]) is not str or not c[k].strip() for k in ("groupId", "branchId"))
        or not alternative_scope_valid(c["sourceScope"])
        or relation.get("predicateId") != "canonical_ingredient"
        or c["sourceScope"]["mentionId"] != relation.get("subjectId")):
        raise ValueError("invalid alternative condition")
    return c


def alternative_group_valid(relations):
    """One exclusive group per source mention; all declared branches stay visible."""
    try:
        conditions = [relation_condition(r) for r in relations]
    except ValueError:
        return False
    if not any(conditions):
        # Multiple incompatible canonical identities are not an implicit AND/OR.
        # A legacy packet missing both conditions must also fail closed.
        return len({r.get("objectId") for r in relations}) <= 1
    if not all(conditions):
        return False
    return (len({_json(c["sourceScope"]) for c in conditions}) == 1
            and len({c["groupId"] for c in conditions}) == 1
            and len({c["branchId"] for c in conditions}) >= 2
            and len({c["branchId"] for c in conditions}) == len(conditions)
            and len({r["objectId"] for r in relations}) == len(relations))

def _uid(*parts):
    return digest(list(parts))

def _index(items, key):
    out = {}
    for item in items:
        identity = item[key]
        if not isinstance(identity, str) or not identity or identity in out:
            raise ValueError("missing or duplicate " + key)
        out[identity] = item
    return out

def build_gold_slice(packet, *, qualifications):
    return _build_gold_slice(packet, qualifications=qualifications, recipe_source_only=False)


def build_recipe_source_subset(packet, *, qualifications):
    """Propose attributable recipe source facts without claiming an application chain.

    This is a trusted caller choice, never a field supplied by a source packet.
    Canonical identity, products, nutrition and private domains are excluded.
    Structured actions and actual admission still require their own qualification.
    """
    return _build_gold_slice(packet, qualifications=qualifications, recipe_source_only=True)


def build_product_source_subset(packet, *, qualifications):
    """Propose source-identifier lookup, optional class fits and label records.

    Trusted qualifications select each source identifier and observation basis.
    This never claims a recipe chain, global identifier ownership, current stock,
    resolved businesses or actual admission. Source packets cannot select it.
    """
    return _build_gold_slice(packet, qualifications=qualifications,
                             recipe_source_only=False, product_source_only=True)


def _build_gold_slice(packet, *, qualifications, recipe_source_only, product_source_only=False):
    """Return deterministic proposed rows and explicit holds; never write a DB.

    Independent reviewers select qualifications; hashes bind those decisions, not
    source truth. Generic relationships remain held until typed support exists.
    """
    _bound(packet); _bound(qualifications)
    if len(_json(packet).encode()) > 4194304 or len(_json(qualifications).encode()) > 4194304:
        raise ValueError("input exceeds 4 MiB")
    if packet.get("schema_version") != "offmenu.gold-input/1":
        raise ValueError("input schema")
    if qualifications.get("schema_version") != "offmenu.gold-qualification/1":
        raise ValueError("qualification schema")
    if qualifications.get("packet_sha256") != digest(packet) or not _pin(qualifications.get("policy_sha256")):
        raise ValueError("qualification packet/policy binding")
    if packet.get("data_class") not in ("synthetic", "real-qualified"):
        raise ValueError("data class")
    common = packet["common"]
    if common.get("schemaVersion") != "offmenu-common/1":
        raise ValueError("common schema")
    if recipe_source_only:
        if packet.get("metrics") or packet.get("observations") or qualifications.get("comparisons"):
            raise ValueError("recipe source subset excludes nutrition and comparisons")
        if any(s.get("domain") not in {"recipes", "ingredients"} for s in packet.get("watermark", {}).get("domains", [])):
            raise ValueError("recipe source subset domain")
        if any(r.get("type") not in {"recipe", "ingredient-mention"} for r in common.get("resources", [])):
            raise ValueError("recipe source subset excludes canonical identity and other entities")
        if any(r.get("predicateId") != "mentions" for r in common.get("relations", [])):
            raise ValueError("recipe source subset supports source mentions only")
    if product_source_only:
        if qualifications.get("comparisons"):
            raise ValueError("product source subset excludes comparisons")
        if any(s.get("domain") not in {"barcodes", "ingredients"} for s in packet.get("watermark", {}).get("domains", [])):
            raise ValueError("product source subset domain")
        if any(r.get("type") not in {"barcode-product", "ingredient"} for r in common.get("resources", [])):
            raise ValueError("product source subset excludes recipes, mentions and other entities")
        if any(r.get("predicateId") != "represents" for r in common.get("relations", [])):
            raise ValueError("product source subset supports direct class fits only")
    rows = {name: [] for name in TABLE_COLUMNS}
    def add(table, **row):
        if set(row) != set(TABLE_COLUMNS[table]):
            raise ValueError("internal row columns " + table)
        rows[table].append(row)
    def hold(kind, identity, reason):
        row = dict(hold_id=_uid(kind, identity, reason), target_kind=kind, target_id=identity, reason=reason)
        if row not in rows["gold_holds"]:
            rows["gold_holds"].append(row)
    water = packet["watermark"]
    if not _pin(water.get("eligible_manifest_sha256")):
        raise ValueError("manifest pin")
    snapshots = _index(water["domains"], "domain")
    if any(d not in DOMAINS for d in snapshots):
        raise ValueError("private or unknown domain")
    for snap in snapshots.values():
        if not _pin(snap.get("manifest_sha256")) or not snap.get("snapshot_id") or not snap.get("committed_watermark"):
            raise ValueError("snapshot evidence")
    run_id = _uid(digest(packet), digest(qualifications))
    run_water = water
    if recipe_source_only:
        run_id = _uid("recipe-source-subset/1", digest(packet), digest(qualifications))
        run_water = dict(water, admission_profile="recipe-source-subset/1")
    if product_source_only:
        run_id = _uid("product-source-subset/1", digest(packet), digest(qualifications))
        run_water = dict(water, admission_profile="product-source-subset/1")
    add("gold_runs", run_id=run_id, packet_sha256=digest(packet), qualification_sha256=digest(qualifications), data_class=packet["data_class"], watermark_json=_json(run_water))
    citations = _index(common.get("citations", []), "id")
    for cid, citation in citations.items():
        if citation.get("scope", {}).get("visibility") != "public":
            raise ValueError("nonpublic citation")
        add("gold_citations", citation_id=cid, payload_json=_json(citation))
    supports = qualifications.get("supports", [])
    def supported(kind, identity, cids, scopes):
        valid = False
        for cid in cids:
            matches = [s for s in supports if s.get("target_kind") == kind and s.get("target_id") == identity and s.get("citation_id") == cid and s.get("support_scope") in scopes and _pin(s.get("evidence_sha256"))]
            if cid in citations and matches:
                valid = True
                for s in matches:
                    addrow = dict(support_id=_uid(kind, identity, cid, s["support_scope"], s["evidence_sha256"]), target_kind=kind, target_id=identity, citation_id=cid, support_scope=s["support_scope"], evidence_sha256=s["evidence_sha256"])
                    if addrow not in rows["gold_support"]:
                        rows["gold_support"].append(addrow)
            else:
                reason = "missing citation" if cid not in citations else "missing scoped support"
                addrow = dict(reference_id=_uid(kind, identity, cid, reason), target_kind=kind, target_id=identity, citation_id=cid, reason=reason)
                if addrow not in rows["gold_unbound_support"]:
                    rows["gold_unbound_support"].append(addrow)
                hold(kind, identity, reason)
        if not valid:
            hold(kind, identity, "no qualified scoped citation")
        return valid and all(cid in citations and any(s.get("target_kind") == kind and s.get("target_id") == identity and s.get("citation_id") == cid and s.get("support_scope") in scopes and _pin(s.get("evidence_sha256")) for s in supports) for cid in cids)
    occurrences = _index(packet.get("occurrences", []), "occurrence_id")
    records = _index(qualifications.get("records", []), "occurrence_id")
    occurrence_good = {}
    for oid, occurrence in occurrences.items():
        domain = occurrence["domain"]
        if domain not in snapshots:
            raise ValueError("occurrence outside selected domain snapshot")
        if not _pin(occurrence.get("content_sha256")) or occurrence.get("committed_watermark") != snapshots[domain]["committed_watermark"]:
            raise ValueError("occurrence content/watermark binding")
        artifact = occurrence.get("normalized_artifact_sha256")
        if not _pin(artifact) and not (domain == "citations" and artifact is None):
            raise ValueError("normalized artifact pin")
        q = records.get(oid, {})
        good = all(q.get(k) == occurrence.get(k) for k in ("content_sha256", "normalized_artifact_sha256", "committed_watermark")) and q.get("rights_state") == "permitted" and all(_pin(q.get(k)) for k in ("operation_evidence_sha256", "review_evidence_sha256"))
        occurrence_good[oid] = good
        if not good:
            hold("occurrence", oid, "record operation rights/review unqualified")
        add("gold_occurrences", occurrence_id=oid, domain=domain, source_key=occurrence["source_key"], source_version=occurrence["source_version"], record_id=occurrence["record_id"], content_sha256=occurrence["content_sha256"], normalized_artifact_sha256=artifact, committed_watermark=occurrence["committed_watermark"], state="verified" if good else "held", payload_json=_json(occurrence))
    def field_english(value):
        if isinstance(value, dict):
            if value.get("kind") == "text" and value.get("language") != "en":
                return False
            return all(field_english(v) for v in value.values())
        if isinstance(value, list):
            return all(field_english(v) for v in value)
        return True
    def qualified_cache(e, selected, occurrence, resource_id, binding, text):
        if not selected:
            return False
        source = e.get("source", {}); scope = e.get("scope", {})
        rights = e.get("rights", {}); validation = e.get("validation", {})
        return (selected.get("evidence_sha256") == digest(e)
            and selected.get("expected_source") == source
            and selected.get("expected_scope") == scope
            and source.get("recordId") == occurrence["record_id"]
            and source.get("locale") == text.get("language")
            and scope.get("domain") == occurrence["domain"]
            and scope.get("entityId") == resource_id
            and scope.get("fieldPointer") == binding.get("field_pointer")
            and rights.get("state") == "permitted" and rights.get("operation") == "translation"
            and rights.get("sourceBinding") == source and rights.get("scope") == scope
            and validation.get("state") == "passed" and validation.get("unsupportedFacts") is False
            and validation.get("requestKey") == e.get("requestKey")
            and validation.get("responseSHA256") == e.get("responseSHA256")
            and validation.get("evidencePin", {}).get("sha256") == selected.get("validation_evidence_sha256")
            and _pin(e.get("inputContentSHA256"))
            and all(e.get("versions", {}).get(k) for k in ("adapterVersion", "outputSchemaVersion", "rulesVersion"))
            and all(e.get("producer", {}).get(k) for k in ("id", "version"))
            and e.get("prompt", {}).get("version")
            and hashlib.sha256(e.get("prompt", {}).get("content", "").encode()).hexdigest() == e.get("prompt", {}).get("sha256"))
    resources = _index(common.get("resources", []), "id")
    entity_for = {}
    entity_good = {}
    bindings = packet.get("english_bindings", [])
    for rid, resource in resources.items():
        if resource.get("scope", {}).get("visibility") != "public":
            raise ValueError("nonpublic resource")
        owners = [(oid, o) for oid, o in occurrences.items() if rid in o.get("resource_ids", [])]
        tuples = {(o["domain"], o["source_key"], o["source_version"], o["record_id"]) for _, o in owners}
        if len(tuples) != 1:
            hold("resource", rid, "missing or ambiguous source occurrence")
            continue
        source = next(iter(tuples)); eid = _uid(*source, rid)
        entity_for[rid] = eid
        good = all(occurrence_good[oid] for oid, _ in owners)
        good = supported("resource", rid, resource.get("citationIds", []), {"record", "field"}) and good
        texts = resource.get("names", [])
        if not texts:
            good = False; hold("resource", rid, "missing English text")
        for text in texts:
            tid = text["id"]; original = text["value"]
            text_good = supported("text", tid, text.get("citationIds", []), {"field"})
            if hashlib.sha256(original.encode()).hexdigest() != text.get("sourceTextSha256"):
                text_good = False; hold("text", tid, "source text digest mismatch")
            english = original if text.get("language") == "en" else None
            evidence = None
            if english is None:
                candidates = [b for b in bindings if b.get("text_id") == tid and b.get("occurrence_id") in {oid for oid, _ in owners}]
                for b in candidates:
                    e = b.get("evidence", {}); o = occurrences[b["occurrence_id"]]
                    selected = next((c for c in qualifications.get("cache_entries", []) if c.get("request_key") == e.get("requestKey") and c.get("response_sha256") == e.get("responseSHA256") and c.get("occurrence_id") == b["occurrence_id"] and _pin(c.get("evidence_sha256")) and _pin(c.get("validation_evidence_sha256"))), None)
                    if qualified_cache(e, selected, o, rid, b, text) and e.get("schemaVersion") == "offmenu-gold-english-cache-evidence/1" and e.get("state") == "validated-cache-evidence" and e.get("dataClass") == packet["data_class"] and e.get("kind") == "translation" and e.get("targetLocale") == "en" and e.get("originalText") == original and e.get("source", {}).get("recordId") == o["record_id"] and e.get("scope", {}).get("fieldPointer") == b.get("field_pointer") and e.get("eligibleManifestPin", {}).get("sha256") == water["eligible_manifest_sha256"] and set(e.get("citationIds", [])) <= set(text.get("citationIds", [])):
                        english = e.get("englishText"); evidence = e; break
            text_good = text_good and isinstance(english, str) and bool(english)
            if not text_good:
                hold("text", tid, "English/field support unqualified")
            good = good and text_good
            add("gold_texts", text_id=_uid(eid, tid), source_text_id=tid, entity_id=eid, occurrence_id=owners[0][0], language=text.get("language"), original_text=original, english_text=english, state="verified" if text_good else "held", evidence_json=_json(evidence))
        entity_good[eid] = good
        add("gold_entities", entity_id=eid, resource_id=rid, domain=source[0], entity_type=resource["type"], state="verified" if good else "held", payload_json=_json(resource))
        for oid, _ in owners:
            add("gold_entity_occurrences", entity_id=eid, occurrence_id=oid)
    claims = _index(common.get("assertions", []), "id")
    claim_for = {}; claim_good = {}
    for aid, assertion in claims.items():
        if assertion.get("scope", {}).get("visibility") != "public":
            raise ValueError("nonpublic assertion")
        eid = entity_for.get(assertion["subjectId"]); cid = _uid("claim", aid, eid)
        good = supported("assertion", aid, assertion.get("citationIds", []), {"field"}) and bool(eid and entity_good[eid])
        # Textual claims require independent per-field English support too; no title-only admission.
        if not field_english(assertion.get("value", {})):
            good = False; hold("assertion", aid, "non-English assertion requires field translation qualification")
        if not good: hold("assertion", aid, "claim qualification incomplete")
        claim_for[aid] = cid; claim_good[aid] = good
        add("gold_claims", claim_id=cid, assertion_id=aid, entity_id=eid, property_id=assertion["propertyId"], state="verified" if good else "held", payload_json=_json(assertion))
    endpoints = {e["entity_id"]: (e["domain"], e["entity_type"]) for e in rows["gold_entities"]}
    allowed_endpoints = {
        "mentions": (("recipes", "recipe"), ("ingredients", "ingredient-mention")),
        "canonical_ingredient": (("ingredients", "ingredient-mention"), ("ingredients", "ingredient")),
        "represents": (("barcodes", "barcode-product"), ("ingredients", "ingredient")),
        "contains": (("barcodes", "barcode-product"), ("ingredients", "ingredient")),
        "recall_applies_to": (("dietary", "recall"), ("barcodes", "barcode-product")),
        "parent": (("suppliers", "supplier"), ("suppliers", "supplier")),
    }
    for role in ("brand", "manufacturer", "retailer", "provider"):
        allowed_endpoints[role] = (("barcodes", "barcode-product"), ("suppliers", "supplier"))
    for relation in _index(common.get("relations", []), "id").values():
        if relation.get("scope", {}).get("visibility") != "public":
            raise ValueError("nonpublic relationship")
        rid = relation["id"]; subject = entity_for.get(relation["subjectId"]); obj = entity_for.get(relation["objectId"])
        predicate = relation["predicateId"]
        good = supported("relation", rid, relation.get("citationIds", []), {"relationship"}) and bool(subject and obj and entity_good[subject] and entity_good[obj])
        if predicate not in allowed_endpoints or (endpoints.get(subject), endpoints.get(obj)) != allowed_endpoints.get(predicate):
            good = False; hold("relation", rid, "endpoint types/domain not qualified")
        if predicate not in RELATION_TYPES:
            good = False; hold("relation", rid, "unqualified relationship type")
        if predicate == "recall_applies_to":
            context = relation.get("context", {})
            if not all(context.get(k) for k in ("product", "lot", "jurisdiction", "date")):
                good = False; hold("relation", rid, "recall applicability scope incomplete")
        condition = None
        try:
            condition = relation_condition(relation)
            if condition:
                scope = condition["sourceScope"]
                recipe = entity_for.get(scope["recipeId"])
                owners = [o for o in occurrences.values() if scope["recipeId"] in o.get("resource_ids", [])]
                source_ok = any(occurrence_good[o["occurrence_id"]] and all(
                    o[k] == scope[v] for k, v in (("source_key", "sourceKey"),
                        ("source_version", "sourceVersion"), ("record_id", "recordId"),
                        ("content_sha256", "contentSha256"))) for o in owners)
                mention_owners = [o for o in occurrences.values() if relation["subjectId"] in o.get("resource_ids", [])]
                source_ok = source_ok and bool(mention_owners) and all(
                    o["source_key"] == scope["sourceKey"] and o["source_version"] == scope["sourceVersion"]
                    for o in mention_owners)
                # Resolve after the loop too: relation order cannot supply authority.
                if not source_ok or endpoints.get(recipe) != ("recipes", "recipe") or not entity_good.get(recipe):
                    good = False; hold("relation", rid, "alternative source scope not qualified")
        except ValueError as error:
            good = False; hold("relation", rid, str(error))
        if not good: hold("relation", rid, "relationship qualification incomplete")
        add("gold_edges", edge_id=_uid("edge", rid), relation_id=rid, subject_id=subject, predicate_id=predicate, object_id=obj, state=("conditional" if condition else "verified") if good else "held", payload_json=_json(relation))
    canonical_groups = {}
    for edge in rows["gold_edges"]:
        if edge["predicate_id"] == "canonical_ingredient":
            canonical_groups.setdefault(edge["subject_id"], []).append(edge)
    for edges in canonical_groups.values():
        relations = [json.loads(e["payload_json"]) for e in edges]
        valid = alternative_group_valid(relations)
        if valid and any("condition" in r for r in relations):
            scope = relations[0]["condition"]["sourceScope"]
            valid = any(e["predicate_id"] == "mentions" and e["state"] == "verified"
                        and e["subject_id"] == entity_for.get(scope["recipeId"])
                        and e["object_id"] == entity_for.get(scope["mentionId"])
                        for e in rows["gold_edges"])
        if not valid:
            for edge in edges:
                edge["state"] = "held"
                hold("relation", edge["relation_id"], "invalid/conflicting alternative group or source recipe association")
    metrics = _index(packet.get("metrics", []), "metric_id")
    metric_good = {}
    for mid, metric in metrics.items():
        good = supported("metric", mid, metric.get("citation_ids", []), {"definition"})
        metric_good[mid] = good
        add("gold_metrics", metric_id=mid, name_en=metric["name_en"], dimension=metric["dimension"], canonical_unit_id=metric.get("canonical_unit_id"), state="verified" if good else "held")
    observations = _index(packet.get("observations", []), "observation_id")
    for oid, obs in observations.items():
        aid = obs["assertion_id"]; mid = obs["metric_id"]
        if aid not in claims or mid not in metrics:
            raise ValueError("observation claim/metric missing")
        good = claim_good[aid] and metric_good[mid] and obs.get("kind") == "observed"
        # A qualified claim and metric separately do not bind their semantics.
        # Different source property IRIs need an independently selected mapping.
        property_id = claims[aid]["propertyId"]
        binding_ok = property_id == mid or any(
            b.get("property_id") == property_id and b.get("metric_id") == mid
            and _pin(b.get("evidence_sha256"))
            for b in qualifications.get("metric_bindings", []))
        original = claims[aid]["value"]
        dimension_ok = (original.get("kind") == "quantity"
            and original.get("dimension") not in (None, "unknown")
            and original.get("dimension") == metrics[mid].get("dimension"))
        if not binding_ok:
            good = False; hold("observation", oid, "claim property not bound to metric")
        if not dimension_ok:
            good = False; hold("observation", oid, "quantity dimension incompatible with metric")
        if product_source_only:
            basis = original.get("basis")
            basis_ok = (type(basis) is dict and basis.get("kind") == "quantity"
                and type(basis.get("value")) in (int, float) and basis["value"] > 0
                and (basis.get("unitId"), basis.get("dimension")) in {("g", "mass"), ("mL", "volume")}
                and obs.get("context", {}).get("basis") == basis
                and any(b.get("observation_id") == oid and b.get("basis") == basis
                        and _pin(b.get("evidence_sha256"))
                        for b in qualifications.get("observation_basis_bindings", [])))
            numerator_unit = original.get("unitId")
            source_value_ok = (type(original.get("value")) in (int, float)
                and type(numerator_unit) is str
                and SOURCE_NUMERATOR_UNITS.get(numerator_unit) == original.get("dimension")
                and numerator_unit == metrics[mid].get("canonical_unit_id"))
            subject = resources.get(claims[aid]["subjectId"], {})
            if not basis_ok or not source_value_ok or subject.get("type") != "barcode-product":
                good = False; hold("observation", oid, "source product value/basis qualification incomplete")
        if obs.get("comparable") is not None:
            comparable = obs["comparable"]; original = claims[aid]["value"]
            rules = [r for r in qualifications.get("unit_rules", []) if r.get("rule_id") == comparable.get("rule_id")]
            conversion_ok = False
            if len(rules) == 1:
                rule = rules[0]
                try:
                    conversion_ok = (original.get("kind") == "quantity"
                        and original.get("dimension") not in (None, "unknown")
                        and rule.get("dimension") == original.get("dimension") == metrics[mid]["dimension"]
                        and rule.get("from_unit_id") == original.get("unitId")
                        and rule.get("to_unit_id") == comparable.get("unit_id") == metrics[mid]["canonical_unit_id"]
                        and _pin(rule.get("evidence_sha256"))
                        and type(rule.get("numerator")) is int and rule["numerator"] > 0
                        and type(rule.get("denominator")) is int and rule["denominator"] > 0
                        and original.get("value") is not None
                        and original.get("basis") is not None
                        and comparable.get("basis") == original.get("basis")
                        and Fraction(str(comparable["value_lexeme"])) == Fraction(str(original["value"])) * Fraction(rule["numerator"], rule["denominator"]))
                except (ValueError, KeyError, ZeroDivisionError, TypeError):
                    conversion_ok = False
            if not conversion_ok:
                good = False; hold("observation", oid, "comparable conversion not qualified; original retained")
        if obs.get("kind") != "observed":
            good = False; hold("observation", oid, "AI derivation admission not implemented; separately retained")
        context = {key: obs.get("context", {}).get(key) for key in CONTEXT_FIELDS}
        context.update(obs.get("context", {}))
        add("gold_observations", observation_id=oid, claim_id=claim_for[aid], metric_id=mid, entity_id=entity_for.get(claims[aid]["subjectId"]), kind=obs["kind"], state="verified" if good else "held", context_json=_json(context), original_json=_json(claims[aid]["value"]), comparable_json=_json(obs.get("comparable")), payload_json=_json(obs))
    for comparison in qualifications.get("comparisons", []):
        ids = comparison["observation_ids"]
        if len(set(ids)) < 2 or any(oid not in observations for oid in ids):
            raise ValueError("comparison references")
        contexts = [_json(observations[oid].get("context", {})) for oid in ids]
        if any(any(observations[oid].get("context", {}).get(k) is None for k in CONTEXT_FIELDS) for oid in ids):
            raise ValueError("unknown comparison context")
        same_metric = len({observations[oid]["metric_id"] for oid in ids}) == 1
        if comparison.get("disposition") != "contradiction" or not _pin(comparison.get("evidence_sha256")) or len(set(contexts)) != 1 or not same_metric:
            raise ValueError("reviewed contradiction requires same context/metric and evidence")
        cid = digest(comparison)
        add("gold_comparisons", comparison_id=cid, disposition="contradiction", reason=comparison["reason"], evidence_sha256=comparison["evidence_sha256"])
        for oid in ids:
            add("gold_comparison_observations", comparison_id=cid, observation_id=oid)
    # Admission network: a supported recipe/mention/canonical/product/observation
    # chain seeds reachability. Citation-only paths never seed admission.
    # This graph retains source-qualified alternatives, not selected application
    # paths. Consumers must evaluate conditional edges, never union them.
    usable_edges = [e for e in rows["gold_edges"] if e["state"] in ("verified", "conditional")]
    by_predicate = {}
    adjacency = {}
    for e in usable_edges:
        by_predicate.setdefault(e["predicate_id"], []).append(e)
        adjacency.setdefault(e["subject_id"], set()).add(e["object_id"])
        adjacency.setdefault(e["object_id"], set()).add(e["subject_id"])
    products_with_nutrition = {o["entity_id"] for o in rows["gold_observations"] if o["state"] == "verified"}
    represented = {e["object_id"] for e in by_predicate.get("represents", []) if e["subject_id"] in products_with_nutrition}
    represented |= {e["object_id"] for e in by_predicate.get("contains", []) if e["subject_id"] in products_with_nutrition}
    mapped_mentions = {e["subject_id"] for e in by_predicate.get("canonical_ingredient", []) if e["object_id"] in represented}
    seeds = {e["subject_id"] for e in by_predicate.get("mentions", []) if e["object_id"] in mapped_mentions}
    unconditional_mentions = {e["subject_id"] for e in by_predicate.get("canonical_ingredient", [])
                              if e["state"] == "verified" and e["object_id"] in represented}
    unconditional_seeds = {e["subject_id"] for e in by_predicate.get("mentions", [])
                           if e["object_id"] in unconditional_mentions}
    if recipe_source_only:
        verified = {e["entity_id"] for e in rows["gold_entities"] if e["state"] == "verified"}
        declared = {}
        for edge in rows["gold_edges"]:
            declared.setdefault(edge["subject_id"], []).append(edge)
        # Every declared branch of a source recipe must qualify. An unsupported
        # ingredient cannot disappear behind a sound sibling or a citation.
        seeds = {subject for subject, edges in declared.items()
                 if subject in verified and edges and all(e["state"] == "verified" and e["object_id"] in verified for e in edges)}
        mapped_mentions = {e["object_id"] for e in usable_edges if e["subject_id"] in seeds}
    if product_source_only:
        verified = {e["entity_id"] for e in rows["gold_entities"] if e["state"] == "verified"}
        seeds = set()
        for binding in qualifications.get("product_identifier_bindings", []):
            aid = binding.get("assertion_id"); rid = binding.get("resource_id")
            assertion = claims.get(aid, {}); value = assertion.get("value", {})
            eid = entity_for.get(rid)
            if (eid in verified and endpoints.get(eid) == ("barcodes", "barcode-product")
                and assertion.get("subjectId") == rid and claim_good.get(aid)
                and value.get("kind") == "identifier" and type(value.get("value")) is str
                and value["value"].strip() and _pin(binding.get("evidence_sha256"))):
                seeds.add(eid)
    # Component membership cannot supply a mention's own required association.
    mentions_with_canonical = {e["subject_id"] for e in by_predicate.get("canonical_ingredient", [])}
    missing_associations = {}
    for entity in rows["gold_entities"]:
        if (entity["domain"], entity["entity_type"]) == ("ingredients", "ingredient-mention") and entity["entity_id"] not in mapped_mentions:
            reason = ("missing own qualified source recipe association" if recipe_source_only else
                "missing own qualified canonical ingredient association"
                if entity["entity_id"] not in mentions_with_canonical
                else "own canonical ingredient lacks qualified product/nutrition association")
            missing_associations[entity["entity_id"]] = reason
            hold("resource", entity["resource_id"], reason)
    # Rebuild the usable graph without deficient branches; valid sibling chains
    # remain available, while no edge can revive an unmapped mention.
    adjacency = {}
    for edge in usable_edges:
        if edge["subject_id"] in missing_associations or edge["object_id"] in missing_associations:
            edge["state"] = "held"
            hold("relation", edge["relation_id"], "endpoint missing own required application association")
            continue
        adjacency.setdefault(edge["subject_id"], set()).add(edge["object_id"])
        adjacency.setdefault(edge["object_id"], set()).add(edge["subject_id"])
    if product_source_only:
        # Only a product's own selected identifier seeds it. A shared class must
        # never revive another product with missing identity/rights evidence.
        reachable = set(seeds) | {e["object_id"] for e in usable_edges if e["subject_id"] in seeds}
    elif recipe_source_only:
        # Each source recipe must qualify its own declared branches. Traversing
        # back through a shared mention must never revive an incomplete recipe.
        reachable = set(seeds) | mapped_mentions
    else:
        reachable = set(seeds); frontier = list(seeds)
        while frontier:
            current = frontier.pop()
            for neighbor in adjacency.get(current, ()):
                if neighbor not in reachable:
                    reachable.add(neighbor); frontier.append(neighbor)
    islands = 0
    for e in rows["gold_entities"]:
        if e["entity_id"] not in reachable:
            islands += 1; e["state"] = "held"
            hold("resource", e["resource_id"], "missing supported recipe/canonical/product/nutrition application path")
    for table in ("gold_texts", "gold_claims", "gold_observations"):
        for row in rows[table]:
            if row["entity_id"] not in reachable:
                row["state"] = "held"
    for e in rows["gold_edges"]:
        if e["subject_id"] not in reachable or e["object_id"] not in reachable:
            e["state"] = "held"
    # Occurrence rights evidence stays retained; proposal state also reflects
    # whether its own candidate resources have a usable application association.
    verified_entities = {e["entity_id"] for e in rows["gold_entities"] if e["state"] == "verified"}
    usable_occurrences = {link["occurrence_id"] for link in rows["gold_entity_occurrences"] if link["entity_id"] in verified_entities}
    for occurrence in rows["gold_occurrences"]:
        if occurrence["occurrence_id"] not in usable_occurrences:
            occurrence["state"] = "held"
            hold("occurrence", occurrence["occurrence_id"], "no own qualified application resource")
    for metric in rows["gold_metrics"]:
        if not any(o["metric_id"] == metric["metric_id"] and o["state"] == "verified" for o in rows["gold_observations"]):
            metric["state"] = "held"
            hold("metric", metric["metric_id"], "no qualified reachable observation")
    # Citation rows are custody, not evidence of their own usable application
    # path. Keep unused/held-only citations with explicit disposition/accounting.
    usable_targets = {
        "resource": {e["resource_id"] for e in rows["gold_entities"] if e["state"] == "verified"},
        "text": {t["source_text_id"] for t in rows["gold_texts"] if t["state"] == "verified"},
        "assertion": {c["assertion_id"] for c in rows["gold_claims"] if c["state"] == "verified"},
        "relation": {e["relation_id"] for e in rows["gold_edges"] if e["state"] in ("verified", "conditional")},
        "metric": {m["metric_id"] for m in rows["gold_metrics"] if m["state"] == "verified"},
    }
    usable_citations = {support["citation_id"] for support in rows["gold_support"]
        if support["target_id"] in usable_targets.get(support["target_kind"], set())}
    for citation_id in citations.keys() - usable_citations:
        hold("citation", citation_id, "no qualified application support path; retained provenance only")
    for table in rows:
        rows[table].sort(key=_json)
    result = dict(schema_version="offmenu.gold-proposal/1", status="proposal-not-admitted", slice_id=run_id, data_class=packet["data_class"], rows=rows, metrics={"domains": {d: sum(e["domain"] == d and e["state"] == "verified" for e in rows["gold_entities"]) for d in DOMAINS}, "holds": len(rows["gold_holds"]), "citations": {"total": len(citations), "usable": len(usable_citations), "held": len(citations) - len(usable_citations)}, "connectivity": {"core_chain_seeds": len(seeds), "reachable_entities": len(reachable), "held_islands": islands, "missing_required_associations": len(missing_associations), "unresolved_edges": sum(e["subject_id"] is None or e["object_id"] is None for e in rows["gold_edges"])}, "actual_gold_admitted": 0, "recall_coverage": "NOT_CHECKED"}, pins={"packet_sha256": digest(packet), "qualification_sha256": digest(qualifications)})
    if recipe_source_only:
        result["admission_profile"] = "recipe-source-subset/1"
        result["metrics"]["connectivity"]["source_recipe_seeds"] = len(seeds)
        result["metrics"]["connectivity"]["core_chain_seeds"] = 0
    if product_source_only:
        result["admission_profile"] = "product-source-subset/1"
        result["metrics"]["connectivity"]["source_product_seeds"] = len(seeds)
        result["metrics"]["connectivity"]["core_chain_seeds"] = 0
    conditional = [e for e in rows["gold_edges"] if e["state"] == "conditional"]
    if conditional:
        result["metrics"]["connectivity"].update(
            core_chain_seeds=len(unconditional_seeds), source_qualified_potential_seeds=len(seeds),
            conditional_edges=len(conditional), selection_required=True)
    if len(_json(result).encode()) > 8388608:
        raise ValueError("proposal exceeds 8 MiB")
    return copy.deepcopy(result)

def select_observations(proposal, *, metric_id, entity_id=None, requested_context=None):
    """Expose all alternatives, matching context first, without averaging."""
    context = requested_context or {}
    alternatives = []
    conflicts = {r["observation_id"] for r in proposal["rows"]["gold_comparison_observations"]}
    for row in proposal["rows"]["gold_observations"]:
        if row["metric_id"] != metric_id or (entity_id is not None and row["entity_id"] != entity_id):
            continue
        actual = json.loads(row["context_json"])
        reasons = ["context differs or unknown: " + k for k, v in context.items() if actual.get(k) is None or actual.get(k) != v]
        if row["state"] != "verified": reasons.append("qualification held")
        if row["observation_id"] in conflicts: reasons.append("reviewed contradiction")
        alternatives.append(dict(observation=copy.deepcopy(row), preferred=not reasons, reasons=reasons))
    return {"alternatives": alternatives, "preferred_ids": [r["observation"]["observation_id"] for r in alternatives if r["preferred"]], "aggregation": "none", "comparison": "reviewed contradiction" if any(r["observation"]["observation_id"] in conflicts for r in alternatives) else "contextual variation or unknown comparability"}
