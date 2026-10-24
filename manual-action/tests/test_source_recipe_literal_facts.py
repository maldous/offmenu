"""Generated wrappers around retained exact source excerpts; no real approvals.

Original artifact SHA anchors are provenance, never a recipe admission allowlist.
No corpus files, database, native helpers or retained workflows are executed here.
"""
import ast
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_recipe_literal_facts as m

ORIGINALS = {
    "date": "a82f49435789f844285beb0bf0ff8f1cc88ecb24dd012a9aa7e05807b38c3460",
    "grenadine": "b2ab150cdf417335d38f48f2c19e7347b0cb5bf6de63284cd6e3164bc026f2c6",
    "jam": "01d0e6f276efdc0a3d907ceb4b9afd07f89d4b336c52585c30135b4d134f6c71",
    "cocoyam": "410ac416a410cb1b78ce955058c2585747fa69c1c4e355132c5206c897ced520",
    "eba": "b7157c32649fd3b8001d6aac0f13354c20e1abbee361d4a5aebea7db09e9b933",
    "hlib": "e8b151b77f00bb16b94ba9e38f933bc878bd563b13032ea5e54d4c40e8679ef8",
    "affogato": "e6f7e9dc3ac55991466efc10054bb84f8a16890278b7825a568c89fb4ad8dd1f",
}


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def coverage(r):
    return {"literalFactIds": [f["id"] for f in r["literalFacts"]],
            "knownAmountFactIds": [f["id"] for f in r["literalFacts"] if f["amount"]["state"] == "stated"],
            "eventIds": [e["id"] for e in r["sourceEvents"]],
            "contextIds": [e["id"] for e in r["mandatoryContexts"]],
            "relativeGroupMembers": {g["id"]: g["factIds"] for g in r["relativeGroups"]},
            "alternativeGroupBranches": {g["id"]: [b["id"] for b in g["branches"]] for g in r["alternativeGroups"]},
            "explicitActors": {e["id"]: e["actor"]["lexeme"] for e in r["sourceEvents"] if e["actor"]["kind"] == "explicit"}}


def seal(r, *, native="held", native_source=None):
    """TEST ONLY: synthetic independent caller context, never real acceptance."""
    artifacts = {}
    def ref(row):
        raw = json.dumps({"rows": [row]}, ensure_ascii=False) + "\n"
        h = hashlib.sha256(raw.encode()).hexdigest()
        artifacts[h] = raw
        return {"artifactSHA256": h, "pointer": "/rows/0", "rowSHA256": m.canonical_sha256(row)}
    native_receipt = ref({"testOnlyExistingNativeReceipt": True}) if native == "available" else None
    b = {"purpose": m.PURPOSE, "sourceSHA256": r["source"]["rawSHA256"],
         "sourceScope": r["sourceScope"], "recordSHA256": m.canonical_sha256(r),
         "coverage": coverage(r), "citationRights": {c["id"]: {
             "purpose": m.PURPOSE, "visibility": "public", "payloadSHA256": c["payloadSHA256"]} for c in r["citations"]},
         "nativeAvailability": {"status": native, "sourceSHA256": native_source or r["source"]["rawSHA256"],
             "receipt": native_receipt, "reasons": ["retained-shape native capability held"] if native == "held" else []},
         "constraints": {"privateInternalOnly": True, "allocation": False, "metricConversion": False,
                         "actualUse": "unobserved", "originalsAreFixturesNotLiveApprovals": True},
         "authorThreadId": "TEST-AUTHOR", "reviewerThreadId": "TEST-INDEPENDENT",
         "disposition": "active", "conflicts": [], "revoked": False}
    if native is None:
        b.pop("nativeAvailability")
    review = ref(b)
    custody = ref({"review": review, "binding": b, "disposition": "accepted"})
    return m.QualifiedSourceFactContext(b, review, custody, artifacts)


