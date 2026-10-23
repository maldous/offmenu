"""Generated inputs and owned in-memory SQLite only; no actual cache/gold I/O."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "gold_english_cache.py"
spec = importlib.util.spec_from_file_location("worker05_gold_english_cache", SOURCE)
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


def pin(name):
    return {"id": "synthetic:" + name, "sha256": hashlib.sha256(name.encode()).hexdigest()}


def fixture(operation="translation"):
    context = {"country": "FR", "cut": None, "fat": "unspecified", "preparation": "boiled and drained",
               "state": "cooked", "originalBasis": "100 g", "unit": "mg", "method": None,
               "date": None, "uncertainty": "synthetic numbers only"}
    source = {"sourceId": "synthetic:source", "releaseId": "fixture-1", "recordId": "row-1",
              "recordSelector": "/rows/1", "locale": "fr", "originalSHA256": pin("original")["sha256"],
              "parsedArtifactSHA256": pin("parsed")["sha256"]}
    scope = {"domain": "ingredients", "entityId": "synthetic:entity", "fieldPointer": "/label",
             "observationIds": ["synthetic:observation"], "context": context}
    content = {"dataClass": "synthetic", "originalText": "Épinards cuits et égouttés",
               "originalMeasurement": "2,7 mg pour 100 g", "value": "2.7", "basis": "100 g",
               "citations": [{"citationId": "synthetic:citation", "evidencePin": pin("citation")}]}
    prompt = "Translate this name only; keep original measurement and context unchanged."
    request = {"schemaVersion": cache.REQUEST_SCHEMA, "source": source, "scope": scope,
               "rights": {"state": "permitted", "operation": operation, "sourceBinding": copy.deepcopy(source),
                          "scope": copy.deepcopy(scope), "evidencePin": pin("rights")},
               "eligibleManifestPin": pin("eligible"), "operation": operation, "targetLocale": "en",
               "inputContent": content, "inputContentSHA256": cache.content_digest(content),
               "producer": {"kind": "ai", "id": "synthetic-fixture-producer", "version": "fixture-only-1", "settings": {"temperature": 0}},
               "prompt": {"version": "fixture-1", "content": prompt, "sha256": hashlib.sha256(prompt.encode()).hexdigest()},
               "adapterVersion": "1", "outputSchemaVersion": "1", "rulesVersion": "fixture-1"}
    response = {"schemaVersion": cache.RESPONSE_SCHEMA, "kind": operation, "originalText": content["originalText"],
                "englishText": "Boiled and drained spinach", "observationIds": copy.deepcopy(scope["observationIds"]),
                "context": copy.deepcopy(context), "citationIds": ["synthetic:citation"], "uncertainty": "synthetic-only",
                "derivation": None, "correction": None}
    if operation in {"inference", "estimate", "unit-normalization"}:
        response["derivation"] = {"type": {"inference": "culinary-inference", "estimate": "derived-estimate", "unit-normalization": "unit-normalization"}[operation],
                                  "label": "Synthetic derived output, not observed fact", "method": "invented fixture method",
                                  "basis": "synthetic input", "uncertainty": "not food evidence",
                                  "inputContentSHA256": request["inputContentSHA256"], "supportingCitationIds": ["synthetic:citation"],
                                  "assertedField": {"inference": "culinary-interpretation", "estimate": "nutrient-estimate", "unit-normalization": "comparable-unit"}[operation], "observedFact": False}
    if operation == "correction":
        response["correction"] = {"parentResponseSHA256": pin("prior-output")["sha256"], "reason": "synthetic wording correction"}
    return request, response, validation(request, response)


def validation(request, response):
    return {"state": "passed", "requestKey": cache.request_key(request), "responseSHA256": cache.content_digest(response),
            "evidencePin": pin("synthetic-validation"), "validatorId": "synthetic-test-only", "unsupportedFacts": False}


class EnglishCacheTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        cache.initialize_cache(self.connection)
        self.request, self.response, self.validation = fixture()

    def tearDown(self):
        self.connection.close()

    def store(self, request=None, response=None, receipt=None):
        return cache.store_cached(self.connection, request or self.request, response or self.response, receipt or self.validation)

    def test_repeat_exact_hit_and_idempotent_append_no_model_client(self):
        first, second = self.store(), self.store()
        self.assertEqual(first["entryKey"], second["entryKey"])
        hit = cache.lookup_cached(self.connection, self.request)
        self.assertEqual(hit["state"], "hit")
        self.assertEqual(hit["evidence"]["goldAdmission"], "not-assigned-by-cache")
        self.assertEqual(hit["evidence"]["dataClass"], "synthetic")
        self.assertEqual(self.connection.execute(f"SELECT count(*) FROM {cache.TABLE}").fetchone()[0], 1)

    def test_current_binding_changes_never_reuse(self):
        self.store()
        changes = [("producer", "id", "other"), ("producer", "version", "other"),
                   ("source", "sourceId", "other"), ("source", "releaseId", "other"),
                   ("source", "recordId", "other"), ("source", "locale", "de"),
                   ("scope", "entityId", "other"), ("scope", "fieldPointer", "/other"),
                   ("scope", "observationIds", ["other"])]
        for block, field, value in changes:
            with self.subTest(block=block, field=field):
                q = copy.deepcopy(self.request); q[block][field] = value
                if block == "source": q["rights"]["sourceBinding"] = copy.deepcopy(q["source"])
                if block == "scope": q["rights"]["scope"] = copy.deepcopy(q["scope"])
                self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "miss")
        for field in ["adapterVersion", "outputSchemaVersion", "rulesVersion"]:
            q = copy.deepcopy(self.request); q[field] = "other"
            self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "miss")

    def test_all_context_fields_keyed_and_original_not_overwritten(self):
        self.store()
        for field in self.request["scope"]["context"]:
            q = copy.deepcopy(self.request); q["scope"]["context"][field] = "different-context"
            q["rights"]["scope"] = copy.deepcopy(q["scope"])
            self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "miss")
        self.assertEqual(self.request["inputContent"]["originalMeasurement"], "2,7 mg pour 100 g")

    def test_prompt_content_settings_citation_and_native_bytes_keyed(self):
        self.store()
        for field in ["prompt", "settings", "citations", "native"]:
            q = copy.deepcopy(self.request)
            if field == "prompt":
                q["prompt"]["content"] += " changed"; q["prompt"]["sha256"] = hashlib.sha256(q["prompt"]["content"].encode()).hexdigest()
            elif field == "settings": q["producer"]["settings"]["temperature"] = 0.3
            elif field == "citations": q["inputContent"]["citations"][0]["evidencePin"] = pin("other-source")
            else: q["inputContent"]["originalText"] = "Epinards cuits et égouttés"
            q["inputContentSHA256"] = cache.content_digest(q["inputContent"])
            self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "miss")

    def test_missing_unknown_model_prompt_rights_eligibility_held(self):
        for kind in ["model", "version", "rights", "rights-scope", "manifest", "prompt"]:
            q = copy.deepcopy(self.request)
            if kind == "model": q["producer"]["id"] = "unknown"
            if kind == "version": q["producer"]["version"] = None
            if kind == "rights": q["rights"]["state"] = "held"
            if kind == "rights-scope": q["rights"]["scope"]["entityId"] = "foreign"
            if kind == "manifest": q["eligibleManifestPin"] = None
            if kind == "prompt": q["prompt"]["sha256"] = pin("wrong")["sha256"]
            self.assertEqual(cache.qualify_entry(q, self.response, self.validation)["state"], "held")
            self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "held")

    def test_current_rights_rechecked_not_copied_from_cached_envelope(self):
        self.store(); q = copy.deepcopy(self.request); q["rights"]["state"] = "denied"
        self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "held")

    def test_unusable_release_pins_never_qualify_store_or_hit(self):
        for release in [None, "", False, {}, "unknown"]:
            with self.subTest(release=release):
                q = copy.deepcopy(self.request)
                q["source"]["releaseId"] = release
                q["rights"]["sourceBinding"] = copy.deepcopy(q["source"])
                v = validation(q, self.response)
                qualified = cache.qualify_entry(q, self.response, v)
                stored = self.store(request=q, receipt=v)
                looked_up = cache.lookup_cached(self.connection, q)
                self.assertEqual((qualified["state"], stored["state"], looked_up["state"]), ("held", "held", "held"))
                saved = self.connection.execute(f"SELECT request_json FROM {cache.TABLE} WHERE entry_key=?", (stored["entryKey"],)).fetchone()[0]
                self.assertEqual(json.loads(saved)["source"]["releaseId"], release)
                self.connection.execute(f"UPDATE {cache.TABLE} SET state='qualified' WHERE entry_key=?", (stored["entryKey"],))
                self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "held")

    def test_padded_unknown_pins_never_qualify_store_or_hit(self):
        fields = [("producer", "id"), ("producer", "version"), ("prompt", "version"), ("source", "locale")]
        for block, field in fields:
            for unknown in [" unknown ", "\tUnAvAiLaBlE\n", "\u2003UNEXPOSED\u2003"]:
                with self.subTest(block=block, field=field, unknown=unknown):
                    q = copy.deepcopy(self.request)
                    q[block][field] = unknown
                    if block == "source":
                        q["rights"]["sourceBinding"] = copy.deepcopy(q["source"])
                    v = validation(q, self.response)
                    qualified = cache.qualify_entry(q, self.response, v)
                    stored = self.store(request=q, receipt=v)
                    looked_up = cache.lookup_cached(self.connection, q)
                    self.assertEqual((qualified["state"], stored["state"], looked_up["state"]), ("held", "held", "held"))
                    saved = self.connection.execute(f"SELECT request_json FROM {cache.TABLE} WHERE entry_key=?", (stored["entryKey"],)).fetchone()[0]
                    self.assertEqual(json.loads(saved)[block][field], unknown)
                    self.connection.execute(f"UPDATE {cache.TABLE} SET state='qualified' WHERE entry_key=?", (stored["entryKey"],))
                    self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "held")

    def test_valid_release_locale_pins_keep_exact_lexical_identity(self):
        keys = set()
        for release, locale in [("release-A", "es"), ("release-B", "en"), ("Release-A", "es")]:
            q = copy.deepcopy(self.request)
            q["source"].update(releaseId=release, locale=locale)
            q["rights"]["sourceBinding"] = copy.deepcopy(q["source"])
            v = validation(q, self.response)
            self.assertEqual(cache.qualify_entry(q, self.response, v)["state"], "qualified")
            self.assertEqual(cache.lookup_cached(self.connection, q)["state"], "miss")
            stored = self.store(request=q, receipt=v)
            self.assertEqual(stored["state"], "qualified")
            hit = cache.lookup_cached(self.connection, q)
            self.assertEqual(hit["state"], "hit")
            self.assertEqual(hit["evidence"]["source"]["releaseId"], release)
            self.assertEqual(hit["evidence"]["source"]["locale"], locale)
            keys.add(cache.request_key(q))
        self.assertEqual(len(keys), 3)

    def test_validated_plain_evidence_preserves_many_citations_and_context(self):
        q, r = copy.deepcopy(self.request), copy.deepcopy(self.response)
        q["inputContent"]["citations"].append({"citationId": "synthetic:second", "evidencePin": pin("second")})
        q["inputContentSHA256"] = cache.content_digest(q["inputContent"])
        r["citationIds"].append("synthetic:second")
        result = cache.qualify_entry(q, r, validation(q, r))
        self.assertEqual(result["state"], "qualified")
        self.assertEqual(result["evidence"]["citationIds"], r["citationIds"])
        self.assertEqual(result["evidence"]["scope"]["context"], q["scope"]["context"])
        result["evidence"]["scope"]["context"]["country"] = "changed"
        self.assertEqual(q["scope"]["context"]["country"], "FR")

    def test_inference_estimate_and_unit_derivation_are_separate(self):
        for operation in ["inference", "estimate", "unit-normalization", "correction"]:
            q, r, v = fixture(operation)
            self.assertEqual(cache.qualify_entry(q, r, v)["state"], "qualified")
            if operation != "correction":
                r["derivation"]["observedFact"] = True
                self.assertEqual(cache.qualify_entry(q, r, validation(q, r))["state"], "held")

    def test_inferred_barcode_licence_allergen_nutrient_fact_rejected(self):
        for field in ["barcode", "licence", "allergen-free", "observed-nutrient"]:
            q, r, _ = fixture("inference"); r["derivation"]["assertedField"] = field
            self.assertEqual(cache.qualify_entry(q, r, validation(q, r))["state"], "held")

    def test_typed_estimate_value_and_supports_cannot_hide_facts(self):
        q, r, _ = fixture("estimate")
        r["derivation"].update(value="1.2", unit="mg", supportingObservationIds=["synthetic:observation"])
        self.assertEqual(cache.qualify_entry(q, r, validation(q, r))["state"], "qualified")
        for field, value in [("nutrientFact", "12"), ("value", float("nan")), ("unit", None), ("supportingObservationIds", ["foreign"])]:
            altered = copy.deepcopy(r); altered["derivation"][field] = value
            try:
                v = validation(q, altered)
            except cache.CacheError:
                v = self.validation
            self.assertEqual(cache.qualify_entry(q, altered, v)["state"], "held")

    def test_citation_confidence_missing_basis_and_context_poison_rejected(self):
        for change in ["confidence", "basis", "context", "citation", "native", "extra-fact", "correction"]:
            q, r, _ = fixture("estimate" if change == "basis" else "correction" if change == "correction" else "translation")
            if change == "confidence": q["inputContent"]["citations"] = [{"citationId": "guess", "confidence": 0.99}]
            if change == "basis": r["derivation"]["basis"] = ""
            if change == "context": r["context"]["state"] = "raw"
            if change == "citation": r["citationIds"] = ["not-input"]
            if change == "native": r["originalText"] = "overwritten"
            if change == "extra-fact": r["nutrientValue"] = "12"
            if change == "correction": r["correction"] = None
            q["inputContentSHA256"] = cache.content_digest(q["inputContent"])
            self.assertEqual(cache.qualify_entry(q, r, validation(q, r))["state"], "held")

    def test_validation_binds_exact_request_response_and_evidence(self):
        for field, value in [("requestKey", "wrong"), ("responseSHA256", "wrong"), ("evidencePin", None), ("unsupportedFacts", True), ("state", "pending")]:
            v = copy.deepcopy(self.validation); v[field] = value
            self.assertEqual(cache.qualify_entry(self.request, self.response, v)["state"], "held")

    def test_different_nondeterministic_outputs_retained_not_overwritten(self):
        first = self.store(); r = copy.deepcopy(self.response); r["englishText"] = "Another synthetic wording"
        second = self.store(response=r, receipt=validation(self.request, r))
        self.assertNotEqual(first["entryKey"], second["entryKey"])
        self.assertEqual(cache.lookup_cached(self.connection, self.request)["reasons"], ["multiple_qualified_variants"])
        self.assertEqual(cache.lookup_cached(self.connection, self.request, entry_key=first["entryKey"])["state"], "hit")

    def test_held_response_persisted_without_becoming_qualified(self):
        v = copy.deepcopy(self.validation); v["state"] = "pending"
        self.assertEqual(self.store(receipt=v)["state"], "held")
        self.assertEqual(cache.lookup_cached(self.connection, self.request)["reasons"], ["no_qualified_variant"])

    def test_poisoned_bytes_request_and_duplicate_json_keys_fail_closed(self):
        for poison in ["response", "request", "duplicate"]:
            with self.subTest(poison=poison):
                self.connection.execute(f"DELETE FROM {cache.TABLE}"); self.store()
                column = "request_json" if poison == "request" else "response_json"
                self.connection.execute(f"UPDATE {cache.TABLE} SET {column}=?", ('{"x":1,"x":2}' if poison == "duplicate" else '{}',))
                self.assertEqual(cache.lookup_cached(self.connection, self.request)["state"], "held")

    def test_caller_transaction_not_committed(self):
        self.connection.commit(); self.connection.execute("BEGIN")
        self.store(); self.connection.rollback()
        self.assertEqual(cache.lookup_cached(self.connection, self.request)["state"], "miss")

    def test_lookup_never_initializes_missing_cache(self):
        other = sqlite3.connect(":memory:")
        try:
            self.assertEqual(cache.lookup_cached(other, self.request)["state"], "miss")
            self.assertEqual(other.execute("SELECT count(*) FROM sqlite_master").fetchone()[0], 0)
        finally: other.close()

    def test_nonfinite_size_depth_and_duplicate_ids_rejected(self):
        for value in [float("nan"), "x" * (cache.MAX_BYTES + 1)]:
            with self.assertRaises(cache.CacheError): cache.canonical_bytes(value)
        nested = None
        for _ in range(35): nested = [nested]
        with self.assertRaises(cache.CacheError): cache.canonical_bytes(nested)
        q = copy.deepcopy(self.request); q["inputContent"]["citations"] *= 2
        q["inputContentSHA256"] = cache.content_digest(q["inputContent"])
        self.assertEqual(cache.qualify_request(q), ["duplicate_citation_id"])

    def test_variant_limit_is_bounded(self):
        key = cache.request_key(self.request)
        self.connection.executemany(f"INSERT INTO {cache.TABLE} VALUES (?,?,?,?,?,?,?)",
                                    [(str(i), key, "unused", "{}", "{}", "{}", "held") for i in range(cache.MAX_VARIANTS + 1)])
        self.assertEqual(cache.lookup_cached(self.connection, self.request)["reasons"], ["variant_limit"])


if __name__ == "__main__":
    unittest.main()
