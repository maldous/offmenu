"""Private member-owned policy evaluation over reviewed recipe variants.

Pure, offline and limited to synthetic/explicitly authorized input. Never exports
a rule, diagnoses an allergy, changes a profile or treats a guideline as a
user rule. Admission is a trusted application port, not a JSON payload field.
"""
from datetime import date, datetime
from fractions import Fraction
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .canonical_food_profile import (DATE, DIGEST, ID, MAG, TEXT, UNIT, amount, convert, ensure,
                                     fingerprint, matches_digest, obj, seq, validated)

PRIVATE = "offmenu-private-dietary-planning-profile/1"
PERIOD = {"enum":["per-serving","per-meal","per-day"]}
base = {"ruleId":TEXT,"severity":{"enum":["hard","preference"]},"period":PERIOD,"targetId":ID,
        "from":DATE,"through":DATE}
presence = {"oneOf":[obj({**base,"kind":{"enum":["require-ingredient","require-attribute"]},
                                "quantifier":{"enum":["any-item","every-item"]}}),
                      obj({**base,"kind":{"enum":["exclude-ingredient","exclude-attribute"]},
                           "quantifier":{"const":"every-item"}})]}
nutrient = obj({**base,"kind":{"enum":["nutrient-min","nutrient-max"]},"magnitude":MAG,"unit":UNIT,
                "inclusive":{"type":"boolean"}})
PRIVATE_SCHEMA = {"$schema":"https://json-schema.org/draft/2020-12/schema",
    "$id":"urn:offmenu:private-dietary-planning-profile:1",
    "description":"Separate member-controlled menu-planning policy; never public corpus or clinical advice.",
    **obj({"profileVersion":{"const":PRIVATE},"accountId":TEXT,"memberId":TEXT,"householdId":TEXT,
           "profileRevision":TEXT,"consentId":TEXT,"purpose":{"const":"private-menu-plan"},
           "zone":TEXT,"rules":seq({"oneOf":[presence,nutrient]},0,128)})}

# Verified variant facts—not plan suggestions—are supplied by a prior authorized
# public recipe/ingredient decision. An absent mapping is unknown. A negative fact
# means explicitly reviewed absence, never an ingredient not seen in a list.
fact = obj({"state":{"enum":["present","absent","unknown","conflicting"]},"evidence":DIGEST})
measure = obj({"magnitude":MAG,"unit":UNIT,"basis":{"enum":["per-serving","per-recipe"]},"evidence":DIGEST})
def by_key(value):
    return {"type":"object","propertyNames":TEXT,"maxProperties":1024,"additionalProperties":value}
VARIANT_SCHEMA = obj({"variantId":TEXT,"revision":TEXT,"evidence":DIGEST,"ingredients":by_key(fact),
                      "attributes":by_key(fact),"nutrients":by_key(measure),
                      "yieldServings":{"anyOf":[MAG,{"type":"null"}]},
                      "yieldEvidence":{"anyOf":[DIGEST,{"type":"null"}]}})
ENTRY = obj({"entryId":TEXT,"day":DATE,"mealId":TEXT,"variantId":TEXT,"revision":TEXT,
             "servings":{"anyOf":[MAG,{"type":"null"}]}})
PLAN = obj({"planId":TEXT,"zone":TEXT,"days":seq(DATE,1,31),
            "completeDays":seq(DATE,0,31),"entries":seq(ENTRY,0,256)})
SCOPE = ("accountId","memberId","householdId","profileRevision","consentId","purpose","zone")
FAILURE = {"failed","conflicting"}
STATUS = {"met","failed","unknown","conflicting"}


