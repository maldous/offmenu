"""Pure GOLD connection for existing reviewed recipe template instances.

NativeRecipeHelpers is trusted execution configuration supplied by Worker00,
never executable material read from a recipe. Its immutable source pin and
module digests name the reconciled native dependency. This module does not
discover/import runtime paths, load code, invoke a model, open a DB, or write.
Receipt validation establishes bindings, not the truth/authenticity of a review.
The existing actual reviewer and independent acceptance own those decisions.
"""
from __future__ import annotations

from collections import Counter
import copy
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from typing import Callable
from source_literal_recipe_quantities import (SourceLiteralQuantityError,
    validate_source_literal, literal_allocation)

SCHEMA_VERSION = "offmenu-gold-recipe-actions/1"
CONNECTION_VERSION = "offmenu-gold-recipe-connections/1"
NATIVE_PIN = "368ef2ce0e42bba3497c5e548f47422a989ea10a"
NATIVE_MODULES = {
    "normalize_recipes.py": "ced8ed09b297330d68504cac14a8326d4a4500f4626097ce8b8520820175c053",
    "normalization_core.py": "72aceeae74b6a3a1fcafb0d2781b97e1b4e31697b7d92914c7946f3e0dca7793",
    "normalization_domains.py": "f6487c8ad3d2e462c33849d156233a40bc914fa3ed3e44c8dae9f09f41696661",
}
MAX_BYTES = 524288
MAX_ROWS = 128
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_FIELD = re.compile(r"\{([a-z][a-z0-9_]*)\}")


@dataclass(frozen=True)
class NativeRecipeHelpers:
    source_pin: str
    module_sha256: dict
    canonical_template_id: Callable
    validate_reviewed_template: Callable
    validate_and_cache_actual_review: Callable
    recipe_translation_units: Callable
    validate_and_cache_translation: Callable
    normalize_quantity: Callable
    digest: Callable


class ActionConnectionError(ValueError):
    pass


def _bounded(value):
    nodes = 0
    def walk(x, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 20000:
            raise ActionConnectionError("input_limit")
        if isinstance(x, dict):
            if len(x) > 512 or any(not isinstance(k, str) for k in x):
                raise ActionConnectionError("invalid_object")
            for k, v in x.items():
                walk(k, depth + 1); walk(v, depth + 1)
        elif isinstance(x, list):
            if len(x) > 512:
                raise ActionConnectionError("input_limit")
            for v in x: walk(v, depth + 1)
        elif x is not None and type(x) not in (str, int, float, bool):
            raise ActionConnectionError("non_json_input")
    walk(value)
    try:
        blob = json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ActionConnectionError("invalid_json") from exc
    if len(blob) > MAX_BYTES:
        raise ActionConnectionError("input_limit")
    return blob


def _digest(value):
    return hashlib.sha256(_bounded(value)).hexdigest()


def _text(x):
    return isinstance(x, str) and bool(x.strip()) and x.strip().casefold() not in {"unknown", "unconfigured", "unavailable", "unexposed"}


def _pin(x):
    return isinstance(x, dict) and _text(x.get("id")) and isinstance(x.get("sha256"), str) and _HASH.fullmatch(x["sha256"]) is not None


def _number(value):
    if not isinstance(value, str) or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+|\d+/[1-9]\d*)", value):
        raise ActionConnectionError("exact_number_required")
    return Fraction(value)


def _display_number(value):
    """Use exact finite decimals for readable English, otherwise a rational."""
    value = Fraction(value)
    remaining, twos, fives = value.denominator, 0, 0
    while remaining % 2 == 0:
        remaining //= 2
        twos += 1
    while remaining % 5 == 0:
        remaining //= 5
        fives += 1
    if remaining != 1:
        return str(value)
    places = max(twos, fives)
    scaled = abs(value.numerator) * (10 ** places) // value.denominator
    digits = str(scaled).rjust(places + 1, "0")
    text = (digits[:-places] + "." + digits[-places:]).rstrip("0").rstrip(".") if places else digits
    return ("-" if value < 0 else "") + text