def fixture(kind):
    source = {"id": "fixture:" + kind, "recordId": "TEST-" + kind, "revisionId": 1,
              "ingredients": [], "steps": [], "notes": ["Retained source restrictions remain source-only."],
              "unknownOriginalField": {"retained": True, "notZero": None}}
    if kind in ("date", "grenadine"):
        syrup, qty = ("Date Syrup|date syrup", "7") if kind == "date" else ("Grenadine|grenadine", "5")
        source["ingredients"] = ["* 1 volume [[Cookbook:" + syrup + "]]",
                                 "* " + qty + " volumes cold [[Cookbook:Carbonated Water|carbonated water]]"]
        source["notes"][0] = "* Use water from a carbonating machine or a brand of pure carbonated water such as Polar Original Sparkling Water, Great Value Seltzer Water, or Signature Select Seltzer Water. Do not use a brand of mineral water such as Perrier, San Pellegrino, or Mineragua because the added minerals will ruin the taste. Avoid flavored sparkling water such as La Croix or Spindrift because the preexisting fruit flavors will ruin the drink."
        source["steps"] = (["# Combine syrup and carbonated water until evenly mixed.", "# Serve cold."]
                           if kind == "date" else ["# Combine grenadine and carbonated water until well-mixed."])
    elif kind == "jam":
        source["ingredients"] = ["*2 slices of [[Cookbook:Bread|bread]]", "*Some [[Cookbook:Jam|jam]] (any flavor)"]
        source["steps"] = ["#Spread the jam onto the first slice of bread.",
                           "#Put the second slice of bread on top of the side of bread you have put the jam on."]
    elif kind == "cocoyam":
        source["ingredients"] = ["*[[Cookbook:Water|Water]]"]
        source["steps"] = ["#Cut the cocoyam into medium-sized chunks, and cook in a pot of water until tender. Drain the cocoyam.",
                           "#Combine the cassava flour with ½ cup water to make a mouldable ball."]
    elif kind == "eba":
        source["ingredients"] = ["*1 [[Cookbook:Liter|liter]] [[Cookbook:Water|water]]",
            "*2 [[Cookbook:Units of measurement#Nigeria|milk tins]] of processed [[Cookbook:Cassava|cassava]] flakes (garri)"]
        source["steps"] = ["#Gradually stir in the cassava flour, and cook until it forms a smooth [[Cookbook:Dough|dough]]."]
    elif kind == "hlib":
        source["ingredients"] = ["* 250 [[Cookbook:Milliliter|ml]] camel [[Cookbook:Milk|milk]]",
                                 "* 7 plump, ripe [[Cookbook:Date|dates]]"]
        source["steps"] = ["# [[Cookbook:Boiling|Boil]] the dates with water and sugar for a few minutes until you feel the dates are well-cooked.",
                           "# Turn off the heat, [[Cookbook:Puréeing|blend]] the date mixture, and [[Cookbook:Straining|strain]] it as well as possible."]
        source["notes"].append("* Alternatively, you can [[Cookbook:Simmering|simmer]] the dates directly in the milk over low heat until the colour of the milk changes to a nice brown shade before straining.")
    elif kind == "affogato":
        source["ingredients"] = ["* 1 scoop [[Cookbook:Gelato|gelato]], typically [[Cookbook:Vanilla|vanilla]]",
                                 "* 1–2 shots [[Cookbook:Coffee#Espresso|espresso]], or one long pull shot"]
        source["steps"] = ["# Either pour espresso over gelato and serve, or serve them side by side for diner to mix at the table."]
    raw = json.dumps(source, ensure_ascii=False) + "\n"
    raw_sha = hashlib.sha256(raw.encode()).hexdigest()
    scope = {"recipeId": source["id"], "recordId": source["recordId"], "revisionId": 1,
             "occurrenceId": "TEST-OCCURRENCE-" + kind, "rawSHA256": raw_sha}
    citation_payload = {"scope": {"visibility": "public"}, "license": "CC BY-SA 4.0",
                        "attribution": "Wikibooks contributors; generated wrapper of retained excerpts"}
    r = {"purpose": m.PURPOSE, "sourceScope": scope,
         "source": {"rawText": raw, "rawSHA256": raw_sha, "artifactReference": "fixture://" + kind,
                    "scopePointers": {"recipeId": "/id", "recordId": "/recordId", "revisionId": "/revisionId"},
                    "retainedOriginalSHA256": ORIGINALS[kind], "generatedWrapper": True},
         "citations": [{"id": "c", "state": "verified", "payload": citation_payload,
                        "payloadSHA256": m.canonical_sha256(citation_payload)}],
         "literalFacts": [], "sourceEvents": [], "relativeGroups": [], "alternativeGroups": [],
         "mandatoryContexts": [], "futureUnknownField": {"preserve": [None, False, 0]}}
    def span(pointer, text=None):
        value = source
        for part in pointer[1:].split("/"):
            value = value[int(part)] if type(value) is list else value[part]
        text = value if text is None else text
        start = value.index(text)
        return {"pointer": pointer, "start": start, "end": start + len(text), "text": text, "offset_unit": "unicode_codepoint"}
    def fact(id_, pointer, value, unit, form="integer", qualifiers=(), binding_kind="ingredient-total"):
        q = {"id": id_, "binding": {"kind": binding_kind, "sourceId": "TEST-LINE-" + id_},
             "sourceSpans": [span(pointer)], "citationIds": ["c"],
             "amount": {"state": "stated", "form": form, "lexeme": value, "span": span(pointer, value)},
             "unit": {"lexeme": unit, "span": span(pointer, unit)},
             "qualifiers": [span(pointer, q) for q in qualifiers], "membership": None}
        r["literalFacts"].append(q)
        return q
    def event(id_, pointer, verb, clause=None, actor=None):
        e = {"id": id_, "sourceSpans": [span(pointer, clause)], "citationIds": ["c"],
             "verb": {"lexeme": verb, "span": span(pointer, verb)},
             "actor": {"kind": "explicit", "lexeme": actor, "span": span(pointer, actor)} if actor else {"kind": "unspecified"},
             "membership": None}
        r["sourceEvents"].append(e)
        return e
    def group(id_, group_kind, pointer, branches):
        g = {"id": id_, "kind": group_kind, "sourceScope": scope, "sourceSpans": [span(pointer)],
             "citationIds": ["c"], "selection": None, "branches": []}
        for bid, clause, fact_ids, event_ids in branches:
            g["branches"].append({"id": bid, "sourceSpans": [span(pointer, clause)], "citationIds": ["c"],
                                  "factIds": fact_ids, "eventIds": event_ids})
            for row in r["literalFacts"] + r["sourceEvents"]:
                if row["id"] in fact_ids + event_ids:
                    row["membership"] = {"groupId": id_, "branchId": bid}
        r["alternativeGroups"].append(g)
    if kind in ("date", "grenadine"):
        fact("part1", "/ingredients/0", "1", "volume", "relative-part")
        fact("part2", "/ingredients/1", "7" if kind == "date" else "5", "volumes", "relative-part", ["cold"])
        r["relativeGroups"] = [{"id": "ratio", "kind": "relative-volume", "sourceScope": scope,
                                "sourceSpans": [span("/ingredients/0"), span("/ingredients/1")],
                                "citationIds": ["c"], "factIds": ["part1", "part2"]}]
        event("combine", "/steps/0", "Combine")
        if kind == "date": event("serve-cold", "/steps/1", "Serve")
    elif kind == "jam":
        q = fact("bread", "/ingredients/0", "2", "slices")
        q["useMentions"] = [{"kind": "ordinal", "lexeme": word, "span": span("/steps/" + str(i), word)}
                            for i, word in enumerate(("first", "second"))]
    elif kind == "cocoyam":
        fact("method-water", "/steps/1", "½", "cup", "fraction", binding_kind="method-use")
        r["mandatoryContexts"].append({"id": "unknown-boiling-water", "sourceSpans": [span("/steps/0")], "citationIds": ["c"]})
    elif kind == "eba":
        fact("water", "/ingredients/0", "1", "liter")
        fact("garri", "/ingredients/1", "2", "milk tins")
        r["mandatoryContexts"].append({"id": "garri-flour-discrepancy", "sourceSpans": [span("/steps/0")], "citationIds": ["c"]})
    elif kind == "hlib":
        fact("milk", "/ingredients/0", "250", "ml", qualifiers=["camel"])
        fact("dates", "/ingredients/1", "7", "dates", qualifiers=["plump, ripe"])
        event("boil", "/steps/0", "Boil")
        event("off", "/steps/1", "Turn off")
        event("simmer", "/notes/1", "simmer")
        g = {"id": "method", "kind": "method-choice", "sourceScope": scope,
             "sourceSpans": [span("/steps/0"), span("/steps/1"), span("/notes/1")], "citationIds": ["c"], "selection": None,
             "branches": [{"id": "primary", "sourceSpans": [span("/steps/0"), span("/steps/1")], "citationIds": ["c"], "factIds": [], "eventIds": ["boil", "off"]},
                          {"id": "alternative", "sourceSpans": [span("/notes/1")], "citationIds": ["c"], "factIds": [], "eventIds": ["simmer"]}]}
        r["alternativeGroups"].append(g)
        for e in r["sourceEvents"]:
            e["membership"] = {"groupId": "method", "branchId": "alternative" if e["id"] == "simmer" else "primary"}
    elif kind == "affogato":
        fact("gelato", "/ingredients/0", "1", "scoop", qualifiers=["typically"])
        fact("shots", "/ingredients/1", "1–2", "shots", "range")
        fact("long-pull", "/ingredients/1", "one", "long pull shot", "word-count")
        group("coffee-amount", "quantity-choice", "/ingredients/1",
              [("shots", "1–2 shots [[Cookbook:Coffee#Espresso|espresso]]", ["shots"], []),
               ("long-pull", "one long pull shot", ["long-pull"], [])])
        event("pour", "/steps/0", "pour", "pour espresso over gelato")
        event("serve-pour", "/steps/0", "serve", "serve")
        # Select the second serve occurrence explicitly, never replace source text.
        side = event("serve-side", "/steps/0", "serve", "serve them side by side")
        side["verb"]["span"] = {**side["verb"]["span"], "start": side["sourceSpans"][0]["start"],
                                   "end": side["sourceSpans"][0]["start"] + len("serve")}
        event("diner-mix", "/steps/0", "mix", "diner to mix at the table", actor="diner")
        group("service", "service-choice", "/steps/0",
              [("pour-over", "pour espresso over gelato and serve", [], ["pour", "serve-pour"]),
               ("side-by-side", "serve them side by side for diner to mix at the table", [], ["serve-side", "diner-mix"])])
    r["mandatoryContexts"].append({"id": "notes", "sourceSpans": [span("/notes/0")], "citationIds": ["c"]})
    return r, seal(r)


