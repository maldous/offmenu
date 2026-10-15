#!/usr/bin/env python3
"""Independent verifier for the 2026-10-15 semantic-lane review candidate.

Review-only tooling for Worker 02's exact independent review of the frozen
semantic-lane candidate (frozen manifest sha256 recorded in the review
receipt).  Read-only: verifies declared hash pins, denominators, outputSha256
self-hashes, judgment<->sample pin chains, remediation lineage, glossary rows
and the absence of fabricated quote text.  It never imports the lane's own
checker and never writes to the reviewed tree.

Usage: python3 scripts/review-verify-semantic-candidate-20261015.py <frozen-tree>
Prints one JSON report; exit 0 iff no unexpected findings.
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CONTRACT = "b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa"
DECLARED_PINS = {
    "checkpoint/queue-state.json": "2c1263355fa84a0931e7430be1be0420d5167ece8ffb05ce2bd3303d5529997d",
    "admission/all.admission.json": "47cc09acf70ce4c41896b86ed7310b0393d0df65bbc38310fce9edda66487e3d",
    "glossary/proposals.jsonl": "df152cdb077a0bda83688c870f57e1f651383affcbfd233123e77089eb8361d2",
    "STATUS.json": "110226ac6375da81943c3b1d2acfd6023fd0dc1de2963806a4258563b411c0f0",
    "queue/ciqual-2025.queue.jsonl": "9d0318b0b919bdc5c0284851448dccd5c7d167ed36077c9ce3a6e6273ad901ff",
    "queue/off-2026-10-12-lf.queue.jsonl": "d4ce0da2efc4bc38eea9a1b8cb41c0d7086dddc4ca49b16245af847804193039",
    "queue/prices-2026-10-12.queue.jsonl": "7f6df9cd492a4e41a3417ed64c7f92cef701513362a0cae4855e3cfbc5346a18",
    "queue/wikibooks-2026-10-13-live.queue.jsonl": "6328e5753f231aadddc049d2db6a262d5ab7bedaa050b85cb001c132bed38ead",
    "queue/wikidata-businesses-20261013.queue.jsonl": "93e622333c5fc31c7d3d8e4959ae7bb501dc22ca95b04b6e5d8504e8e7ec4735",
}
CORRECTED_FILES = {
    "judgments/ciqual-2025/sq:34b3a5befcbdee7f3f69dd91.json": "47e5153691d8de37df4d5e048377c8f6c5980073e776be854d3458ea865a65c0",
    "judgments/ciqual-2025/sq:562993bfe07e14752c150923.json": "a7b70d61104cc456f02a73750419ae0800b743d485ea929ae709575806448159",
    "judgments/ciqual-2025/sq:95e167d455de4b7857c589b0.json": "8cf30f5fae906173fd4b94c34e9d0ea9fd2faaba6f7d22b69aa11729654cca61",
    "judgments/ciqual-2025/sq:99625fde6e9ba87913ac98dd.json": "05238d98a65a3906e74194f3a2fba53f365802cb2b84e782c0559221f6ace6b0",
    "judgments/ciqual-2025/sq:b5faac1a1a12a1962409cf1f.json": "e66a9c2af289c67dc93244e879ebf6cb66c10f7943f21a21edcb776d34f70c9b",
    "judgments/ciqual-2025/sq:f3bfc0f209e138cd64385b18.json": "5934b0f6a9621ca6b11ce01bbf2494359e10754aceef3ee7a7533967c9f444a4",
}
REMEDIATION_KEYS = {"appliedAtUTC", "appliedBy", "reason", "supersedesProposal", "priorModelId", "historyPreserved"}
EXPECTED = {
    "total": 78, "done": 58, "blocked": 20, "open": 0, "skipped": 0,
    "fields": {"original": 63, "proposed": 2, "conflict": 4, "unknown": 4},
    "acceptedFields": 0,
    "stages": {"unit": 14, "value": 14, "terminology-en": 6, "translation-stage": 6,
               "dietary": 6, "ingredient": 6, "price": 6},
    "models": {"native-active-model/unverified-catalog-id": 23,
               "nemotron-3.5-lightning": 35, "blocked-unqualified": 20},
}


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def shao(obj):
    return hashlib.sha256(canon(obj)).hexdigest()


def shaf(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(sys.argv[1])
    findings = []
    # 1. Declared pins
    for rel, want in DECLARED_PINS.items():
        if shaf(root / rel) != want:
            findings.append(f"pin mismatch: {rel}")
    # 2. Denominators from queue-state + judgments
    qs = json.loads((root / "checkpoint/queue-state.json").read_text())
    counts = qs.get("counts", {})
    for key in ("done", "blocked", "open", "skipped"):
        if counts.get(key) != EXPECTED[key]:
            findings.append(f"queue-state counts.{key}={counts.get(key)} != {EXPECTED[key]}")
    stage_done = Counter()
    field_state = Counter()
    model = Counter()
    model_by_ds = defaultdict(Counter)
    selfhash_bad = []
    pin_errors = []
    quote_fabricated = []
    remediated = []
    files = sorted((root / "judgments").rglob("*.json"))
    if len(files) != EXPECTED["total"]:
        findings.append(f"judgment file count {len(files)} != {EXPECTED['total']}")
    queue = {}
    for qf in sorted((root / "queue").glob("*.jsonl")):
        for line in qf.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                queue[q["itemId"]] = q
    for jf in files:
        j = json.loads(jf.read_text())
        iid = j["itemId"]
        model[j["model"]["modelId"]] += 1
        model_by_ds[j["dataset"]][j["model"]["modelId"]] += 1
        body = dict(j)
        declared = body.pop("outputSha256", None)
        body["outputSha256"] = ""
        blocked = j["model"]["modelId"] == "blocked-unqualified"
        if declared != shao(body) and not blocked:
            selfhash_bad.append(iid)
        if blocked:
            if declared not in (None, ""):
                findings.append(f"blocked artifact has non-empty outputSha256: {iid}")
        else:
            stage_done[j["stage"]] += 1
        qi = queue.get(iid)
        if qi is None:
            pin_errors.append((iid, "not-in-queue"))
            continue
        sp = root / qi["sampleFile"]
        s = json.loads(sp.read_text())
        if j["recordSha256"] != s["recordSha256"]:
            pin_errors.append((iid, "recordSha-judgment-vs-sample"))
        if shao(s["record"]) != s["recordSha256"]:
            pin_errors.append((iid, "sample-recordSha-not-recompute"))
        ctx = shao({"dataset": s["dataset"], "stage": qi["stage"], "sampleSha256": shaf(sp), "contract": CONTRACT})
        if j["contextSha256"] != ctx:
            pin_errors.append((iid, "contextSha-mismatch"))
        for c in j.get("citations", []):
            if c.get("sampleFile") and c["sampleFile"] != qi["sampleFile"]:
                pin_errors.append((iid, "citation-sampleFile"))
            if s.get("archiveSha256") and c.get("archiveSha256") != s["archiveSha256"]:
                pin_errors.append((iid, "citation-archiveSha"))
            if s.get("sourceUrl") and c.get("sourceUrl") != s["sourceUrl"]:
                pin_errors.append((iid, "citation-sourceUrl"))
            if c.get("quote") is not None and c["quote"] not in json.dumps(s["record"], ensure_ascii=False):
                quote_fabricated.append((iid, c["quote"][:40]))
        for f in j.get("fields", []):
            field_state[f.get("provenanceState")] += 1
            node = s["record"]
            try:
                for part in f["fieldPath"].split("."):
                    node = node[part]
            except Exception:
                pin_errors.append((iid, "fieldPath-unresolvable:" + str(f.get("fieldPath"))))
                continue
            if not blocked and canon(node) != canon(f.get("original", "<absent>")):
                pin_errors.append((iid, "original-mismatch:" + str(f.get("fieldPath"))))
        if "remediation" in j:
            remediated.append(iid)
            if not REMEDIATION_KEYS <= set(j["remediation"]):
                findings.append(f"remediation keys incomplete: {iid}")
            if j["fields"][0].get("provenanceState") != "original" or j["fields"][0].get("proposed") is not None:
                findings.append(f"corrected field not reconciled: {iid}")
    # 3. Expected tallies
    if sum(stage_done.values()) != EXPECTED["done"] or dict(stage_done) != EXPECTED["stages"]:
        findings.append(f"stage tally mismatch: {dict(stage_done)}")
    done_fields = {k: v for k, v in field_state.items() if k != "blocked"}
    if done_fields != EXPECTED["fields"]:
        findings.append(f"field tally mismatch: {done_fields}")
    if field_state.get("accepted", 0) != EXPECTED["acceptedFields"]:
        findings.append(f"accepted fields {field_state.get('accepted', 0)} != {EXPECTED['acceptedFields']}")
    if dict(model) != EXPECTED["models"]:
        findings.append(f"model tally mismatch: {dict(model)}")
    if selfhash_bad:
        findings.append(f"outputSha256 mismatch in done set: {selfhash_bad}")
    if pin_errors:
        findings.append(f"pin errors in done set: {pin_errors[:5]} (total {len(pin_errors)})")
    if quote_fabricated:
        findings.append(f"fabricated quote text: {quote_fabricated[:5]}")
    expected_ids = sorted(Path(rel).stem for rel in CORRECTED_FILES)
    if sorted(remediated) != expected_ids:
        findings.append("remediation file set != the six claimed corrections")
    for rel, want in CORRECTED_FILES.items():
        if shaf(root / rel) != want:
            findings.append(f"corrected file sha mismatch: {rel}")
    # 4. Glossary
    rows = [json.loads(l) for l in (root / "glossary/proposals.jsonl").read_text().splitlines() if l.strip()]
    if len(rows) != 4:
        findings.append(f"glossary rows {len(rows)} != 4")
    for r in rows:
        if r.get("status") != "proposal-unfrozen" or r.get("schemaVersion") != "glossary-proposal/0":
            findings.append(f"glossary row not unfrozen/glossary-proposal/0: {r.get('nativeText')}")
        cites = json.dumps(r)
        if "17550133" not in cites:
            findings.append(f"glossary row missing Zenodo 17550133 pin: {r.get('nativeText')}")
    report = {
        "schemaVersion": "offmenu-semantic-candidate-review-verifier/1",
        "reviewedRoot": str(root),
        "declaredPinsChecked": len(DECLARED_PINS),
        "judgmentFiles": len(files),
        "denominators": {"queueStateCounts": counts, "stageDone": dict(stage_done),
                         "fieldStatesDone": done_fields, "models": dict(model)},
        "outputSha256ValidDoneSet": not selfhash_bad,
        "pinChainErrorsDoneSet": len(pin_errors),
        "fabricatedQuoteTexts": len(quote_fabricated),
        "remediationFiles": sorted(remediated),
        "glossaryRows": len(rows),
        "findings": findings or ["none — candidate internally consistent with all declared claims checked"],
        "verdict_support": "consistent" if not findings else "discrepancies-present",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