def authorized(profile,auth,now):
    validated(PRIVATE_SCHEMA,profile,"invalid-private-profile")
    ensure(isinstance(auth,dict) and auth.get("authorized") is True and auth.get("withdrawn") is False
           and auth.get("sessionGeneration")==auth.get("activeSessionGeneration")
           and isinstance(auth.get("sessionGeneration"),str) and auth["sessionGeneration"]
           and all(auth.get(k)==profile[k] for k in SCOPE) and auth.get("profileSha256")==fingerprint(profile)
           and isinstance(now,datetime) and now.tzinfo is not None
           and isinstance(auth.get("expiresAt"),datetime) and auth["expiresAt"].tzinfo is not None
           and now<auth["expiresAt"],"private-scope-or-consent-denied")
    try:ZoneInfo(profile["zone"])
    except (ValueError,ZoneInfoNotFoundError):raise ValueError("unknown-plan-zone") from None
    rules=profile["rules"]
    ensure(len({r["ruleId"] for r in rules})==len(rules),"conflicting-rule-id")
    for r in rules:
        ensure(date.fromisoformat(r["from"])<=date.fromisoformat(r["through"]),"invalid-rule-window")


def conflicts(rules):
    bad=set()
    for i,r in enumerate(rules):
        for s in rules[:i]:
            if r["severity"]!="hard" or s["severity"]!="hard" or r["targetId"]!=s["targetId"] or r["period"]!=s["period"]:
                continue
            kinds={r["kind"],s["kind"]}
            if kinds in ({"require-ingredient","exclude-ingredient"},{"require-attribute","exclude-attribute"}):
                bad.update((r["ruleId"],s["ruleId"]))
            elif kinds=={"nutrient-min","nutrient-max"}:
                low,high=(r,s) if r["kind"]=="nutrient-min" else (s,r)
                try:
                    x,y=amount(low["magnitude"]),convert(amount(high["magnitude"]),high["unit"],low["unit"])
                    mismatch=x>y or (x==y and not (low["inclusive"] and high["inclusive"]))
                except ValueError:
                    mismatch=True
                if mismatch:bad.update((r["ruleId"],s["ruleId"]))
    return bad


def observation(rule,group,complete):
    """Each group member is (plan entry, externally verified immutable variant)."""
    kind,target=rule["kind"],rule["targetId"]
    if not group:return "unknown",[]
    proofs=[]; flags=[]; numbers=[]; unknown=not complete
    for e,v in group:
        proofs.append(v["evidence"])
        if kind.startswith(("require-","exclude-")):
            section="ingredients" if kind.endswith("-ingredient") else "attributes"
            located=v[section].get(target);state=located["state"] if located else "unknown"
            if located:proofs.append(located["evidence"])
            flags.append(state)
        else:
            n=v["nutrients"].get(target)
            if n is None:
                unknown=True;continue
            proofs.append(n["evidence"])
            try:
                per=convert(amount(n["magnitude"]),n["unit"],rule["unit"])
                if n["basis"]=="per-recipe":
                    y=v["yieldServings"]
                    if y is None or not matches_digest(v["yieldEvidence"]) or amount(y)<=0:
                        unknown=True;continue
                    per/=amount(y);proofs.append(v["yieldEvidence"])
                if rule["period"]!="per-serving":
                    if e["servings"] is None:
                        unknown=True;continue
                    per*=amount(e["servings"])
                numbers.append(per)
            except ValueError:
                unknown=True
    if flags:
        if "conflicting" in flags:return "conflicting",proofs
        if kind.startswith("exclude"):
            if "present" in flags:return "failed",proofs
            return ("unknown" if unknown or "unknown" in flags else "met"),proofs
        if rule["quantifier"]=="every-item":
            if "absent" in flags:return "failed",proofs
            return ("unknown" if unknown or "unknown" in flags else "met"),proofs
        if "present" in flags:return "met",proofs
        return ("unknown" if unknown or "unknown" in flags else "failed"),proofs
    # All known nutrient values are nonnegative. A proven max violation survives
    # an incomplete group; an incomplete group must never be labelled compliant.
    total=sum(numbers,Fraction());threshold=amount(rule["magnitude"])
    if kind=="nutrient-min":ok=total>=threshold if rule["inclusive"] else total>threshold
    else:ok=total<=threshold if rule["inclusive"] else total<threshold
    if unknown and (ok or kind=="nutrient-min"):return "unknown",proofs
    return ("met" if ok else "failed"),proofs


