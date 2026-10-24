"""Generated-only contract tests for the recipe-action GOLD connector.

These fixtures load the exact immutable native helpers named by
gold_recipe_actions.NATIVE_PIN. They do not open a NormalizationStore, staging
database, runner layout or production cache.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PIN = "368ef2ce0e42bba3497c5e548f47422a989ea10a"
NATIVE_FILES = (
    "manual-action/ingest_api.py",
    "manual-action/normalization_api.py",
    "manual-action/runner_paths.py",
    "manual-action/normalization_domains.py",
    "manual-action/normalization_core.py",
    "manual-action/normalize_recipes.py",
)


# Test-only source snapshot: exact Git blobs from PIN, including the transitive
# import closure. Never use installed/current runtime modules as a substitute.
# All six hashes are checked before any snapshot module is imported.
NATIVE_SHA256 = {
    "manual-action/ingest_api.py": "b26a90375b9dc410dad2f6d00687ad810d60a653721d3a886cf4a4c998ffb26b",
    "manual-action/normalization_api.py": "faddea9b4447aa908ffc7ec92533dd078aac9d435aa2569dd2f0cece884229ea",
    "manual-action/runner_paths.py": "ffbe973e8885bd65c1813e5651a1530cca516dd6b87db7f4f60fdce20943fa99",
    "manual-action/normalization_domains.py": "f6487c8ad3d2e462c33849d156233a40bc914fa3ed3e44c8dae9f09f41696661",
    "manual-action/normalization_core.py": "72aceeae74b6a3a1fcafb0d2781b97e1b4e31697b7d92914c7946f3e0dca7793",
    "manual-action/normalize_recipes.py": "ced8ed09b297330d68504cac14a8326d4a4500f4626097ce8b8520820175c053"
}
NATIVE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "recipe_native_368ef"


def _blob(path):
    expected = NATIVE_SHA256[path]
    blob = (NATIVE_FIXTURE / Path(path).name).read_bytes()
    if hashlib.sha256(blob).hexdigest() != expected:
        raise ValueError("immutable native test fixture digest mismatch: " + path)
    return blob


class PinnedNativeFixture:
    """A temporary import location for pure, immutable native helper blobs."""

    def __init__(self):
        self._directory = tempfile.TemporaryDirectory(prefix="offmenu-native-fixture-")
        self.path = Path(self._directory.name)
        self.previous = {}

    def load(self):
        for source_path in NATIVE_FILES:
            destination = self.path / Path(source_path).name
            destination.write_bytes(_blob(source_path))
        self.expected_hashes = {
            name: hashlib.sha256((self.path / name).read_bytes()).hexdigest()
            for name in ("normalize_recipes.py", "normalization_core.py", "normalization_domains.py")
        }
        self.previous = {name: sys.modules.get(name) for name in (
            "ingest_api", "normalization_api", "runner_paths", "normalization_domains",
            "normalization_core", "normalize_recipes",
        )}
        for name in self.previous:
            sys.modules.pop(name, None)
        sys.path.insert(0, str(self.path))
        self.recipes = importlib.import_module("normalize_recipes")
        self.core = importlib.import_module("normalization_core")
        self.domains = importlib.import_module("normalization_domains")
        self.api = importlib.import_module("normalization_api")
        return self

    def close(self):
        sys.path.remove(str(self.path))
        for name in self.previous:
            sys.modules.pop(name, None)
            if self.previous[name] is not None:
                sys.modules[name] = self.previous[name]
        self._directory.cleanup()


def _span(pointer, text, token, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(token, start + 1)
    return {"pointer": pointer, "start": start, "end": start + len(token),
            "text": token, "offset_unit": "unicode_codepoint"}


def _record(*, single=False):
    record = {
        "id": "generated:recipe-actions", "kind": "recipe", "title": "Generated beans",
        "language": "en", "yield": "2 servings",
        "ingredients": [{
            "id": "generated:line:beans", "ordinal": 1,
            "raw_text": "100 g beans", "source_name_text": "beans",
            "quantity": "100", "unit": "g",
        }],
        "steps": [
            {"ordinal": 1, "source_section": "Method", "raw_text": "Mix 40 g beans."},
            {"ordinal": 2, "source_section": "Method", "raw_text": "Serve beans."},
        ],
    }
    if single:
        record["steps"] = record["steps"][:1]
    return record


def _rules_for(native, record):
    versions = native.api.Versions(model_version="generated-test-model/1", prompt_version="generated-test-prompt/1")
    return native.core.run_rules({
        "domain": "recipes", "source_key": "generated-only", "source_version": "fixture/1",
        "record_id": record["id"], "content_sha256": native.recipes.digest(record), "payload": record,
    }, versions)


def _rules(native, *, single=False):
    return _rules_for(native, _record(single=single))


def _review(native, rules, *, dependency=True, include_numeric=True, amount="40", unit="g"):
    reviewed = copy.deepcopy(rules["normalized"])
    template = reviewed["fields"]["recipe_menu_template"]
    template["status"] = "reviewed"
    template["unresolved"] = []
    ingredient = template["ingredients"][0]["ingredient_id"]
    mix = template["steps"][0]
    serve = template["steps"][1] if len(template["steps"]) > 1 else None
    mix_pattern = "Mix {amount} {unit} {material}." if include_numeric else "Mix {material}."
    mix_slots = {"material": "ingredient_reference"}
    if include_numeric:
        mix_slots = {"amount": "quantity", "unit": "unit", "material": "ingredient_reference"}
    definitions = [
        {"action": "mix", "phase": "preparation", "pattern": mix_pattern,
         "slot_types": mix_slots, "source_locale": "en", "grammar_context": {"mood": "imperative", "fixture": True}},
    ]
    if serve is not None:
        definitions.append(
            {"action": "serve", "phase": "presentation", "pattern": "Serve {material}.",
             "slot_types": {"material": "ingredient_reference"}, "source_locale": "en",
             "grammar_context": {"mood": "imperative", "fixture": True}}
        )
    template["learned_templates"] = [
        {"template_id": native.recipes.canonical_template_id(definition), "definition": definition}
        for definition in definitions
    ]
    mix_evidence = copy.deepcopy(mix["source_span"])
    serve_evidence = copy.deepcopy(serve["source_span"]) if serve is not None else None
    slots = {"material": {"type": "ingredient_reference", "value": ingredient,
                           "evidence": [copy.deepcopy(mix_evidence)], "lexical_unit": None}}
    if include_numeric:
        raw = mix["source_span"]["text"]
        slots = {
            "amount": {"type": "quantity", "value": {"value": amount, "unit": unit},
                       "evidence": [_span(mix["source_span"]["pointer"], raw, amount)], "lexical_unit": None},
            "unit": {"type": "unit", "value": unit,
                     "evidence": [_span(mix["source_span"]["pointer"], raw, unit)], "lexical_unit": None},
            "material": slots["material"],
        }
    mix_id = "generated:mix"
    serve_id = "generated:serve"
    template["template_instances"] = [
        {"instance_id": mix_id, "template_id": template["learned_templates"][0]["template_id"],
         "step_id": mix["step_id"], "source_order": mix["source_order"], "evidence": [mix_evidence],
         "slots": slots, "depends_on": [], "unknown_parameters": []},
    ]
    if serve is not None:
        template["template_instances"].append(
            {"instance_id": serve_id, "template_id": template["learned_templates"][1]["template_id"],
             "step_id": serve["step_id"], "source_order": serve["source_order"], "evidence": [serve_evidence],
             "slots": {"material": {"type": "ingredient_reference", "value": ingredient,
                                      "evidence": [serve_evidence], "lexical_unit": None}},
             "depends_on": [mix_id] if dependency else [], "unknown_parameters": ["serving_temperature_not_stated"]}
        )
    reviewed["fields"]["translation_plan"].update(
        status="ready_for_localized_template_translation",
        template_ids=[entry["template_id"] for entry in template["learned_templates"]],
    )
    return {
        "artifact_id": rules["artifact_id"], "artifact_sha256": native.core.artifact_digest(rules),
        "receipt_id": "generated-only:recipe-actions", "reviewer_id": "generated-test-fixture",
        "reviewer_kind": "assistant", "model_version": rules["versions"]["model_version"],
        "prompt_version": rules["versions"]["prompt_version"], "schema_version": rules["versions"]["schema_version"],
        "template_version": rules["versions"]["template_version"], "reviewed_at": "2026-10-23T00:00:00Z",
        "method": "direct_item_review", "evidence_ref": "fixture-only://not-a-real-review", "decision": "accepted",
        "normalized": reviewed,
        "coverage": [{"item_id": item, "decision": "accepted", "notes": "Generated contract fixture."}
                     for item in rules["review_item_ids"]],
        "issues": [], "uncertainty": [],
    }


def _connections(native, review, *, quantity=True, dependency=True, quantity_value="40", quantity_unit="g"):
    template = review["normalized"]["fields"]["recipe_menu_template"]
    mix = template["template_instances"][0]
    serve = template["template_instances"][1] if len(template["template_instances"]) > 1 else None
    mix_span = copy.deepcopy(mix["evidence"])
    serve_span = copy.deepcopy(serve["evidence"]) if serve is not None else None
    body = {
        "schema_version": "offmenu-gold-recipe-connections/1", "data_class": "synthetic",
        "recipe_occurrence_id": "generated:occurrence:recipe-actions", "recipe_entity_id": "recipe:generated-beans",
        "entities": [
            {"id": "recipe:generated-beans", "domain": "recipes", "state": "verified"},
            {"id": "ingredient:beans", "domain": "ingredients", "state": "verified"},
        ],
        "citations": [{"id": "citation:generated", "state": "verified"}],
        "ingredient_links": [
            {"instance_id": mix["instance_id"], "slot_name": "material",
             "source_ingredient_line_id": "generated:line:beans", "ingredient_entity_id": "ingredient:beans",
             "quantity": {"value": quantity_value, "unit": quantity_unit} if quantity else None,
             "quantity_slot_name": "amount" if quantity else None, "unit_slot_name": "unit" if quantity else None,
             "citation_ids": ["citation:generated"], "evidence": mix_span},
        ],
        "materials": [], "material_inputs": [], "action_citations": [
            {"instance_id": mix["instance_id"], "citation_ids": ["citation:generated"], "evidence": mix_span},
        ],
        "source_servings": {"value": "2", "unit": "servings",
                            "evidence": [_span("/yield", "2 servings", "2 servings")]},
    }
    if serve is not None:
        body["ingredient_links"].append(
            {"instance_id": serve["instance_id"], "slot_name": "material",
             "source_ingredient_line_id": "generated:line:beans", "ingredient_entity_id": "ingredient:beans",
             "quantity": None, "quantity_slot_name": None, "unit_slot_name": None,
             "citation_ids": ["citation:generated"], "evidence": serve_span}
        )
        body["materials"] = [{"material_id": "material:mixed-beans", "producer_instance_id": mix["instance_id"],
                              "label": "beans", "citation_ids": ["citation:generated"], "evidence": mix_span}]
        body["material_inputs"] = [{"instance_id": serve["instance_id"], "material_id": "material:mixed-beans",
                                    "citation_ids": ["citation:generated"], "evidence": serve_span}]
        body["action_citations"].append(
            {"instance_id": serve["instance_id"], "citation_ids": ["citation:generated"], "evidence": serve_span}
        )
    body["qualification"] = {"state": "passed", "content_sha256": native.recipes.digest(body),
                             "evidence_pin": {"id": "generated:connection-fixture",
                                              "sha256": "a" * 64}}
    return body


def _quantified_single_case(native, amount, *, unit="g", source_total="100"):
    record = _record(single=True)
    record["ingredients"][0].update(raw_text=source_total + " " + unit + " beans", quantity=source_total, unit=unit)
    record["steps"][0]["raw_text"] = "Mix " + amount + " " + unit + " beans."
    rules = _rules_for(native, record)
    review = _review(native, rules, amount=amount, unit=unit)
    return rules, review, _connections(native, review, quantity_value=amount, quantity_unit=unit)


def _reused_template_case(native):
    record = {
        "id": "generated:reused-template", "kind": "recipe", "title": "Generated pair", "language": "en",
        "ingredients": [
            {"id": "generated:line:beans", "ordinal": 1, "raw_text": "10 g beans", "source_name_text": "beans", "quantity": "10", "unit": "g"},
            {"id": "generated:line:peas", "ordinal": 2, "raw_text": "10 g peas", "source_name_text": "peas", "quantity": "10", "unit": "g"},
        ],
        "steps": [
            {"ordinal": 1, "source_section": "Method", "raw_text": "Serve beans."},
            {"ordinal": 2, "source_section": "Method", "raw_text": "Serve peas."},
        ],
    }
    rules = _rules_for(native, record)
    reviewed = copy.deepcopy(rules["normalized"])
    template = reviewed["fields"]["recipe_menu_template"]
    template["status"], template["unresolved"] = "reviewed", []
    definition = {"action": "serve", "phase": "presentation", "pattern": "Serve {material}.",
                  "slot_types": {"material": "ingredient_reference"}, "source_locale": "en",
                  "grammar_context": {"mood": "imperative", "fixture": "reused-template"}}
    template_id = native.recipes.canonical_template_id(definition)
    template["learned_templates"] = [{"template_id": template_id, "definition": definition}]
    instances = []
    for index, (step, ingredient_id) in enumerate(zip(template["steps"], ("generated:line:beans", "generated:line:peas"))):
        span = copy.deepcopy(step["source_span"])
        instances.append({"instance_id": "generated:serve:" + str(index), "template_id": template_id,
                          "step_id": step["step_id"], "source_order": step["source_order"], "evidence": [span],
                          "slots": {"material": {"type": "ingredient_reference", "value": ingredient_id,
                                                 "evidence": [span], "lexical_unit": None}},
                          "depends_on": [], "unknown_parameters": []})
    template["template_instances"] = instances
    reviewed["fields"]["translation_plan"].update(
        status="ready_for_localized_template_translation", template_ids=[template_id]
    )
    review = {
        "artifact_id": rules["artifact_id"], "artifact_sha256": native.core.artifact_digest(rules),
        "receipt_id": "generated-only:reused-template", "reviewer_id": "generated-test-fixture",
        "reviewer_kind": "assistant", "model_version": rules["versions"]["model_version"],
        "prompt_version": rules["versions"]["prompt_version"], "schema_version": rules["versions"]["schema_version"],
        "template_version": rules["versions"]["template_version"], "reviewed_at": "2026-10-23T00:00:00Z",
        "method": "direct_item_review", "evidence_ref": "fixture-only://not-a-real-review", "decision": "accepted",
        "normalized": reviewed,
        "coverage": [{"item_id": item, "decision": "accepted", "notes": "Generated contract fixture."}
                     for item in rules["review_item_ids"]], "issues": [], "uncertainty": [],
    }
    connections = {
        "schema_version": "offmenu-gold-recipe-connections/1", "data_class": "synthetic",
        "recipe_occurrence_id": "generated:occurrence:reused", "recipe_entity_id": "recipe:generated-pair",
        "entities": [
            {"id": "recipe:generated-pair", "domain": "recipes", "state": "verified"},
            {"id": "ingredient:beans", "domain": "ingredients", "state": "verified"},
            {"id": "ingredient:peas", "domain": "ingredients", "state": "verified"},
        ], "citations": [{"id": "citation:generated", "state": "verified"}],
        "ingredient_links": [], "materials": [], "material_inputs": [], "action_citations": [], "source_servings": None,
    }
    for instance, entity in zip(instances, ("ingredient:beans", "ingredient:peas")):
        spans = copy.deepcopy(instance["evidence"])
        connections["ingredient_links"].append({
            "instance_id": instance["instance_id"], "slot_name": "material",
            "source_ingredient_line_id": instance["slots"]["material"]["value"], "ingredient_entity_id": entity,
            "quantity": None, "quantity_slot_name": None, "unit_slot_name": None,
            "citation_ids": ["citation:generated"], "evidence": spans,
        })
        connections["action_citations"].append({"instance_id": instance["instance_id"],
                                                  "citation_ids": ["citation:generated"], "evidence": spans})
    connections["qualification"] = {"state": "passed", "content_sha256": native.recipes.digest(connections),
                                    "evidence_pin": {"id": "generated:reused-template", "sha256": "c" * 64}}
    return rules, review, connections


def _spanish_case(native):
    record = {
        "id": "generated:spanish", "kind": "recipe", "title": "Frijoles", "language": "es",
        "ingredients": [{"id": "generated:line:frijoles", "ordinal": 1, "raw_text": "10 g frijoles",
                         "source_name_text": "frijoles", "quantity": "10", "unit": "g"}],
        "steps": [{"ordinal": 1, "source_section": "Método", "raw_text": "Servir frijoles."}],
    }
    rules = _rules_for(native, record)
    reviewed = copy.deepcopy(rules["normalized"])
    template = reviewed["fields"]["recipe_menu_template"]
    template["status"], template["unresolved"] = "reviewed", []
    definition = {"action": "serve", "phase": "presentation", "pattern": "Servir {material}.",
                  "slot_types": {"material": "ingredient_reference"}, "source_locale": "es",
                  "grammar_context": {"mood": "imperative", "fixture": "spanish"}}
    template_id = native.recipes.canonical_template_id(definition)
    step = template["steps"][0]
    span = copy.deepcopy(step["source_span"])
    template["learned_templates"] = [{"template_id": template_id, "definition": definition}]
    template["template_instances"] = [{
        "instance_id": "generated:servir", "template_id": template_id, "step_id": step["step_id"],
        "source_order": step["source_order"], "evidence": [span],
        "slots": {"material": {"type": "ingredient_reference", "value": "generated:line:frijoles",
                               "evidence": [span], "lexical_unit": None}},
        "depends_on": [], "unknown_parameters": [],
    }]
    reviewed["fields"]["translation_plan"].update(status="ready_for_localized_template_translation", template_ids=[template_id])
    review = {
        "artifact_id": rules["artifact_id"], "artifact_sha256": native.core.artifact_digest(rules),
        "receipt_id": "generated-only:spanish", "reviewer_id": "generated-test-fixture", "reviewer_kind": "assistant",
        "model_version": rules["versions"]["model_version"], "prompt_version": rules["versions"]["prompt_version"],
        "schema_version": rules["versions"]["schema_version"], "template_version": rules["versions"]["template_version"],
        "reviewed_at": "2026-10-23T00:00:00Z", "method": "direct_item_review",
        "evidence_ref": "fixture-only://not-a-real-review", "decision": "accepted", "normalized": reviewed,
        "coverage": [{"item_id": item, "decision": "accepted", "notes": "Generated contract fixture."}
                     for item in rules["review_item_ids"]], "issues": [], "uncertainty": [],
    }
    connections = {
        "schema_version": "offmenu-gold-recipe-connections/1", "data_class": "synthetic",
        "recipe_occurrence_id": "generated:occurrence:spanish", "recipe_entity_id": "recipe:frijoles",
        "entities": [{"id": "recipe:frijoles", "domain": "recipes", "state": "verified"},
                     {"id": "ingredient:beans", "domain": "ingredients", "state": "verified"}],
        "citations": [{"id": "citation:generated", "state": "verified"}],
        "ingredient_links": [{"instance_id": "generated:servir", "slot_name": "material",
                              "source_ingredient_line_id": "generated:line:frijoles", "ingredient_entity_id": "ingredient:beans",
                              "quantity": None, "quantity_slot_name": None, "unit_slot_name": None,
                              "citation_ids": ["citation:generated"], "evidence": [span]}],
        "materials": [], "material_inputs": [],
        "action_citations": [{"instance_id": "generated:servir", "citation_ids": ["citation:generated"], "evidence": [span]}],
        "source_servings": None,
    }
    connections["qualification"] = {"state": "passed", "content_sha256": native.recipes.digest(connections),
                                    "evidence_pin": {"id": "generated:spanish", "sha256": "d" * 64}}
    interpreted = native.core.validate_and_cache_actual_review(rules, review, store=None, cache_result=False)
    units = native.recipes.recipe_translation_units(interpreted, "en")
    translations = {"Servir {material}.": "Serve {material}.", "frijoles": "beans", "Frijoles": "Beans"}
    receipts = [{
        "unit_id": unit["unit_id"], "unit_sha256": native.core.digest(unit), "translated_text": translations[unit["source_text"]],
        "receipt_id": "generated-only:translation:" + unit["unit_id"], "reviewer_id": "generated-test-fixture",
        "reviewer_kind": "assistant", "method": "direct_unit_review", "evidence_ref": "fixture-only://not-a-real-translation",
        "reviewed_at": "2026-10-23T00:00:00Z", "decision": "accepted",
        "model_version": unit["versions"]["model_version"], "prompt_version": unit["versions"]["prompt_version"],
        "schema_version": unit["versions"]["schema_version"], "template_version": unit["versions"]["template_version"],
    } for unit in units]
    return rules, review, connections, receipts


def _source_literal_case(native, *, count=False, method_evidence=False):
    amount, unit = ('4', 'eggs') if count else ('2', 'handfuls')
    record = _record(single=True)
    record['ingredients'][0].update(quantity=amount, unit=unit,
        raw_text='4 large eggs' if count else '2 handfuls beans',
        source_name_text='eggs' if count else 'beans')
    record['steps'][0]['raw_text'] = 'Mix 4 large eggs.' if count else 'Mix 2 handfuls beans.'
    if method_evidence:
        record['ingredients'][0]['raw_text'] = 'Beans'
    rules = _rules_for(native, record)
    review = _review(native, rules, amount=amount, unit=unit)
    template = review['normalized']['fields']['recipe_menu_template']
    instance = template['template_instances'][0]
    if count:
        definition = template['learned_templates'][0]['definition']
        definition['pattern'] = 'Mix {amount} {material}.'
        del definition['slot_types']['unit']
        del instance['slots']['unit']
        instance['slots']['amount']['value']['descriptor'] = 'large'
        template_id = native.recipes.canonical_template_id(definition)
        template['learned_templates'][0]['template_id'] = template_id
        instance['template_id'] = template_id
        review['normalized']['fields']['translation_plan']['template_ids'] = [template_id]
    connections = _connections(native, review, quantity_value=amount, quantity_unit=unit)
    if count:
        connections['ingredient_links'][0]['unit_slot_name'] = None
    connections['source_literal_quantities'] = [dict(
        source_ingredient_line_id=template['ingredients'][0]['ingredient_id'],
        kind='item-count' if count else 'household-measure', value=amount, unit=unit,
        descriptor='large' if count else None,
        evidence=[_span('/steps/0/raw_text', record['steps'][0]['raw_text'], record['steps'][0]['raw_text'])]
                 if method_evidence else [_span('/ingredients/0/raw_text', record['ingredients'][0]['raw_text'],
                        record['ingredients'][0]['raw_text'])], citation_ids=['citation:generated'])]
    connections['qualification']['content_sha256'] = native.recipes.digest(
        {key: value for key, value in connections.items() if key != 'qualification'})
    return rules, review, connections


class GoldRecipeActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native_source = PinnedNativeFixture().load()
        sys.path.insert(0, str(ROOT))
        cls.actions = importlib.import_module("gold_recipe_actions")
        cls.native = cls.actions.NativeRecipeHelpers(
            source_pin=PIN,
            module_sha256=cls.native_source.expected_hashes,
            canonical_template_id=cls.native_source.recipes.canonical_template_id,
            validate_reviewed_template=cls.native_source.recipes.validate_reviewed_template,
            validate_and_cache_actual_review=cls.native_source.core.validate_and_cache_actual_review,
            recipe_translation_units=cls.native_source.recipes.recipe_translation_units,
            validate_and_cache_translation=cls.native_source.core.validate_and_cache_translation,
            normalize_quantity=cls.native_source.domains.normalize_quantity,
            digest=cls.native_source.recipes.digest,
        )

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(ROOT))
        cls.native_source.close()

    def _connected(self, **kwargs):
        single = kwargs.pop("single", False)
        rules = _rules(self.native_source, single=single)
        review = _review(self.native_source, rules, dependency=kwargs.pop("dependency", True))
        connections = _connections(self.native_source, review, **kwargs)
        return rules, review, connections

    def test_source_literal_measure_and_large_count_preserve_native_scaffold(self):
        for count, text in ((False, 'Mix 2 handfuls beans.'), (True, 'Mix 4 large eggs.')):
            with self.subTest(count=count):
                rules, review, connections = _source_literal_case(self.native_source, count=count)
                frozen = copy.deepcopy((rules, review, connections))
                result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
                self.assertEqual('ready-for-review', result['status'], result['holds'])
                self.assertEqual(text, result['actions'][0]['english_text'])
                allocation = result['ingredient_links'][0]['allocation']
                self.assertEqual('source-literal', allocation['status'])
                self.assertIsNone(allocation['metric_normalization'])
                self.assertEqual('not-qualified', allocation['scaling'])
                self.assertEqual('unresolved', review['normalized']['fields']['recipe_menu_template']['ingredients'][0]['quantity']['status'])
                self.assertEqual(frozen, (rules, review, connections))

    def test_no_literal_contract_keeps_legacy_unsupported_unit_hold(self):
        rules, review, connections = _source_literal_case(self.native_source)
        del connections['source_literal_quantities']
        connections['qualification']['content_sha256'] = self.native_source.recipes.digest(
            {k: v for k, v in connections.items() if k != 'qualification'})
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual([{'code': 'recipe_ingredient_quantity_unresolved', 'target': 'recipe'}], result['holds'])

    def test_literal_profile_rejects_scaling_and_qualitative_allocation_bypass(self):
        for change in ('scaling', 'null-allocation', 'duplicate-contract', 'wrong-evidence', 'missing-descriptor'):
            with self.subTest(change=change):
                rules, review, connections = _source_literal_case(self.native_source, count=True)
                kwargs = {}
                if change == 'scaling': kwargs['requested_servings'] = '2'
                elif change == 'null-allocation': connections['ingredient_links'][0]['quantity'] = None
                elif change == 'duplicate-contract': connections['source_literal_quantities'] *= 2
                elif change == 'wrong-evidence': connections['source_literal_quantities'][0]['evidence'][0]['pointer'] = '/ingredients/1/raw_text'
                else: connections['source_literal_quantities'][0]['descriptor'] = None
                connections['qualification']['content_sha256'] = self.native_source.recipes.digest(
                    {k: v for k, v in connections.items() if k != 'qualification'})
                result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections, **kwargs)
                self.assertEqual('held', result['status'])

    def test_verified_pinned_helpers_produce_ordered_english_actions_and_material_flow(self):
        rules, review, connections = self._connected()
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "ready-for-review")
        self.assertEqual([row["action_id"] for row in result["actions"]], ["generated:mix", "generated:serve"])
        self.assertEqual([row["english_text"] for row in result["actions"]], ["Mix 40 g beans.", "Serve beans."])
        self.assertEqual(result["dependencies"], [{"action_id": "generated:serve", "depends_on": "generated:mix"}])
        self.assertEqual(result["material_inputs"][0]["material_id"], "material:mixed-beans")
        self.assertEqual(result["native_source_pin"], PIN)
        self.assertEqual(result["native_module_sha256"], self.actions.NATIVE_MODULES)

    def test_reference_ids_must_be_nonempty_strings(self):
        for field in ("entities", "citations"):
            for invalid in (None, {}, [], 7, True, "", "  "):
                with self.subTest(field=field, invalid=invalid):
                    rules, review, connections = self._connected()
                    if field == "entities":
                        connections["entities"][1]["id"] = invalid
                        for link in connections["ingredient_links"]:
                            link["ingredient_entity_id"] = invalid
                    else:
                        connections["citations"][0]["id"] = invalid
                        for group in ("ingredient_links", "materials", "material_inputs", "action_citations"):
                            for row in connections[group]:
                                row["citation_ids"] = [invalid]
                    connections["qualification"]["content_sha256"] = self.native.digest(
                        {k: v for k, v in connections.items() if k != "qualification"})
                    result = self.actions.connect_recipe_actions(
                        rules, review, native=self.native, connections=connections)
                    self.assertEqual(result["status"], "held")
                    self.assertIn({"code": "gold_reference_id_required", "target": "recipe"}, result["holds"])

    def test_material_rows_reject_undeclared_properties(self):
        for field, code in (("materials", "material_shape"), ("material_inputs", "material_input_shape")):
            with self.subTest(field=field):
                rules, review, connections = self._connected()
                connections[field][0]["undeclared"] = "source annotation is not an output field"
                connections["qualification"]["content_sha256"] = self.native.digest(
                    {k: v for k, v in connections.items() if k != "qualification"})
                result = self.actions.connect_recipe_actions(
                    rules, review, native=self.native, connections=connections)
                self.assertEqual(result["status"], "held")
                self.assertTrue(any(h["code"] == code for h in result["holds"]))
                self.assertFalse(any("undeclared" in row for row in result[field]))

    def test_pinned_fixture_does_not_need_git_history(self):
        with patch("subprocess.run", side_effect=AssertionError("test helpers must not require Git history")):
            blob = _blob("manual-action/normalize_recipes.py")
        self.assertEqual(hashlib.sha256(blob).hexdigest(), self.actions.NATIVE_MODULES["normalize_recipes.py"])

    def test_missing_or_corrupt_fixture_never_uses_runtime_source(self):
        with tempfile.TemporaryDirectory(prefix="offmenu-missing-fixture-") as directory:
            with patch(__name__ + ".NATIVE_FIXTURE", Path(directory)):
                with patch("subprocess.run", side_effect=AssertionError("no alternate history or runtime source")):
                    with self.assertRaises(FileNotFoundError):
                        _blob("manual-action/normalize_recipes.py")
                    (Path(directory) / "normalize_recipes.py").write_bytes(b"not the immutable fixture")
                    with self.assertRaisesRegex(ValueError, "fixture digest mismatch"):
                        _blob("manual-action/normalize_recipes.py")

    def test_scaling_preserves_original_allocation_and_scales_only_amount(self):
        rules, review, connections = self._connected(single=True)
        result = self.actions.connect_recipe_actions(
            rules, review, native=self.native, connections=connections, requested_servings="4"
        )
        self.assertEqual(result["status"], "ready-for-review")
        self.assertEqual(result["scale_factor"], "2")
        self.assertEqual(result["actions"][0]["english_text"], "Mix 80 g beans.")
        allocation = result["ingredient_links"][0]["allocation"]
        self.assertEqual(allocation["original"], {"value": "40", "unit": "g"})
        self.assertEqual((allocation["scaled_min"], allocation["scaled_max"]), ("80", "80"))

    def test_unknown_servings_holds_instead_of_scaling(self):
        rules, review, connections = self._connected()
        connections["source_servings"] = None
        connections["qualification"]["content_sha256"] = self.native_source.recipes.digest(
            {key: value for key, value in connections.items() if key != "qualification"}
        )
        result = self.actions.connect_recipe_actions(
            rules, review, native=self.native, connections=connections, requested_servings="4"
        )
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "source_servings_unknown", "target": "recipe"}, result["holds"])

    def test_overallocation_is_held_and_does_not_claim_ready(self):
        rules, review, connections = self._connected()
        connections["ingredient_links"][0]["quantity"] = {"value": "101", "unit": "g"}
        connections["qualification"]["content_sha256"] = self.native_source.recipes.digest(
            {key: value for key, value in connections.items() if key != "qualification"}
        )
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "allocation_slot_quantity_mismatch", "target": "generated:mix:material"}, result["holds"])

    def test_matching_semantic_overallocation_reaches_conservation_hold(self):
        rules, review, connections = _quantified_single_case(self.native_source, "101")
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "ingredient_quantity_not_conserved", "target": "generated:mix:material"}, result["holds"])

    def test_null_allocation_cannot_bypass_quantified_ingredient_conservation(self):
        for amount in ("101", "40"):
            with self.subTest(amount=amount):
                rules, review, connections = _quantified_single_case(self.native_source, amount)
                connections["ingredient_links"][0].update(
                    quantity=None, quantity_slot_name=None, unit_slot_name=None)
                connections["qualification"]["content_sha256"] = self.native.digest(
                    {k: v for k, v in connections.items() if k != "qualification"})
                result = self.actions.connect_recipe_actions(
                    rules, review, native=self.native, connections=connections)
                self.assertEqual(result["status"], "held")
                self.assertIn({"code": "quantified_ingredient_allocation_required",
                               "target": "generated:mix:material"}, result["holds"])
                self.assertEqual(result["actions"], [])

    def test_separate_unit_slot_requires_explicit_allocation_unit_binding(self):
        rules, review, connections = _quantified_single_case(self.native_source, "40")
        connections["ingredient_links"][0]["unit_slot_name"] = None
        connections["qualification"]["content_sha256"] = self.native.digest(
            {k: v for k, v in connections.items() if k != "qualification"})
        result = self.actions.connect_recipe_actions(
            rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "allocation_unit_binding_required",
                       "target": "generated:mix:material"}, result["holds"])
        self.assertEqual(result["actions"], [])

    def test_range_normalization_is_exact_and_unsupported_allocation_unit_is_held(self):
        ranged = self.native.normalize_quantity("40-60", "g")
        self.assertEqual((ranged["min"], ranged["max"], ranged["unit"]), ("40", "60", "g"))
        rules, review, connections = _quantified_single_case(self.native_source, "40-60")
        rendered = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(rendered["status"], "ready-for-review")
        self.assertEqual(rendered["actions"][0]["english_text"], "Mix 40–60 g beans.")
        rules, review, connections = _quantified_single_case(self.native_source, "0.04-0.06", unit="kg", source_total="1")
        converted = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(converted["status"], "ready-for-review")
        self.assertEqual(converted["actions"][0]["english_text"], "Mix 0.04–0.06 kg beans.")
        rules, review, connections = self._connected()
        connections["ingredient_links"][0]["quantity"] = {"value": "1", "unit": "cup"}
        connections["qualification"]["content_sha256"] = self.native_source.recipes.digest(
            {key: value for key, value in connections.items() if key != "qualification"}
        )
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "unsupported_quantity", "target": "generated:mix:material"}, result["holds"])

    def test_material_input_requires_explicit_earlier_dependency(self):
        rules, review, connections = self._connected(dependency=False)
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "material_dependency_missing", "target": "recipe"}, result["holds"])

    def test_native_pin_or_hash_mismatch_is_held(self):
        rules, review, connections = self._connected()
        bad_native = self.actions.NativeRecipeHelpers(
            source_pin=PIN, module_sha256={**self.native_source.expected_hashes, "normalize_recipes.py": "b" * 64},
            canonical_template_id=self.native.canonical_template_id,
            validate_reviewed_template=self.native.validate_reviewed_template,
            validate_and_cache_actual_review=self.native.validate_and_cache_actual_review,
            recipe_translation_units=self.native.recipe_translation_units,
            validate_and_cache_translation=self.native.validate_and_cache_translation,
            normalize_quantity=self.native.normalize_quantity, digest=self.native.digest,
        )
        result = self.actions.connect_recipe_actions(rules, review, native=bad_native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "immutable_native_dependency_mismatch", "target": "recipe"}, result["holds"])

    def test_reused_template_keeps_each_instance_ingredient_argument_distinct(self):
        rules, review, connections = _reused_template_case(self.native_source)
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "ready-for-review")
        self.assertEqual([row["english_text"] for row in result["actions"]], ["Serve beans.", "Serve peas."])
        self.assertEqual([row["source_ingredient_line_id"] for row in result["ingredient_links"]],
                         ["generated:line:beans", "generated:line:peas"])

    def test_malformed_connection_returns_held_not_exception(self):
        rules, review, connections = self._connected()
        connections["ingredient_links"][0]["evidence"] = [{"pointer": "/steps/0/raw_text"}]
        connections["qualification"]["content_sha256"] = self.native_source.recipes.digest(
            {key: value for key, value in connections.items() if key != "qualification"}
        )
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(result["status"], "held")
        self.assertTrue(result["holds"])

    def test_english_only_target_is_held(self):
        rules, review, connections = self._connected()
        result = self.actions.connect_recipe_actions(
            rules, review, native=self.native, connections=connections, target_language="fr"
        )
        self.assertEqual(result["status"], "held")
        self.assertIn({"code": "English_output_only", "target": "recipe"}, result["holds"])

    def test_non_english_source_requires_exact_reviewed_translation_receipts(self):
        rules, review, connections, receipts = _spanish_case(self.native_source)
        missing = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        self.assertEqual(missing["status"], "held")
        self.assertTrue(missing["holds"])
        result = self.actions.connect_recipe_actions(
            rules, review, native=self.native, connections=connections, translation_receipts=receipts
        )
        self.assertEqual(result["status"], "ready-for-review")
        self.assertEqual(result["actions"][0]["english_text"], "Serve beans.")
        stale = copy.deepcopy(receipts)
        stale[0]["unit_sha256"] = "e" * 64
        rejected = self.actions.connect_recipe_actions(
            rules, review, native=self.native, connections=connections, translation_receipts=stale
        )
        self.assertEqual(rejected["status"], "held")
        self.assertTrue(rejected["holds"])

    def test_fixed_gold_schema_round_trip_and_foreign_key_rejection(self):
        schema = (ROOT / "gold.schema.sql").read_text(encoding="utf-8")
        with sqlite3.connect(":memory:") as database:
            database.executescript(schema)
            database.execute("INSERT INTO gold_citations VALUES(?,?)", ("citation:fixture", "{}"))
            database.execute("INSERT INTO gold_entities VALUES(?,?,?,?,?,?)",
                             ("recipe:fixture", "resource:fixture", "recipes", "recipe", "verified", "{}"))
            database.execute("INSERT INTO gold_occurrences VALUES(?,?,?,?,?,?,?,?,?,?)",
                             ("occurrence:fixture", "recipes", "generated", "v1", "fixture", "a" * 64,
                              None, "watermark:fixture", "verified", "{}"))
            database.execute("INSERT INTO gold_entity_occurrences VALUES(?,?)", ("recipe:fixture", "occurrence:fixture"))
            database.execute("INSERT INTO gold_support VALUES(?,?,?,?,?,?)",
                             ("support:fixture", "recipe", "recipe:fixture", "citation:fixture", "source", "b" * 64))
            self.assertEqual(database.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("INSERT INTO gold_entity_occurrences VALUES(?,?)", ("missing:entity", "occurrence:fixture"))
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("INSERT INTO gold_edges VALUES(?,?,?,?,?,?,?)",
                                 ("edge:fixture", "rel:fixture", "recipe:fixture", "uses", "missing:entity", "verified", "{}"))

    def test_recipe_projection_json_and_sql_round_trip_with_join_and_rejections(self):
        import jsonschema
        rules, review, connections = self._connected()
        result = self.actions.connect_recipe_actions(rules, review, native=self.native, connections=connections)
        schema = json.loads((ROOT / "gold-recipe-actions.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(result)
        base = (ROOT / "gold.schema.sql").read_text(encoding="utf-8")
        extension = (ROOT / "gold-recipe-actions.schema.sql").read_text(encoding="utf-8")
        dump = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
        with sqlite3.connect(":memory:") as database:
            database.executescript(base)
            database.executescript(extension)
            database.execute("INSERT INTO gold_citations VALUES(?,?)", ("citation:generated", "{}"))
            database.execute("INSERT INTO gold_entities VALUES(?,?,?,?,?,?)",
                             (result["recipe_entity_id"], "resource:recipe", "recipes", "recipe", "verified", "{}"))
            database.execute("INSERT INTO gold_entities VALUES(?,?,?,?,?,?)",
                             ("ingredient:beans", "resource:beans", "ingredients", "ingredient", "verified", "{}"))
            database.execute("INSERT INTO gold_occurrences VALUES(?,?,?,?,?,?,?,?,?,?)",
                             (result["source_occurrence_id"], "recipes", "generated", "v1", "generated", "a" * 64,
                              None, "watermark:generated", "verified", "{}"))
            database.execute("INSERT INTO gold_entity_occurrences VALUES(?,?)",
                             (result["recipe_entity_id"], result["source_occurrence_id"]))
            database.execute("INSERT INTO gold_recipe_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (result["run_id"], result["source_occurrence_id"], result["recipe_entity_id"], result["data_class"],
                              result["target_language"], result["schema_version"], result["native_source_pin"],
                              dump(result["native_module_sha256"]), result["rules_artifact_sha256"], result["semantic_review_sha256"],
                              result["translation_receipts_sha256"], result["connection_sha256"], result["source_original_sha256"],
                              result["scale_factor"], result["status"], result["gold_admission"]))
            for template in result["native_templates"]:
                database.execute("INSERT INTO gold_recipe_templates VALUES(?,?,?)",
                                 (result["run_id"], template["template_id"], dump(template["definition"])))
            instances = {row["instance_id"]: row for row in result["native_instances"]}
            sequence = {row["action_id"]: row["sequence_index"] for row in result["actions"]}
            for action in result["actions"]:
                native_instance = instances[action["action_id"]]
                database.execute("INSERT INTO gold_recipe_actions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (result["run_id"], action["action_id"], action["template_id"], action["step_id"],
                                  action["source_order"], action["sequence_index"], action["original_text"], action["source_language"],
                                  action["english_text"], action["action_concept"], action["phase"], dump(native_instance),
                                  dump(action["unknown_parameters"]), dump(action["evidence"])))
            for row in result["dependencies"]:
                database.execute("INSERT INTO gold_recipe_dependencies VALUES(?,?,?,?,?)",
                                 (result["run_id"], row["action_id"], row["depends_on"],
                                  sequence[row["action_id"]], sequence[row["depends_on"]]))
            for row in result["ingredient_links"]:
                database.execute("INSERT INTO gold_recipe_ingredients VALUES(?,?,?,?,?,?,?)",
                                 (result["run_id"], row["action_id"], row["slot_name"], row["source_ingredient_line_id"],
                                  row["ingredient_entity_id"], None if row["allocation"] is None else dump(row["allocation"]), dump(row["evidence"])))
            for row in result["materials"]:
                database.execute("INSERT INTO gold_recipe_materials VALUES(?,?,?,?,?,?)",
                                 (result["run_id"], row["material_id"], row["producer_instance_id"],
                                  sequence[row["producer_instance_id"]], row["label"], dump(row["evidence"])))
            for row in result["material_inputs"]:
                producer = next(item for item in result["materials"] if item["material_id"] == row["material_id"])
                database.execute("INSERT INTO gold_recipe_material_inputs VALUES(?,?,?,?,?,?)",
                                 (result["run_id"], row["instance_id"], row["material_id"], sequence[row["instance_id"]],
                                  sequence[producer["producer_instance_id"]], dump(row["evidence"])))
            for row in result["supports"]:
                if row["target_kind"] == "action":
                    database.execute("INSERT INTO gold_recipe_action_support VALUES(?,?,?,?)",
                                     (result["run_id"], row["action_id"], row["citation_id"], dump(row["evidence"])))
                elif row["target_kind"] == "ingredient":
                    database.execute("INSERT INTO gold_recipe_ingredient_support VALUES(?,?,?,?,?)",
                                     (result["run_id"], row["action_id"], row["slot_name"], row["citation_id"], dump(row["evidence"])))
                elif row["target_kind"] == "material":
                    database.execute("INSERT INTO gold_recipe_material_support VALUES(?,?,?,?)",
                                     (result["run_id"], row["material_id"], row["citation_id"], dump(row["evidence"])))
                elif row["target_kind"] == "material_input":
                    database.execute("INSERT INTO gold_recipe_material_input_support VALUES(?,?,?,?,?)",
                                     (result["run_id"], row["action_id"], row["material_id"], row["citation_id"], dump(row["evidence"])))
            joined = database.execute("""
                SELECT a.english_text, i.ingredient_entity_id, m.material_id, s.citation_id
                FROM gold_recipe_actions a
                JOIN gold_recipe_ingredients i ON i.run_id=a.run_id AND i.action_id=a.action_id
                JOIN gold_recipe_action_support s ON s.run_id=a.run_id AND s.action_id=a.action_id
                LEFT JOIN gold_recipe_materials m ON m.run_id=a.run_id AND m.producer_instance_id=a.action_id
                WHERE a.run_id=? AND a.action_id='generated:mix'
            """, (result["run_id"],)).fetchone()
            self.assertEqual(joined, ("Mix 40 g beans.", "ingredient:beans", "material:mixed-beans", "citation:generated"))
            self.assertEqual(database.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("UPDATE gold_recipe_actions SET english_text='changed' WHERE run_id=? AND action_id='generated:mix'",
                                 (result["run_id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("INSERT INTO gold_recipe_ingredients VALUES(?,?,?,?,?,?,?)",
                                 (result["run_id"], "generated:mix", "bad", "line", "missing:ingredient", None, "[]"))
            database.execute("SAVEPOINT no_material_dependency")
            database.execute("DELETE FROM gold_recipe_material_input_support WHERE run_id=?", (result["run_id"],))
            database.execute("DELETE FROM gold_recipe_material_inputs WHERE run_id=?", (result["run_id"],))
            database.execute("DELETE FROM gold_recipe_dependencies WHERE run_id=?", (result["run_id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("INSERT INTO gold_recipe_material_inputs VALUES(?,?,?,?,?,?)",
                                 (result["run_id"], "generated:serve", "material:mixed-beans", 1, 0,
                                  dump(result["material_inputs"][0]["evidence"])))
            database.execute("ROLLBACK TO no_material_dependency")
            database.execute("RELEASE no_material_dependency")


if __name__ == "__main__":
    unittest.main()