def boundary_fixture(text, value, unit, form="integer"):
    """Wholly generated expression/token fixture, not a retained recipe."""
    raw = json.dumps({"id": "TEST-LEXICAL-BOUNDARY", "line": text}, ensure_ascii=False) + "\n"
    h = hashlib.sha256(raw.encode()).hexdigest()
    def span(word):
        start = text.index(word)
        return {"pointer": "/line", "start": start, "end": start + len(word),
                "text": word, "offset_unit": "unicode_codepoint"}
    payload = {"scope": {"visibility": "public"}, "license": "Generated",
               "attribution": "Test-only lexical boundary control"}
    r = {"purpose": m.PURPOSE,
         "sourceScope": {"recipeId": "TEST-LEXICAL-BOUNDARY", "occurrenceId": "TEST-OCCURRENCE", "rawSHA256": h},
         "source": {"rawText": raw, "rawSHA256": h, "artifactReference": "generated://boundary",
                    "scopePointers": {"recipeId": "/id"}},
         "citations": [{"id": "c", "state": "verified", "payload": payload, "payloadSHA256": m.canonical_sha256(payload)}],
         "literalFacts": [{"id": "quantity", "binding": {"kind": "ingredient-total", "sourceId": "TEST-LINE"},
                           "sourceSpans": [span(text)], "citationIds": ["c"],
                           "amount": {"state": "stated", "form": form, "lexeme": value, "span": span(value)},
                           "unit": {"lexeme": unit, "span": span(unit)}, "qualifiers": [], "membership": None}],
         "sourceEvents": [], "relativeGroups": [], "alternativeGroups": [], "mandatoryContexts": []}
    return r, seal(r, native=None)