def _interval(quantity, *, allow_negative=False):
    if not isinstance(quantity, dict) or quantity.get("status") != "normalized" or quantity.get("exact") is not True:
        raise ActionConnectionError("unsupported_quantity")
    low = _number(quantity.get("min", quantity.get("value")))
    high = _number(quantity.get("max", quantity.get("value")))
    if (low < 0 and not allow_negative) or high < low:
        raise ActionConnectionError("invalid_quantity_range")
    return low, high


def _pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ActionConnectionError("source_pointer_required")
    try:
        for part in pointer[1:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) and key.isdigit() else value[key]
        return value
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ActionConnectionError("source_pointer_missing") from exc


def _evidence(spans, source, *, pointer=None):
    if not isinstance(spans, list) or not spans:
        raise ActionConnectionError("source_evidence_required")
    for span in spans:
        if not isinstance(span, dict) or set(span) != {"pointer", "start", "end", "text", "offset_unit"} or span["offset_unit"] != "unicode_codepoint":
            raise ActionConnectionError("source_evidence_shape")
        raw = _pointer(source, span["pointer"])
        start, end = span["start"], span["end"]
        if not isinstance(raw, str) or type(start) is not int or type(end) is not int or not (0 <= start < end <= len(raw)) or raw[start:end] != span["text"]:
            raise ActionConnectionError("source_evidence_mismatch")
        if pointer is not None and span["pointer"] != pointer:
            raise ActionConnectionError("source_evidence_wrong_step")


def _placeholders(pattern):
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 4000:
        raise ActionConnectionError("render_pattern_required")
    names = _FIELD.findall(pattern)
    remainder = _FIELD.sub("", pattern)
    if "{" in remainder or "}" in remainder:
        raise ActionConnectionError("render_placeholder_syntax")
    return names


def _check_native(native):
    if not isinstance(native, NativeRecipeHelpers) or native.source_pin != NATIVE_PIN or native.module_sha256 != NATIVE_MODULES:
        raise ActionConnectionError("immutable_native_dependency_mismatch")
    for name in ("canonical_template_id", "validate_reviewed_template", "validate_and_cache_actual_review", "recipe_translation_units", "validate_and_cache_translation", "normalize_quantity", "digest"):
        if not callable(getattr(native, name)):
            raise ActionConnectionError("native_helper_unavailable")


