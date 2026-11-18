"""No corpus, household records, external services, persistence or inferred safety."""
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from offmenu.refresh.canonical_food_profile import (PUBLIC, PUBLIC_SCHEMA, aggregate, amount, convert,
    exact, fingerprint, origin_key, source_witness, validate_assertion)
from offmenu.refresh.private_dietary_plan import PRIVATE, PRIVATE_SCHEMA, evaluate_plan, select_plan

H="a"*64
M="b"*64
N="urn:fixture:nutrient:sodium"
I="urn:fixture:ingredient:peanut"
A="urn:fixture:attribute:whole-grain"
NOW=datetime(2026,1,2,tzinfo=timezone.utc)
D1,D2="2026-01-02","2026-01-03"


def observation(i="1",n="300",unit="mg"):
    a={"profileVersion":PUBLIC,"assertionId":"urn:fixture:assert:"+i,
        "subjectId":"urn:fixture:sample-group:1","propertyId":N,"fieldPointer":"/nutrients/amount",
        "context":{"measureId":N,"nutrientForm":"total sodium","issuer":"fixture panel",
                   "jurisdiction":"NZ","population":"adult-test","ageBand":"20-40","sex":"all",
                   "lifeStage":"adult","edition":"fixture-2025","referenceType":"measured",
                   "period":"one assay","basis":"100 g edible portion","foodState":"raw",
                   "measurementMethod":"fixture-A1","effectiveFrom":"2025-01-01","effectiveThrough":"2026-12-31"},
        "measurement":{"magnitude":n,"unit":unit,"originalLexeme":n+" "+unit},
        "origins":[{"citationId":"urn:fixture:cite:"+i,"sourceId":"p"+i,"releaseId":"rel1","sourceRecordId":"000"+i,
                    "sourceField":"/n/0","upstreamOccurrenceId":"native-"+i,"upstreamUrl":"https://publisher.example/item/"+i,
                    "assetSha256":H,"sourceFieldSha256":M,"license":"fixture terms","attribution":"fixture"}]}
    keys=["/subjectId","/propertyId","/fieldPointer"]+["/context/"+k for k in a["context"]]+[
        "/measurement/"+k for k in a["measurement"]]
    a["fieldOrigins"]={k:{"kind":"source","citationIds":[a["origins"][0]["citationId"]]} for k in keys}
    return a


def reg(*obs):
    out={}
    for a in obs:
        for o in a["origins"]:
            k=origin_key(o)
            item=out.setdefault(k,{"witnesses":set(),"upstreamUrl":o["upstreamUrl"],"originHosts":{"publisher.example"},
                                   "allowedPurposes":{"reference","aggregate:median:"+H,"aggregate:unweighted-mean:"+H}})
            item["witnesses"].add(source_witness(a,o))
    return out


def rule(rid,kind,target,period="per-meal",severity="hard",**extra):
    if kind.startswith(("require-","exclude-")):
        extra.setdefault("quantifier","any-item" if kind=="require-ingredient" else "every-item")
    return dict(ruleId=rid,kind=kind,targetId=target,period=period,severity=severity,**{"from":D1,"through":D2},**extra)


def profile(rules,member="one"):
    return dict(profileVersion=PRIVATE,accountId="acct",householdId="hh",memberId=member,consentId="consent-"+member,
                profileRevision="rev1",purpose="private-menu-plan",zone="Pacific/Auckland",rules=rules)


def plan(id="plan",variant="v1",days=(D1,D2)):
    return dict(planId=id,zone="Pacific/Auckland",days=list(days),completeDays=list(days),
                entries=[dict(entryId=f"e{k}",day=d,mealId="lunch",variantId=variant,revision="a",servings="1")
                         for k,d in enumerate(days)])


def auth(p,*plans):
    return {**{k:p[k] for k in ("accountId","memberId","householdId","profileRevision","consentId","purpose","zone")},
            "planPins":{c["planId"]:fingerprint(c) for c in plans},"profileSha256":fingerprint(p),
            "sessionGeneration":"S2","activeSessionGeneration":"S2","authorized":True,"withdrawn":False,
            "expiresAt":NOW+timedelta(hours=1)}


def variants():
    def v(k,state,attr):
        return dict(variantId=k,revision="a",evidence=H,ingredients={I:{"state":state,"evidence":M}},
                    attributes={A:{"state":attr,"evidence":M}},
                    nutrients={N:{"magnitude":"0.6","unit":"g","basis":"per-recipe","evidence":H}},
                    yieldServings="2",yieldEvidence=M)
    return {(x,"a"):v(x,s,a) for x,s,a in (("v1","absent","present"),("v2","present","absent"),("v3","unknown","unknown"))}