class LiteralFactsTests(unittest.TestCase):
    def ok(self, r, ctx):
        before = copy.deepcopy(r)
        context_before = copy.deepcopy(ctx)
        out = m.build_source_recipe_literal_facts(r, qualified_context=ctx)
        self.assertEqual(out["outcome"], "source-facts-qualified", out)
        self.assertEqual(r, before)
        self.assertEqual(ctx, context_before)
        self.assertEqual(out["literalFacts"], r["literalFacts"])
        self.assertEqual(out["alternativeGroups"], r["alternativeGroups"])
        self.assertEqual(out["sourceEvents"], r["sourceEvents"])
        self.assertEqual(out["mandatoryContexts"], r["mandatoryContexts"])
        self.assertEqual(out["executableSuitability"], {"status": "not-qualified", "actualSelection": "unobserved", "currentStateFit": None})
        self.assertEqual(out["nutritionCompleteness"], {"status": "not-qualified", "actualRecipeComposition": None,
                                                      "globalProductFitAcceptance": False, "metricNormalization": None})
        return out

    def rejected(self, r, ctx, reason=None):
        out = m.build_source_recipe_literal_facts(r, qualified_context=ctx)
        self.assertEqual(out["outcome"], "rejected", out)
        self.assertNotIn("literalFacts", out)
        if reason: self.assertIn(reason, out["reason"])
        return out

    def test_01_date_ordered_one_to_seven(self):
        r, c = fixture("date"); out = self.ok(r, c)
        self.assertEqual([f["amount"]["lexeme"] for f in out["literalFacts"]], ["1", "7"])

    def test_02_grenadine_ordered_one_to_five(self):
        r, c = fixture("grenadine"); out = self.ok(r, c)
        self.assertEqual([f["amount"]["lexeme"] for f in out["literalFacts"]], ["1", "5"])

    def test_03_jam_two_slices_and_ordinal_uses(self):
        r, c = fixture("jam"); out = self.ok(r, c)
        self.assertEqual(out["literalFacts"][0]["amount"]["lexeme"], "2")
        self.assertEqual([u["lexeme"] for u in out["literalFacts"][0]["useMentions"]], ["first", "second"])

    def test_04_cocoyam_fraction_is_method_use(self):
        r, c = fixture("cocoyam"); out = self.ok(r, c)
        self.assertEqual(out["literalFacts"][0]["binding"]["kind"], "method-use")
        self.assertEqual(out["literalFacts"][0]["amount"]["lexeme"], "½")

    def test_05_eba_tins_and_discrepancy(self):
        r, c = fixture("eba"); out = self.ok(r, c)
        self.assertEqual(out["literalFacts"][1]["unit"]["lexeme"], "milk tins")

    def test_06_hlib_dates_qualifiers_and_off(self):
        r, c = fixture("hlib"); out = self.ok(r, c)
        self.assertEqual(out["literalFacts"][1]["qualifiers"][0]["text"], "plump, ripe")
        self.assertEqual(out["sourceEvents"][1]["verb"]["lexeme"], "Turn off")

    def test_07_affogato_scoop_range_or_word_count(self):
        r, c = fixture("affogato"); out = self.ok(r, c)
        self.assertEqual([f["amount"]["lexeme"] for f in out["literalFacts"]], ["1", "1–2", "one"])

    def test_08_affogato_service_order_and_diner(self):
        r, c = fixture("affogato"); out = self.ok(r, c)
        service = out["alternativeGroups"][1]
        self.assertIsNone(service["selection"])
        self.assertEqual(service["branches"][0]["eventIds"], ["pour", "serve-pour"])
        self.assertEqual(out["sourceEvents"][-1]["actor"]["lexeme"], "diner")

    def test_09_hlib_multisource_alternative_stays_separate(self):
        r, c = fixture("hlib"); out = self.ok(r, c)
        self.assertEqual(out["alternativeGroups"][0]["branches"][1]["eventIds"], ["simmer"])
        self.assertIsNone(out["alternativeGroups"][0]["selection"])

    def test_10_partial_range_fraction_and_unit_loss_fail(self):
        r, c = fixture("affogato")
        fact = r["literalFacts"][1]
        fact["amount"].update(form="integer", lexeme="2")
        fact["amount"]["span"].update(start=fact["amount"]["span"]["end"] - 1, text="2")
        self.rejected(r, seal(r), "partial numeric prefix")
        r, c = fixture("cocoyam"); r["literalFacts"][0]["amount"]["lexeme"] = "0.5"
        self.rejected(r, seal(r), "amount source binding")
        r, c = fixture("eba"); r["literalFacts"][1]["unit"]["lexeme"] = "tins"
        self.rejected(r, seal(r), "unit source binding")
        for raw, start in (("* 2*4 eggs", 4), ("* 4*2 eggs", 2)):
            with self.assertRaisesRegex(m.SourceFactError, "multiplication"):
                m._numeric_boundary({"pointer": "/x", "start": start, "end": start + 1,
                                     "text": "4", "offset_unit": "unicode_codepoint"}, {"x": raw})

    def test_11_source_identity_span_and_citation_purpose(self):
        r, c = fixture("date"); r["source"]["rawText"] += " "
        self.rejected(r, seal(r), "raw source hash")
        r, c = fixture("date"); r["sourceScope"]["revisionId"] = 2
        self.rejected(r, seal(r), "identity field")
        r, c = fixture("date"); r["literalFacts"][0]["amount"]["span"]["end"] += 1
        self.rejected(r, seal(r), "span mismatch")
        r, c = fixture("date"); c.binding["citationRights"]["c"]["purpose"] = "wrong-purpose"
        self.rejected(r, c)

    def test_12_full_pair_and_branch_closure(self):
        r, c = fixture("date"); r["relativeGroups"][0]["factIds"].reverse()
        self.rejected(r, seal(r), "source order")
        r, c = fixture("date"); r["relativeGroups"][0]["factIds"].pop()
        self.rejected(r, seal(r), "ID list")
        r, c = fixture("date"); r["literalFacts"].reverse(); r["relativeGroups"][0]["factIds"].reverse()
        self.rejected(r, seal(r), "source order")
        r, c = fixture("affogato"); r["alternativeGroups"][1]["branches"].pop()
        self.rejected(r, seal(r), "complete alternative")

    def test_13_no_forced_selection_actor_change_or_flattened_order(self):
        r, c = fixture("affogato"); r["alternativeGroups"][1]["selection"] = "pour-over"
        self.rejected(r, seal(r), "unselected")
        r, c = fixture("affogato"); r["sourceEvents"][-1]["actor"]["lexeme"] = "operator"
        self.rejected(r, seal(r), "actor binding")
        r, c = fixture("affogato"); r["alternativeGroups"][1]["branches"][0]["eventIds"].reverse()
        self.rejected(r, seal(r), "source order")
        r, c = fixture("hlib"); r["alternativeGroups"][0]["branches"][0]["eventIds"].reverse()
        self.rejected(r, seal(r), "source order")
        r, c = fixture("date"); r["sourceEvents"].reverse()
        self.rejected(r, seal(r), "event source order")

    def test_14_known_amount_is_not_null_or_zero(self):
        r, c = fixture("jam"); r["literalFacts"][0]["amount"] = None
        self.rejected(r, c)
        r, c = fixture("jam"); r["literalFacts"][0]["amount"] = {"state": "not-stated"}
        # Correct raw review hash blocks source-driven downgrade of known quantity.
        self.rejected(r, c, "unreviewed record")
        r, c = fixture("jam"); r["literalFacts"][0]["amount"]["state"] = "not-stated"
        self.rejected(r, seal(r), "cannot hide a known literal")
        r, c = fixture("jam")
        r["literalFacts"][0]["amount"] = {"state": "not-stated"}
        # Explicit unknown amount remains a tagged, nonzero assertion only in a
        # separately reviewed test record; it is not derived from the known2.
        r["literalFacts"][0].pop("unit")
        r["literalFacts"][0]["id"] = "TEST-UNKNOWN-FACT"
        r["literalFacts"][0]["sourceSpans"] = [r["mandatoryContexts"][0]["sourceSpans"][0]]
        self.ok(r, seal(r))

    def test_15_four_statuses_are_independent_and_unknown_fields_survive(self):
        r, c = fixture("eba"); out = self.ok(r, c)
        self.assertEqual(out["sourceFactQualification"]["status"], "qualified")
        self.assertEqual(out["normalizedInstructionAvailability"]["status"], "held")
        self.assertEqual(out["uninterpretedRecordFields"], {"futureUnknownField": r["futureUnknownField"]})
        self.assertEqual(out["sourceReference"]["rawSHA256"], r["source"]["rawSHA256"])
        r, c = fixture("jam"); r["literalFacts"][0]["futureFactField"] = {"opaque": 0}
        self.ok(r, seal(r))
        self.ok(r, seal(r, native="available"))
        self.rejected(r, seal(r, native="available", native_source="0" * 64), "native availability source")
        r, c = fixture("jam")
        self.ok(r, seal(r, native="not-supplied"))
        out = self.ok(r, seal(r, native=None))
        self.assertEqual(out["normalizedInstructionAvailability"]["status"], "not-supplied")

    def test_16_trusted_context_is_not_stored_json_or_prose(self):
        r, c = fixture("date")
        self.rejected(r, {"binding": c.binding, "accepted": True}, "caller-owned")
        r["reviewer"] = "independent"; r["accepted"] = True
        self.rejected(r, c, "unreviewed record")
        r, c = fixture("date"); c.artifacts[c.review["artifactSHA256"]] += " "
        self.rejected(r, c, "raw review hash")
        r, c = fixture("date"); c.review["pointer"] = "/rows/00"
        self.rejected(r, c)
        with self.assertRaises(m.InvalidInput): m.parse_json('{"x":1,"x":2}')

    def test_17_event_shaped_higher_grants_cannot_promote(self):
        r, c = fixture("affogato")
        r["event"] = {"actualUseApproved": True, "nativeAvailability": "available", "nutrition": 99}
        out = self.ok(r, seal(r))
        self.assertEqual(out["uninterpretedRecordFields"]["event"], r["event"])
        self.assertEqual(out["normalizedInstructionAvailability"]["status"], "held")

    def test_18_limits_atomic_reject_and_purity(self):
        for kind in ("facts", "events", "groups", "branches", "citations", "input", "output", "nodes", "depth", "nan", "amount"):
            with self.subTest(kind=kind):
                r, c = fixture("affogato")
                if kind == "facts": r["literalFacts"] *= 44
                elif kind == "events": r["sourceEvents"] *= 33
                elif kind == "groups": r["alternativeGroups"] *= 9
                elif kind == "branches": r["alternativeGroups"][0]["branches"] *= 9
                elif kind == "citations": r["citations"] *= 129
                elif kind in ("input", "output"): r["large"] = "x" * (524289 if kind == "input" else 263000)
                elif kind == "nodes": r["large"] = [None] * 100001
                elif kind == "depth":
                    value = 0
                    for _ in range(33): value = [value]
                    r["large"] = value
                elif kind == "nan": r["large"] = float("nan")
                elif kind == "amount": r["literalFacts"][0]["amount"]["lexeme"] = "1" * 129
                try: ctx = seal(r)
                except (m.InvalidInput, TypeError): ctx = c
                self.rejected(r, ctx)
        r, c = fixture("date")
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            self.ok(r, c)
        tree = ast.parse(Path(m.__file__).read_text())
        forbidden = {"open", "exec", "eval", "assess", "_assess", "_closure", "connect", "normalize_recipe"}
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                name = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else None
                self.assertNotIn(name, forbidden)

    def test_19_reject_ascii_products_and_exponent_fragments(self):
        for text, value in [
            ("* 2 x 3 cups grains", "2"), ("* 2 x 3 cups grains", "3"),
            ("* 2X3 cups grains", "2"), ("* 2x3 cups grains", "3"),
            ("* (2) x (3) cups grains", "2"), ("* (2) x (3) cups grains", "3"),
            ("* '2' x '3' cups grains", "2"), ("* '2' x '3' cups grains", "3"),
            ("* “2” X “3” cups grains", "2"), ("* “2” X “3” cups grains", "3"),
            ("* 1e3 cups grains", "1"), ("* 1e3 cups grains", "3"),
            ("* 1E+3 cups grains", "1"), ("* 1E+3 cups grains", "3"),
            ("* 1e−3 cups grains", "1"), ("* 1e−3 cups grains", "3"),
            ("* 2^3 cups grains", "2"), ("* 2^3 cups grains", "3"),
        ]:
            with self.subTest(text=text, value=value):
                r, c = boundary_fixture(text, value, "cups")
                self.rejected(r, c)
        for text, value, unit, form in [
            ("* 2 cups grains", "2", "cups", "integer"),
            ("* 250ml water", "250", "ml", "integer"),
            ("* 2 xylitol portions", "2", "xylitol", "integer"),
            ("* 2 espresso cups", "2", "espresso cups", "integer"),
            ("* ½ cup water", "½", "cup", "fraction"),
            ("* 1–2 shots coffee", "1–2", "shots", "range"),
        ]:
            with self.subTest(positive=text):
                r, c = boundary_fixture(text, value, unit, form)
                self.ok(r, c)

    def test_20_word_count_unicode_whole_tokens(self):
        for text in ["* stone cup holder", "* onerous cup holder", "* someone cup holder",
                     "* éone cup holder", "* oneé cup holder", "* e\u0301one cup holder",
                     "* one\u0301 cup holder", "* one_name cup holder", "* name_one cup holder",
                     "* one\u200dname cup holder", "* name\u200cone cup holder",
                     "* one2 cup holder", "* 2one cup holder", "* one's cup holder"]:
            with self.subTest(negative=text):
                r, c = boundary_fixture(text, "one", "cup", "word-count")
                self.rejected(r, c)
        for text, value in [("* one cup water", "one"), ("* ONE cup water", "ONE"),
                            ("* (one) cup water", "one"), ("* ‘one’ cup water", "one"),
                            ("* 'one' cup water", "one")]:
            with self.subTest(positive=text):
                r, c = boundary_fixture(text, value, "cup", "word-count")
                self.ok(r, c)

    def test_21_signed_wrapped_operand_prefixes_are_not_quantities(self):
        operands = ["-3", "+3", "(-3)", "(+3)", "(−3)", "[−3]", "{ +3 }",
                    "“(-3)”", "-(3)", "( - (3))", '"+3"', "((+ (−3)))"]
        for operator in ("x", "X", "e", "E"):
            for operand in operands:
                value = "2" if operator in "xX" else "1"
                text = "* " + value + operator + operand + " cups grains"
                with self.subTest(operator=operator, operand=operand):
                    r, c = boundary_fixture(text, value, "cups")
                    self.rejected(r, c)
        text = "* 1e" + "(" * 129 + "-3" + ")" * 129 + " cups grains"
        r, c = boundary_fixture(text, "1", "cups")
        self.rejected(r, c)


    def test_22_expression_operands_share_boundaries_and_preserve_bullets(self):
        # Both operands and the full unsupported expression must stay unqualified.
        for operator in ("*", "x", "X", "e", "E"):
            for left, right, spacing in [
                ("2", "3", ""), ("(2)", "(3)", " "),
                ("“2”", '"3"', ""), ("2", "-3", " "),
                ("(-2)", "(+3)", " "), ("[+2]", "{−3}", ""),
                ("((−(2)))", "((+ (−3)))", " "),
            ]:
                expression = left + spacing + operator + spacing + right
                text = "* " + expression + " cups grains"
                for value in ("2", "3", expression):
                    with self.subTest(operator=operator, expression=expression, selected=value):
                        r, c = boundary_fixture(text, value, "cups")
                        self.rejected(r, c)
        # Existing immediate operator guards also reject clipped/full expressions.
        for operator in ("/", "⁄", "∕", "+", "−", "×", "÷", "^", "–"):
            expression = "(2) " + operator + " (3)"
            for value in ("2", "3", expression):
                with self.subTest(operator=operator, selected=value):
                    r, c = boundary_fixture("* " + expression + " cups grains", value, "cups")
                    self.rejected(r, c)
        for operator in ("*", "x", "X", "e", "E"):
            for text, value in [("* 2" + operator + "(" * 129 + "3 cups grains", "2"),
                                ("* 2" + ")" * 129 + operator + "3 cups grains", "3")]:
                with self.subTest(over_budget=text, selected=value):
                    r, c = boundary_fixture(text, value, "cups")
                    self.rejected(r, c)
        for text, value, unit, form in [
            ("* 2 cups grains", "2", "cups", "integer"),
            ("* (2) cups grains", "2", "cups", "integer"),
            ("* ‘2’ cups grains", "2", "cups", "integer"),
            ("* 250ml water", "250", "ml", "integer"),
            ("* 2 xylitol portions", "2", "xylitol", "integer"),
            ("* 2 espresso cups", "2", "espresso cups", "integer"),
            ("* ½ cup water", "½", "cup", "fraction"),
            ("* 1–2 shots coffee", "1–2", "shots", "range"),
        ]:
            with self.subTest(bullet_positive=text):
                r, c = boundary_fixture(text, value, unit, form)
                self.ok(r, c)


if __name__ == "__main__":
    unittest.main()