def connect_recipe_actions(rules_artifact, semantic_review, *, native,
                           translation_receipts=(), connections,
                           target_language="en", requested_servings=None):
    """Return bounded connection rows; Worker00 alone executes fixed DDL/rows.

    Native definitions and instances are preserved verbatim. Connections add
    only missing GOLD identity/allocation/material/citation references. Partial
    rows remain held; no source fact, dependency, ingredient identity or English
    instruction is invented on a missing receipt. Output is never gold admission.
    """
    out = {"schema_version": SCHEMA_VERSION, "status": "held", "target_language": "en",
           "gold_admission": "not-assigned", "holds": [], "native_templates": [],
           "native_instances": [], "actions": [], "dependencies": [],
           "ingredient_links": [], "materials": [], "material_inputs": [], "supports": []}
    def hold(code, target="recipe"):
        item = {"code": code, "target": target}
        if item not in out["holds"]: out["holds"].append(item)
    try:
        if target_language != "en": raise ActionConnectionError("English_output_only")
        _check_native(native)
        translation_receipts = list(translation_receipts)
        _bounded([rules_artifact, semantic_review, connections, translation_receipts, requested_servings])
        if not isinstance(connections, dict) or connections.get("schema_version") != CONNECTION_VERSION or connections.get("data_class") not in {"synthetic", "real-qualified"}:
            raise ActionConnectionError("connection_schema")
        for field in ("recipe_occurrence_id", "recipe_entity_id"):
            if not _text(connections.get(field)): raise ActionConnectionError("recipe_gold_reference_required")
        body = {k: v for k, v in connections.items() if k != "qualification"}
        qualification = connections.get("qualification", {})
        if qualification.get("state") != "passed" or qualification.get("content_sha256") != native.digest(body) or not _pin(qualification.get("evidence_pin")):
            raise ActionConnectionError("connection_qualification_binding")
        for field in ("entities", "citations", "ingredient_links", "materials", "material_inputs", "action_citations"):
            if not isinstance(connections.get(field), list) or len(connections[field]) > MAX_ROWS:
                raise ActionConnectionError("connection_list_limit")
            if any(not isinstance(row, dict) for row in connections[field]):
                raise ActionConnectionError("connection_row_shape")
        reviewed = native.validate_and_cache_actual_review(copy.deepcopy(rules_artifact), copy.deepcopy(semantic_review), store=None, cache_result=False)
        native.validate_reviewed_template(rules_artifact["normalized"], reviewed["normalized"], review=semantic_review)
        if reviewed.get("review", {}).get("status") != "reviewed": raise ActionConnectionError("semantic_review_not_accepted")
        template = reviewed["normalized"]["fields"]["recipe_menu_template"]
        if template.get("source_kind") != "recipe": raise ActionConnectionError("recipe_not_menu_required")
        instances = template["template_instances"]
        if not instances or len(instances) > MAX_ROWS: raise ActionConnectionError("action_count_limit")
        definitions = {t["template_id"]: t["definition"] for t in template["learned_templates"]}
        if len(definitions) != len(template["learned_templates"]) or any(native.canonical_template_id(d) != key for key, d in definitions.items()):
            raise ActionConnectionError("native_template_identity")
        source = rules_artifact["source_original"]
        steps = {s["step_id"]: s for s in template["steps"]}
        instance_map = {i["instance_id"]: i for i in instances}
        if len(instance_map) != len(instances): raise ActionConnectionError("duplicate_action_id")
        order = {i["instance_id"]: index for index, i in enumerate(instances)}
        ingredients = {i["ingredient_id"]: i for i in template["ingredients"]}
        if any(not _text(row.get("id")) for field in ("entities", "citations") for row in connections[field]):
            raise ActionConnectionError("gold_reference_id_required")
        entities = {r.get("id"): r for r in connections["entities"]}
        citations = {r.get("id"): r for r in connections["citations"]}
        if len(entities) != len(connections["entities"]) or len(citations) != len(connections["citations"]) or None in entities or None in citations:
            raise ActionConnectionError("duplicate_or_missing_gold_reference")
        literal_profile = "source_literal_quantities" in connections
        literals = {}
        if literal_profile:
            rows = connections["source_literal_quantities"]
            if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
                raise ActionConnectionError("source_literal_contract_list_required")
            if requested_servings is not None:
                raise ActionConnectionError("source_literal_scaling_not_qualified")
            for row in rows:
                line = row.get("source_ingredient_line_id") if isinstance(row, dict) else None
                if not isinstance(line, str) or line not in ingredients or line in literals:
                    raise ActionConnectionError("source_literal_duplicate_or_unknown_line")
                ingredient = ingredients[line]
                pointers = {ingredient["evidence_pointer"] + "/raw_text",
                            ingredient["evidence_pointer"] + "/source_name_text"}
                pointers.update(steps[i["step_id"]]["source_span"]["pointer"] for i in instances
                    if any(s.get("type") == "ingredient_reference" and s.get("value") == line
                           for s in i["slots"].values()))
                try:
                    literals[line] = validate_source_literal(row, ingredient,
                        allowed_pointers=pointers, source=source, citations=citations,
                        validate_evidence=_evidence)
                except SourceLiteralQuantityError as exc:
                    raise ActionConnectionError(str(exc)) from exc
        if any(isinstance(i.get("quantity"), dict) and i["quantity"].get("status") != "normalized"
               and line not in literals for line, i in ingredients.items()):
            raise ActionConnectionError("recipe_ingredient_quantity_unresolved")
        recipe_entity = entities.get(connections["recipe_entity_id"], {})
        if recipe_entity.get("domain") != "recipes" or recipe_entity.get("state") != "verified":
            raise ActionConnectionError("recipe_entity_not_qualified")
        units = native.recipe_translation_units(reviewed, "en")
        unit_map = {u["unit_id"]: u for u in units}
        receipt_map = {r.get("unit_id"): r for r in translation_receipts}
        if len(receipt_map) != len(translation_receipts) or not set(receipt_map) <= set(unit_map):
            raise ActionConnectionError("translation_scope_mismatch")
        used_units = set()
        def english(unit):
            used_units.add(unit["unit_id"])
            locale = unit.get("source_language")
            if isinstance(locale, str) and locale.lower().split("-")[0] == "en":
                return unit["source_text"]
            receipt = receipt_map.get(unit["unit_id"])
            if receipt is None: raise ActionConnectionError("reviewed_English_unit_required")
            result = native.validate_and_cache_translation(copy.deepcopy(unit), copy.deepcopy(receipt), store=None)
            if result.get("status") != "complete": raise ActionConnectionError("English_unit_review_not_accepted")
            return receipt["translated_text"]
        def supported(ids, spans, action_id, kind="action", target=None, **keys):
            if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
                raise ActionConnectionError("citation_support_required")
            step = steps[instance_map[action_id]["step_id"]]
            _evidence(spans, source, pointer=step["source_span"]["pointer"])
            if any(citations.get(cid, {}).get("state") != "verified" for cid in ids):
                raise ActionConnectionError("citation_not_qualified")
            if len(out["supports"]) + len(ids) > 1024:
                raise ActionConnectionError("citation_support_limit")
            for cid in ids:
                out["supports"].append({"target_kind": kind, "target_id": target or action_id,
                                        "action_id": action_id, **keys,
                                        "citation_id": cid, "evidence": copy.deepcopy(spans)})
        factor = Fraction(1)
        servings = connections.get("source_servings")
        if requested_servings is not None:
            if not isinstance(servings, dict) or servings.get("unit") != "servings": raise ActionConnectionError("source_servings_unknown")
            _evidence(servings.get("evidence"), source)
            original_servings, desired = _number(servings.get("value")), _number(requested_servings)
            if original_servings <= 0 or desired <= 0: raise ActionConnectionError("servings_must_be_positive")
            factor = desired / original_servings
        out.update(data_class=connections["data_class"], native_source_pin=native.source_pin,
                   native_module_sha256=copy.deepcopy(native.module_sha256),
                   source_occurrence_id=connections["recipe_occurrence_id"], recipe_entity_id=connections["recipe_entity_id"],
                   rules_artifact_sha256=native.digest(rules_artifact), semantic_review_sha256=native.digest(semantic_review),
                   translation_receipts_sha256=native.digest(translation_receipts),
                   connection_sha256=native.digest(connections), scale_factor=str(factor),
                   native_templates=copy.deepcopy(template["learned_templates"]), native_instances=copy.deepcopy(instances))
        out["run_id"] = "recipe-actions:" + _digest({k: out[k] for k in ("source_occurrence_id", "rules_artifact_sha256", "semantic_review_sha256", "translation_receipts_sha256", "connection_sha256", "scale_factor")})
        numeric_display, allocated, seen_links, bound_refs = {}, {}, set(), set()
        allocation_counts = {}
        first_use = {}
        if literal_profile:
            for item in instances:
                for slot in item["slots"].values():
                    if slot["type"] == "ingredient_reference":
                        first_use.setdefault(slot["value"], item["instance_id"])
        for link in connections["ingredient_links"]:
            target = str(link.get("instance_id")) + ":" + str(link.get("slot_name"))
            try:
                iid, name, line = link["instance_id"], link["slot_name"], link["source_ingredient_line_id"]
                if iid not in instance_map or (iid, name) in seen_links: raise ActionConnectionError("duplicate_or_unknown_ingredient_binding")
                seen_links.add((iid, name))
                bound = instance_map[iid]["slots"].get(name, {})
                if bound.get("type") != "ingredient_reference" or bound.get("value") != line or line not in ingredients:
                    raise ActionConnectionError("source_ingredient_binding_mismatch")
                entity = entities.get(link.get("ingredient_entity_id"), {})
                if entity.get("domain") != "ingredients" or entity.get("state") != "verified": raise ActionConnectionError("canonical_ingredient_not_qualified")
                supported(link.get("citation_ids"), link.get("evidence"), iid, "ingredient", target, slot_name=name)
                allocation, quantity = None, link.get("quantity")
                if literal_profile and quantity is not None and first_use.get(line) != iid:
                    raise ActionConnectionError("source_quantity_first_use_binding_required")
                if quantity is not None and line in literals:
                    qname, uname = link.get("quantity_slot_name"), link.get("unit_slot_name")
                    slots = instance_map[iid]["slots"]
                    if (iid, qname) in numeric_display or allocation_counts.get(line):
                        raise ActionConnectionError("source_literal_allocate_once_required")
                    if uname is None and any(s["type"] == "unit" for s in slots.values()):
                        raise ActionConnectionError("allocation_unit_binding_required")
                    if uname is not None and (uname not in slots or slots[uname].get("type") != "unit"):
                        raise ActionConnectionError("source_literal_unit_slot_mismatch")
                    lexical = bound.get("lexical_unit")
                    noun = lexical["text"] if lexical else ingredients[line]["source_name"]
                    try:
                        allocation, display = literal_allocation(literals[line], quantity,
                            slots.get(qname, {}), unit_slot=slots.get(uname) if uname is not None else None,
                            ingredient_name=noun)
                    except SourceLiteralQuantityError as exc:
                        raise ActionConnectionError(str(exc)) from exc
                    numeric_display[(iid, qname)] = display
                    if uname is not None:
                        numeric_display[(iid, uname)] = literals[line]["unit"]
                    allocation_counts[line] = 1
                elif quantity is not None:
                    if not isinstance(quantity, dict) or set(quantity) != {"value", "unit"}: raise ActionConnectionError("allocation_quantity_shape")
                    normal = native.normalize_quantity(quantity["value"], quantity["unit"])
                    low, high = _interval(normal)
                    total = ingredients[line].get("quantity")
                    total_low, _ = _interval(total)
                    if normal["unit"] != total["unit"] or normal.get("dimension") != total.get("dimension"):
                        raise ActionConnectionError("allocation_unit_basis_mismatch")
                    qname = link.get("quantity_slot_name")
                    qslot = instance_map[iid]["slots"].get(qname, {})
                    if qslot.get("type") != "quantity" or (iid, qname) in numeric_display: raise ActionConnectionError("allocation_quantity_slot_required")
                    raw = qslot.get("value")
                    basis = raw.get("original", raw) if isinstance(raw, dict) else raw
                    raw_value = basis.get("value", basis) if isinstance(basis, dict) else basis
                    raw_unit = basis.get("unit", quantity["unit"]) if isinstance(basis, dict) else quantity["unit"]
                    compared = native.normalize_quantity(raw_value, raw_unit)
                    if _interval(compared) != (low, high) or compared["unit"] != normal["unit"]:
                        raise ActionConnectionError("allocation_slot_quantity_mismatch")
                    uname = link.get("unit_slot_name")
                    if uname is None and any(s["type"] == "unit" for s in instance_map[iid]["slots"].values()):
                        raise ActionConnectionError("allocation_unit_binding_required")
                    if uname is not None:
                        uslot = instance_map[iid]["slots"].get(uname, {})
                        if uslot.get("type") != "unit" or uslot.get("value") != quantity["unit"]: raise ActionConnectionError("allocation_unit_slot_mismatch")
                    running = allocated.get(line, Fraction(0)) + high
                    if running > total_low: raise ActionConnectionError("ingredient_quantity_not_conserved")
                    allocated[line] = running
                    allocation_counts[line] = allocation_counts.get(line, 0) + 1
                    # Reuse the native linear unit mapping for display; do not parse
                    # a second range grammar or attach a source unit to canonical bounds.
                    basis_unit = native.normalize_quantity("1", quantity["unit"])
                    unit_low, unit_high = _interval(basis_unit)
                    if normal.get("dimension") not in {"mass", "volume", "count"} or unit_low != unit_high or unit_low <= 0:
                        raise ActionConnectionError("allocation_linear_unit_required")
                    display_low, display_high = low * factor / unit_low, high * factor / unit_low
                    display = _display_number(display_low) if display_low == display_high else _display_number(display_low) + "–" + _display_number(display_high)
                    numeric_display[(iid, qname)] = display + (" " + quantity["unit"] if uname is None else "")
                    allocation = {"original": copy.deepcopy(quantity), "normalized": normal,
                                  "scaled_min": str(low * factor), "scaled_max": str(high * factor),
                                  "normalized_unit": normal["unit"], "factor": str(factor)}
                else:
                    # Null is qualitative only when this action has no quantity
                    # slot. Never infer which ingredient an unbound amount uses.
                    if any(s["type"] == "quantity" for s in instance_map[iid]["slots"].values()):
                        raise ActionConnectionError("quantified_ingredient_allocation_required")
                    if factor != 1:
                        raise ActionConnectionError("allocation_quantity_unknown_for_scaling")
                bound_refs.add((iid, name))
                out["ingredient_links"].append({"action_id": iid, "slot_name": name,
                    "source_ingredient_line_id": line, "ingredient_entity_id": link["ingredient_entity_id"],
                    "allocation": allocation, "evidence": copy.deepcopy(link["evidence"])})
            except (ActionConnectionError, KeyError, TypeError, ValueError) as exc:
                hold(str(exc) if isinstance(exc, ActionConnectionError) else "ingredient_binding_shape", target)
        if literal_profile:
            # This opt-in profile is source-amount transcription, not partial
            # allocation. In particular a literal egg fix cannot hide an
            # unallocated known flour amount behind qualitative NULL links.
            for line, ingredient in ingredients.items():
                total = ingredient.get("quantity")
                if total is None:
                    continue
                complete = allocation_counts.get(line) == 1
                if line not in literals:
                    low, high = _interval(total)
                    complete = complete and low == high and allocated.get(line) == low
                if not complete:
                    hold("source_quantity_allocate_once_required", line)
        action_support = {}
        for item in connections["action_citations"]:
            iid = item.get("instance_id")
            try:
                if iid not in instance_map or iid in action_support: raise ActionConnectionError("action_citation_binding")
                supported(item.get("citation_ids"), item.get("evidence"), iid)
                action_support[iid] = True
            except ActionConnectionError as exc: hold(str(exc), str(iid))
        def numeric(slot):
            value = slot["value"]
            if slot["type"] == "unit":
                if not isinstance(value, str) or native.normalize_quantity("1", value).get("status") != "normalized": raise ActionConnectionError("unsupported_unit_slot")
                return value
            if isinstance(value, dict):
                original = value.get("original", value)
                normal = native.normalize_quantity(original.get("value"), original.get("unit"))
                low, high = _interval(normal, allow_negative=slot["type"] == "temperature")
                return (_display_number(low) if low == high else _display_number(low) + "–" + _display_number(high)) + " " + normal["unit"]
            return _display_number(_number(value))
        for instance in instances:
            iid = instance["instance_id"]
            try:
                if iid not in action_support: raise ActionConnectionError("action_citation_required")
                definition = definitions[instance["template_id"]]
                grammar = next(u for u in units if u.get("unit_kind") == "canonical_template" and u.get("semantic_identity") == instance["template_id"])
                pattern = english(grammar)
                if Counter(_placeholders(pattern)) != Counter(_placeholders(definition["pattern"])):
                    raise ActionConnectionError("render_placeholder_mismatch")
                values = {}
                for name, slot in instance["slots"].items():
                    kind = slot["type"]
                    literal_line = slot.get("value") if kind == "ingredient_reference" else None
                    if literal_line in literals and not allocation_counts.get(literal_line):
                        raise ActionConnectionError("source_literal_allocation_required")
                    if kind == "ingredient_reference" and (iid, name) not in bound_refs: raise ActionConnectionError("ingredient_gold_link_required")
                    if (iid, name) in numeric_display: values[name] = numeric_display[(iid, name)]
                    elif kind in {"quantity", "unit", "duration", "temperature"}:
                        if kind == "quantity":
                            if factor != 1:
                                raise ActionConnectionError("unallocated_quantity_for_scaling")
                            if any(s["type"] in {"ingredient_reference", "unit"} for s in instance["slots"].values()):
                                raise ActionConnectionError("unallocated_quantity_binding")
                        values[name] = numeric(slot)
                    elif kind == "material_reference": raise ActionConnectionError("native_material_reference_not_admitted")
                    else:
                        context = {"template_id": instance["template_id"], "slot_name": name,
                                   "slot_type": kind, "grammar_context": definition["grammar_context"],
                                   "role": "template_argument", "recipe_template_version": template["schema_version"]}
                        lexical = slot.get("lexical_unit")
                        if lexical is not None:
                            identity = native.digest({"text": lexical["text"], "context": context,
                                                      "lexical_context": lexical["context"]})
                        else:
                            ingredient = ingredients[slot["value"]]
                            text = ingredient["source_name"] or ingredient["source_text"]
                            identity = native.digest({"text": text, "context": context})
                        unit = next(u for u in units if u.get("unit_kind") == "lexical_unit" and
                                    u.get("semantic_identity") == identity)
                        values[name] = english(unit)
                rendered = _FIELD.sub(lambda m: values[m[1]], pattern)
                if "{" in rendered or "}" in rendered: raise ActionConnectionError("unresolved_render_parameters")
                step = steps[instance["step_id"]]
                out["actions"].append({"action_id": iid, "template_id": instance["template_id"],
                    "step_id": instance["step_id"], "source_order": instance["source_order"], "sequence_index": order[iid],
                    "original_text": step["source_span"]["text"], "source_language": reviewed["normalized"]["language"],
                    "english_text": rendered, "action_concept": definition["action"], "phase": definition["phase"],
                    "unknown_parameters": copy.deepcopy(instance["unknown_parameters"]), "evidence": copy.deepcopy(instance["evidence"])})
                for dependency in instance["depends_on"]:
                    if dependency not in order or order[dependency] >= order[iid]: raise ActionConnectionError("action_dependency_not_earlier")
                    row = {"action_id": iid, "depends_on": dependency}
                    if row not in out["dependencies"]: out["dependencies"].append(row)
            except (ActionConnectionError, StopIteration, KeyError, TypeError, ValueError) as exc:
                hold(str(exc) if isinstance(exc, ActionConnectionError) else "render_binding_missing", iid)
        material_map = {}
        for material in connections["materials"]:
            mid = material.get("material_id")
            try:
                if set(material) != {"material_id", "producer_instance_id", "label", "citation_ids", "evidence"}:
                    raise ActionConnectionError("material_shape")
                producer = material["producer_instance_id"]
                if not _text(mid) or mid in material_map or producer not in instance_map or not _text(material.get("label")):
                    raise ActionConnectionError("material_producer_binding")
                if not any(material["label"] in span.get("text", "") for span in material.get("evidence", [])):
                    raise ActionConnectionError("material_label_not_source_grounded")
                supported(material.get("citation_ids"), material.get("evidence"), producer, "material", mid, material_id=mid)
                material_map[mid] = material
                out["materials"].append(copy.deepcopy(material))
            except (ActionConnectionError, KeyError) as exc: hold(str(exc) if isinstance(exc, ActionConnectionError) else "material_shape", str(mid))
        seen_inputs = set()
        for item in connections["material_inputs"]:
            try:
                if set(item) != {"instance_id", "material_id", "citation_ids", "evidence"}:
                    raise ActionConnectionError("material_input_shape")
                mid, consumer = item["material_id"], item["instance_id"]
                if (consumer, mid) in seen_inputs: raise ActionConnectionError("duplicate_material_input")
                seen_inputs.add((consumer, mid))
                material = material_map.get(mid)
                if material is None or consumer not in instance_map or order[material["producer_instance_id"]] >= order[consumer]:
                    raise ActionConnectionError("material_input_not_earlier")
                frontier = list(instance_map[consumer]["depends_on"]); ancestors = set()
                while frontier:
                    parent = frontier.pop()
                    if parent not in ancestors:
                        ancestors.add(parent); frontier.extend(instance_map[parent]["depends_on"])
                if material["producer_instance_id"] not in ancestors: raise ActionConnectionError("material_dependency_missing")
                supported(item.get("citation_ids"), item.get("evidence"), consumer, "material_input", consumer + ":" + mid, material_id=mid)
                out["material_inputs"].append(copy.deepcopy(item))
            except (ActionConnectionError, KeyError) as exc: hold(str(exc) if isinstance(exc, ActionConnectionError) else "material_input_shape")
        if len(out["actions"]) != len(instances): hold("incomplete_action_rendering")
        if not out["holds"]: out["status"] = "ready-for-review"
        out["translation_unit_ids_used"] = sorted(used_units)
        out["source_original_sha256"] = native.digest(source)
    except (ActionConnectionError, ValueError, KeyError, TypeError, AttributeError, IndexError, StopIteration, RecursionError) as exc:
        code = str(exc) if isinstance(exc, ActionConnectionError) else "native_review_or_input_rejected"
        hold(code)
    return out