def run(p,c,*,facts=None,access=None):
    return evaluate_plan(p,c,authorization=access if access is not None else auth(p,c),now=NOW,
                         variants=variants() if facts is None else facts)


class CanonicalTest(unittest.TestCase):
    def test_schema_mirrors_and_private_public_separation(self):
        root=Path(__file__).resolve().parents[1]/"contracts/schemas"
        for file,schema in (("canonical-food-assertion-profile-v1",PUBLIC_SCHEMA),
                            ("private-dietary-planning-profile-v1",PRIVATE_SCHEMA)):
            self.assertEqual(json.loads((root/(file+".schema.json")).read_text()),schema)
            Draft202012Validator.check_schema(schema)
        self.assertFalse(Draft202012Validator(PUBLIC_SCHEMA).is_valid(profile([])))
        self.assertFalse(Draft202012Validator(PRIVATE_SCHEMA).is_valid(observation()))
        a=observation();a["memberId"]="no";self.assertFalse(Draft202012Validator(PUBLIC_SCHEMA).is_valid(a))

    def test_multiple_origins_bound_to_exact_value_and_grant(self):
        a=observation();a["origins"].append(observation("2")["origins"][0])
        a["fieldOrigins"]["/measurement/magnitude"]["citationIds"].append(a["origins"][1]["citationId"])
        catalog=reg(a)
        self.assertEqual(validate_assertion(a,registry=catalog),a)
        changed=deepcopy(a);changed["measurement"]["magnitude"]="301"
        with self.assertRaisesRegex(ValueError,"permission"):validate_assertion(changed,registry=catalog)
        catalog[origin_key(a["origins"][1])]["allowedPurposes"]=set()
        with self.assertRaisesRegex(ValueError,"permission"):validate_assertion(a,registry=catalog)

    def test_each_scalar_has_exact_eligible_source_or_qualified_transform(self):
        for fn in (
            lambda a:a["fieldOrigins"].pop("/context/nutrientForm"),
            lambda a:a["fieldOrigins"]["/measurement/magnitude"].update(citationIds=["unknown"]),
            lambda a:a["fieldOrigins"].update({"/invented":{"kind":"source","citationIds":["bad"]}}),
        ):
            a=observation();fn(a)
            with self.assertRaises(ValueError):validate_assertion(a,registry=reg(a))
        a=observation();f=a["fieldOrigins"]["/measurement/unit"]
        f.update(kind="derived",policySha256=M,methodId="urn:fixture:method:unit-code")
        with self.assertRaisesRegex(ValueError,"transformation"):validate_assertion(a,registry=reg(a))
        self.assertEqual(validate_assertion(a,registry=reg(a),trusted_transform_pins={M}),a)

    def test_original_upstream_only_never_mirror_or_credentials(self):
        for url in ("https://offmenu.example/hosted-original","http://publisher.example/file",
                    "https://user:pass@publisher.example/file","https://publisher.example/file?access_token=redacted"):
            a=observation();a["origins"][0]["upstreamUrl"]=url
            with self.assertRaises(ValueError):validate_assertion(a,registry=reg(a))

    def test_exact_aggregation_retains_sources_conversion_and_prevents_double_vote(self):
        rows=[observation("a","2","g"),observation("b","300","mg"),observation("c","400","mg")]
        median=aggregate(rows,registry=reg(*rows),method="median",method_pin=H,target_unit="mg")
        mean=aggregate(rows,registry=reg(*rows),method="unweighted-mean",method_pin=H,target_unit="mg")
        self.assertEqual(median["value"],{"numerator":"400","denominator":"1"})
        self.assertEqual(mean["value"],{"numerator":"900","denominator":"1"})
        self.assertEqual(len(mean["inputs"]),3);self.assertEqual(mean["inputs"][0]["factor"],{"numerator":"1000","denominator":"1"})
        self.assertEqual(mean["inputs"][0]["fieldOrigins"][0]["sourceField"],"/n/0")
        rows[1]["origins"][0]["upstreamOccurrenceId"]=rows[0]["origins"][0]["upstreamOccurrenceId"]
        with self.assertRaisesRegex(ValueError,"overlapping"):aggregate(rows,registry=reg(*rows),method="median",method_pin=H,target_unit="mg")

    def test_relabelled_physical_measurement_is_not_an_independent_vote(self):
        first=observation("a");second=deepcopy(first)
        second["assertionId"]="urn:fixture:assert:b"
        second["origins"][0]["upstreamOccurrenceId"]="re-labelled"
        for mirror in (False,True):
            if mirror:second["origins"][0].update(sourceId="mirror",releaseId="another",
                                                 upstreamUrl="https://publisher.example/mirror")
            with self.subTest(mirror=mirror),self.assertRaisesRegex(ValueError,"overlapping-observations"):
                aggregate([first,second],registry=reg(first,second),method="median",method_pin=H,target_unit="mg")

    def test_policy_and_all_comparability_axes_must_match(self):
        a,b=observation(),observation("b")
        for key in b["context"]:
            v=deepcopy(b)
            v["context"][key]={"effectiveFrom":"2025-04-01","effectiveThrough":"2026-11-30","measureId":"urn:fixture:n:other"}.get(key,"other")
            with self.subTest(key=key),self.assertRaises(ValueError):
                aggregate([a,v],registry=reg(a,v),method="median",method_pin=H,target_unit="mg")
        for method,pin in (("sum",H),("median",M)):
            with self.assertRaises(ValueError):aggregate([a,b],registry=reg(a,b),method=method,method_pin=pin,target_unit="mg")
        for x in (a,b):x["context"]["population"]="unknown"
        with self.assertRaisesRegex(ValueError,"unknown-comparability"):aggregate([a,b],registry=reg(a,b),method="median",method_pin=H,target_unit="mg")

    def test_dimension_and_measure_system_are_not_locale_guesses(self):
        self.assertEqual(exact(convert(amount("1"),"[oz_av]","g")),{"numerator":"45359237","denominator":"1600000"})
        self.assertNotEqual(convert(amount("1"),"[foz_us]","mL"),convert(amount("1"),"[foz_br]","mL"))
        for u,v in (("g","mL"),("cup","mL"),("oz","g"),("kcal","mg")):
            with self.assertRaises(ValueError):convert(amount("1"),u,v)
        with self.assertRaises(ValueError):amount("1,234")