def evaluate_plan(profile,plan,*,authorization,now,variants):
    """Evaluate actual selected variants per member-local day; caller authenticates current context.

    variants[(variantId,revision)] contains independently licensed and immutable
    per-field evidence. Unbound or stale revisions are refused, never substituted.
    """
    authorized(profile,authorization,now);validated(PLAN,plan,"invalid-planning-window")
    ensure(plan["zone"]==profile["zone"],"wrong-period-zone")
    # The plan must not declare its own completeness or remove meals unnoticed.
    # Trusted caller binds the selected complete/incomplete window and membership.
    ensure(isinstance(authorization.get("planPins"), dict) and
           authorization["planPins"].get(plan["planId"])==fingerprint(plan),"unverified-plan-membership")
    dates=plan["days"]; complete=set(plan["completeDays"])
    ensure(len(set(dates))==len(dates) and len(complete)==len(plan["completeDays"]) and complete<=set(dates),"invalid-days")
    for day in dates:date.fromisoformat(day)
    entries=plan["entries"];ensure(len({e["entryId"] for e in entries})==len(entries),"duplicate-plan-entry")
    byday={day:[] for day in dates}
    for e in entries:
        ensure(e["day"] in byday and (e["servings"] is None or amount(e["servings"])>0),"invalid-serving-or-day")
        k=(e["variantId"],e["revision"]);v=variants.get(k)
        ensure(isinstance(v,dict) and v.get("variantId")==k[0] and v.get("revision")==k[1],"unverified-variant")
        validated(VARIANT_SCHEMA,v,"malformed-verified-variant");byday[e["day"]].append((e,v))
    checks=[]
    for day in sorted(dates):
        relevant=[r for r in profile["rules"] if r["from"]<=day<=r["through"]];bad=conflicts(relevant)
        for r in relevant:
            groups={}
            for e,v in byday[day]:
                key={"per-serving":e["entryId"],"per-meal":e["mealId"],"per-day":day}[r["period"]]
                groups.setdefault(key,[]).append((e,v))
            for key,items in sorted((groups or {day:[]}).items()):
                if r["ruleId"] in bad:status,pins="conflicting",[]
                else:status,pins=observation(r,items,r["period"]=="per-serving" or day in complete)
                checks.append({"day":day,"group":key,"ruleId":r["ruleId"],"severity":r["severity"],
                               "status":status,"inputEvidence":sorted(set(pins))})
    hard={c["status"] for c in checks if c["severity"]=="hard"}
    outcome=next((x for x in ("conflicting","failed","unknown") if x in hard),"met")
    window_complete=(bool(entries) and set(dates)==complete and all(byday[d] for d in dates))
    if not window_complete and outcome not in FAILURE:outcome="unknown"
    # Rank one vote per applicable rule and day, not per extra meal in a candidate.
    soft={}
    for c in checks:
        if c["severity"]=="preference":
            soft.setdefault((c["ruleId"],c["day"]),set()).add(c["status"])
    return {"planId":plan["planId"],"audience":{k:profile[k] for k in SCOPE},
            "sessionGeneration":authorization["sessionGeneration"],"hardStatus":outcome,
            "membershipStatus":"complete" if window_complete else "incomplete",
            "preferencesMet":sum(states=={"met"} for states in soft.values()),
            "checks":checks,"clinicalAdvice":False}


def select_plan(profile,plans,*,authorization,now,variants):
    """Choose only fully qualified options, with taste ranking after hard filters."""
    ensure(isinstance(plans,list) and 1<=len(plans)<=100,"candidate-limit")
    results=[evaluate_plan(profile,p,authorization=authorization,now=now,variants=variants) for p in plans]
    ensure(len({r["planId"] for r in results})==len(results),"duplicate-candidate")
    ensure(len({(p["zone"],tuple(sorted(p["days"]))) for p in plans})==1,"different-candidate-windows")
    eligible=sorted((r for r in results if r["hardStatus"]=="met"),key=lambda r:(-r["preferencesMet"],r["planId"]))
    return {"selectedPlanId":eligible[0]["planId"] if eligible else None,"results":results}