class PrivateTest(unittest.TestCase):
    def test_selections_respect_person_and_hard_constraints_before_preferences(self):
        p=profile([rule("no","exclude-ingredient",I),rule("like","require-attribute",A,severity="preference")])
        q=profile([rule("yes","require-ingredient",I)],member="two");a,b=plan("a"),plan("b","v2")
        for owner,want in [(p,"a"),(q,"b")]:
            res=select_plan(owner,[b,a],authorization=auth(owner,a,b),now=NOW,variants=variants())
            self.assertEqual(res["selectedPlanId"],want)
            self.assertTrue(all(x["audience"]["memberId"]==owner["memberId"] for x in res["results"]))
        with self.assertRaisesRegex(ValueError,"private-scope"):run(q,b,access=auth(p,b))
        self.assertEqual(run(p,a)["hardStatus"],"met");self.assertEqual(run(p,b)["hardStatus"],"failed")
        self.assertEqual(run(p,plan("c","v3"))["hardStatus"],"unknown")

    def test_consent_withdrawal_and_plan_membership(self):
        p,c=profile([]),plan();g=auth(p,c)
        for key,value in (("withdrawn",True),("authorized",False),("profileRevision","new"),
                          ("accountId","switched"),("activeSessionGeneration","new"),("expiresAt",NOW)):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"private-scope"):
                run(p,c,access=dict(g,**{key:value}))
        c["entries"].pop()
        with self.assertRaisesRegex(ValueError,"unverified-plan"):run(p,c,access=g)

    def test_unknown_yield_portion_does_not_become_zero(self):
        p=profile([rule("max","nutrient-max",N,period="per-day",unit="mg",magnitude="300",inclusive=True)])
        c=plan();self.assertEqual(run(p,c)["hardStatus"],"met")
        f=variants();f["v1","a"]["yieldServings"]=None
        self.assertEqual(run(p,c,facts=f)["hardStatus"],"unknown")
        f=variants();f["v1","a"]["nutrients"].clear()
        self.assertEqual(run(p,c,facts=f)["hardStatus"],"unknown")
        c["entries"][0]["servings"]=None
        self.assertEqual(run(p,c)["hardStatus"],"unknown")

    def test_period_grouping_and_exclusive_bounds(self):
        p=profile([rule("max","nutrient-max",N,period="per-day",unit="g",magnitude="0.6",inclusive=False)])
        c=plan();c["entries"].append(dict(c["entries"][0],entryId="second",mealId="dinner"))
        out=run(p,c)
        self.assertEqual([(x["day"],x["status"]) for x in out["checks"]],[(D1,"failed"),(D2,"met")])
        p["rules"][0]["period"]="per-meal";self.assertEqual(run(p,c)["hardStatus"],"met")
        p["rules"][0]["period"]="per-serving";c["entries"][0]["servings"]="3"
        self.assertEqual(run(p,c)["hardStatus"],"met")
        p["rules"][0]["period"]="per-day";c["completeDays"]=[D1];self.assertEqual(run(p,c)["checks"][-1]["status"],"unknown")

    def test_incomplete_window_never_selected_even_with_good_visible_serving(self):
        for period in ("per-serving","per-meal","per-day"):
            p=profile([rule("r","exclude-ingredient",I,period=period)]);c=plan(days=(D1,));c["completeDays"]=[]
            self.assertEqual(run(p,c)["hardStatus"],"unknown")
            self.assertIsNone(select_plan(p,[c],authorization=auth(p,c),now=NOW,variants=variants())["selectedPlanId"])
            bad=plan(variant="v2",days=(D1,));bad["completeDays"]=[]
            self.assertEqual(run(p,bad)["hardStatus"],"failed")

    def test_unseen_meal_members_never_prove_insufficiency_or_absence(self):
        c=plan(days=(D1,)); c["completeDays"]=[]
        for requirement in (rule("r","require-ingredient",I,period="per-meal",quantifier="any-item"),
                 rule("r","nutrient-min",N,period="per-meal",unit="mg",magnitude="600",inclusive=True)):
            p=profile([requirement]); out=run(p,c)
            self.assertEqual((out["hardStatus"],out["checks"][0]["status"]),("unknown","unknown"))
            requirement["period"]="per-serving"; self.assertEqual(run(p,c)["hardStatus"],"failed")
            requirement["period"]="per-meal"; c["completeDays"]=[D1]
            self.assertEqual(run(p,c)["hardStatus"],"failed"); c["completeDays"]=[]
        for violation in (rule("r","require-ingredient",I,period="per-meal",quantifier="every-item"),
                          rule("r","nutrient-max",N,period="per-meal",unit="mg",magnitude="299",inclusive=True)):
            self.assertEqual(run(profile([violation]),c)["hardStatus"],"failed")

    def test_coverage_quantifier_is_explicit_not_inferred_from_attribute(self):
        c=plan(days=(D1,));c["entries"].append(dict(c["entries"][0],entryId="another",variantId="v2"))
        p=profile([rule("must","require-attribute",A,quantifier="every-item")])
        self.assertEqual(run(p,c)["hardStatus"],"failed")
        p["rules"][0]["quantifier"]="any-item";self.assertEqual(run(p,c)["hardStatus"],"met")
        del p["rules"][0]["quantifier"]
        with self.assertRaisesRegex(ValueError,"invalid-private-profile"):run(p,c)

    def test_hard_contradictions_or_incomparable_units_block_selection(self):
        p=profile([rule("min","nutrient-min",N,unit="mg",magnitude="300",inclusive=True),
                   rule("max","nutrient-max",N,unit="g",magnitude="0.3",inclusive=False)])
        c=plan()
        self.assertEqual(run(p,c)["hardStatus"],"conflicting")
        self.assertIsNone(select_plan(p,[c],authorization=auth(p,c),now=NOW,variants=variants())["selectedPlanId"])
        p["rules"]=[rule("a","require-ingredient",I),rule("b","exclude-ingredient",I)]
        self.assertEqual(run(p,c)["hardStatus"],"conflicting")
        p["rules"]=[rule("n","nutrient-min",N,unit="mL",magnitude="1",inclusive=True)]
        self.assertEqual(run(p,c)["hardStatus"],"unknown")

    def test_scope_window_stale_recipe_facts_and_soft_only(self):
        p=profile([rule("soft","exclude-ingredient",I,severity="preference")]);c=plan("b","v2")
        self.assertEqual(run(p,c)["hardStatus"],"met")
        self.assertTrue(all(e["status"]=="failed" for e in run(p,c)["checks"]))
        p["rules"][0]["from"]=D2;self.assertEqual([x["day"] for x in run(p,c)["checks"]],[D2])
        c["entries"][0]["revision"]="not-current"
        with self.assertRaisesRegex(ValueError,"unverified-variant"):run(p,c)
        c=plan();c["zone"]="America/New_York"
        with self.assertRaisesRegex(ValueError,"wrong-period-zone"):run(p,c)


if __name__=="__main__":unittest.main()
