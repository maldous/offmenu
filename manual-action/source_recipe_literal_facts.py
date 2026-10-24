"""Pure, bounded source facts and explicit choices; no native or physical grant."""
from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata

# Reuse the accepted pure finite-JSON/RFC6901/R4 guards. Never call its assessor.
from source_recipe_product_proofs import (
    InvalidInput, Held, _bounded, _pointer, _citation_visibility,
    canonical_sha256, parse_json,
)

PURPOSE = "PRIVATE_INTERNAL_ATTRIBUTED_SOURCE_FACTS_ONLY"
MAX_INPUT_BYTES = 524288
MAX_OUTPUT_BYTES = 262144
MAX_FACTS = 128
MAX_EVENTS = 128
MAX_GROUPS = 16
MAX_BRANCHES = 16
MAX_CITATIONS = 128
MAX_AMOUNT_BYTES = 128
MAX_NODES = 100000
MAX_DEPTH = 32
SHA = re.compile(r"[0-9a-f]{64}\Z")


class SourceFactError(ValueError):
    pass


@dataclass(frozen=True)
class QualifiedSourceFactContext:
    """Construct only through the existing independently accepted caller route.

    This is not authentication of arbitrary Python callers. The review/custody
    issuer must qualify source rights, full coverage and current disposition.
    """
    binding: dict
    review: dict
    custody: dict
    artifacts: dict


def _need(ok, reason):
    if not ok:
        raise SourceFactError(reason)


def _same(left, right):
    return _bounded(left) == _bounded(right)


def _sha(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _text(value, maximum=1024):
    _need(type(value) is str and value.strip() and len(value.encode("utf-8")) <= maximum, "text shape/limit")
    return value


def _index(rows, maximum):
    _need(type(rows) is list and len(rows) <= maximum, "row count/type limit")
    out = {}
    for row in rows:
        _need(type(row) is dict, "row object required")
        identity = _text(row.get("id"), 256)
        _need(identity not in out, "duplicate row ID")
        out[identity] = row
    return out


def _ids(values, known, *, minimum=0, maximum=128):
    _need(type(values) is list and minimum <= len(values) <= maximum
          and all(type(v) is str for v in values), "ID list shape/count")
    _need(len(set(values)) == len(values) and set(values) <= set(known), "duplicate/foreign reference")
    return values


def _span(span, source, *, whole=False):
    _need(type(span) is dict and span.get("offset_unit") == "unicode_codepoint", "Unicode span required")
    pointer = _text(span.get("pointer"))
    value = _pointer(source, pointer)
    start, end = span.get("start"), span.get("end")
    _need(type(value) is str and type(start) is int and type(end) is int
          and 0 <= start < end <= len(value), "span range/type")
    _need(value[start:end] == _text(span.get("text"), 16384), "source span mismatch")
    if whole:
        _need(start == 0 and end == len(value), "whole source context required")
    return value


def _inside(span, containers):
    return any(span["pointer"] == c["pointer"] and c["start"] <= span["start"]
               and span["end"] <= c["end"] for c in containers)


def _spans(spans, source, *, whole=False):
    _need(type(spans) is list and 1 <= len(spans) <= 128, "source spans required")
    for span in spans:
        _span(span, source, whole=whole)


def _source_order(previous, current, source):
    """Compare shared source arrays or positions in one string, without reordering.

    Order across unrelated source fields is the independent review's obligation.
    """
    if previous["pointer"] == current["pointer"]:
        return current["start"] >= previous["end"]
    def positions(span):
        value, prefix, result = source, "", {}
        for encoded in span["pointer"][1:].split("/"):
            key = encoded.replace("~1", "/").replace("~0", "~")
            if type(value) is list:
                result[prefix] = int(key)
                value = value[int(key)]
            else:
                value = value[key]
            prefix += "/" + encoded
        return result
    left, right = positions(previous), positions(current)
    for parent, index in left.items():
        if parent in right and right[parent] != index:
            return right[parent] > index
    return True


def _reference(ref, artifacts):
    _need(type(ref) is dict and set(ref) == {"artifactSHA256", "pointer", "rowSHA256"}, "review reference shape")
    _need(_sha(ref["artifactSHA256"]) and _sha(ref["rowSHA256"]), "review digest shape")
    raw = artifacts[ref["artifactSHA256"]]
    _need(type(raw) is str and hashlib.sha256(raw.encode("utf-8")).hexdigest()
          == ref["artifactSHA256"], "raw review hash mismatch")
    row = _pointer(parse_json(raw), ref["pointer"])
    _need(type(row) is dict and canonical_sha256(row) == ref["rowSHA256"], "resolved review row mismatch")
    return row


def _native_availability(native, source_sha, artifacts):
    if native is None:
        return {"status": "not-supplied", "sourceSHA256": source_sha, "receipt": None, "reasons": []}
    _need(type(native) is dict and native.get("status") in ("available", "held", "not-supplied"),
          "native availability shape")
    _need(native.get("sourceSHA256") == source_sha, "native availability source mismatch")
    reasons = native.get("reasons")
    _need(type(reasons) is list and len(reasons) <= 128, "native reasons shape")
    for reason in reasons:
        _text(reason)
    receipt = native.get("receipt")
    if native["status"] == "available":
        _need(not reasons and receipt is not None, "qualified native receipt required")
    elif native["status"] == "held":
        _need(bool(reasons), "native held reason required")
    else:
        _need(not reasons and receipt is None, "not-supplied native availability cannot assert a receipt")
    if receipt is not None:
        _reference(receipt, artifacts)
    # Existing native semantics are qualified by the accepted caller/review route,
    # not reinterpreted here or inferred from source facts.
    return native


def _qualified(record, ctx):
    binding = ctx["binding"]
    _need(type(binding) is dict and binding.get("purpose") == PURPOSE and record.get("purpose") == PURPOSE,
          "private source purpose required")
    _need(binding.get("recordSHA256") == canonical_sha256(record), "unreviewed record digest")
    _need(_same(binding.get("sourceScope"), record["sourceScope"]), "source scope mismatch")
    _need(binding.get("sourceSHA256") == record["source"]["rawSHA256"], "source digest mismatch")
    author, reviewer = binding.get("authorThreadId"), binding.get("reviewerThreadId")
    _need(type(author) is str and author and type(reviewer) is str and reviewer and author != reviewer,
          "independent review required")
    _need(binding.get("disposition") == "active" and binding.get("conflicts") == []
          and binding.get("revoked") is False, "review revoked/conflicting/inactive")
    _need(type(binding.get("constraints")) is dict and binding["constraints"], "reviewed constraints required")
    actual = _reference(ctx["review"], ctx["artifacts"])
    _need(_same(actual, binding), "review binding mismatch")
    custody = _reference(ctx["custody"], ctx["artifacts"])
    _need(_same(custody, {"review": ctx["review"], "binding": binding, "disposition": "accepted"}),
          "owner custody mismatch")
    native = _native_availability(binding.get("nativeAvailability"), binding["sourceSHA256"], ctx["artifacts"])
    return binding, native


def _source(record):
    source = record["source"]
    _need(type(source) is dict and _sha(source.get("rawSHA256")), "raw source reference required")
    raw = _text(source.get("rawText"), MAX_INPUT_BYTES)
    _need(hashlib.sha256(raw.encode("utf-8")).hexdigest() == source["rawSHA256"], "raw source hash mismatch")
    _text(source.get("artifactReference"), 4096)  # Opaque reference, never opened.
    original = parse_json(raw)
    scope = record["sourceScope"]
    _need(type(scope) is dict and scope.get("rawSHA256") == source["rawSHA256"], "source scope hash")
    _text(scope.get("occurrenceId"), 256)
    pointers = source["scopePointers"]
    _need(type(pointers) is dict and set(pointers) == set(scope) - {"rawSHA256", "occurrenceId"}
          and pointers, "source scope field bindings required")
    for field, pointer in pointers.items():
        _need(_same(_pointer(original, pointer), scope[field]), "source identity field mismatch")
    return original


def _citations(record, binding):
    citations = _index(record["citations"], MAX_CITATIONS)
    rights = binding["citationRights"]
    _need(type(rights) is dict and set(rights) == set(citations), "citation rights closure")
    for cid, citation in citations.items():
        payload = citation["payload"]
        _need(citation.get("state") == "verified" and rights[cid]["purpose"] == PURPOSE,
              "citation state/purpose not qualified")
        _need(_sha(citation.get("payloadSHA256")) and canonical_sha256(payload) == citation["payloadSHA256"]
              == rights[cid]["payloadSHA256"], "citation payload mismatch")
        _need(_citation_visibility(payload) == rights[cid]["visibility"], "citation visibility mismatch")
        _text(payload.get("license")); _text(payload.get("attribution"), 8192)
    return citations


def _row_evidence(row, source, citations, *, whole=False):
    _spans(row["sourceSpans"], source, whole=whole)
    _ids(row["citationIds"], citations, minimum=1, maximum=MAX_CITATIONS)


def _numeric_boundary(span, source):
    raw = _span(span, source)
    before, after = raw[:span["start"]].rstrip(), raw[span["end"]:].lstrip()
    while before and (unicodedata.category(before[-1]) in ("Ps", "Pi") or before[-1] in "\"'"):
        before = before[:-1].rstrip()
    while after and (unicodedata.category(after[0]) in ("Pe", "Pf") or after[0] in "\"'"):
        after = after[1:].lstrip()
    bad = "/⁄∕+−﹣－＋﹢±×÷.,^"
    _need(not before or (before[-1] not in bad and unicodedata.category(before[-1])[0] != "N"
                        and unicodedata.category(before[-1]) != "Pd"), "partial numeric prefix")
    _need(not after or (after[0] not in bad and unicodedata.category(after[0])[0] != "N"
                       and unicodedata.category(after[0]) != "Pd"), "partial numeric suffix")
    _need(not re.search(r"\d\s+to\s*$", before, re.I)
          and not re.match(r"to\s+\d", after, re.I), "partial numeric range")
    _need(not re.search(r"\d\s*\*\s*$", before)
          and not re.match(r"\*\s*\d", after), "partial numeric multiplication")
    if before and before[-1] in "xXeE":
        operand = before[:-1].rstrip()
        while operand and (unicodedata.category(operand[-1]) in ("Pe", "Pf") or operand[-1] in "\"'"):
            operand = operand[:-1].rstrip()
        _need(not operand or unicodedata.category(operand[-1])[0] != "N", "partial numeric expression operand")
    if after and after[0] in "xXeE":
        operand, position, prefix_bytes = after[1:], 0, 0
        while position < len(operand):
            character = operand[position]
            if not (character.isspace() or character in "+-−﹣－＋﹢±\"'"
                    or unicodedata.category(character) in ("Ps", "Pe", "Pi", "Pf")):
                break
            prefix_bytes += len(character.encode("utf-8"))
            _need(prefix_bytes <= MAX_AMOUNT_BYTES, "numeric operand prefix limit")
            position += 1
        _need(position == len(operand) or unicodedata.category(operand[position])[0] != "N",
              "partial numeric expression operand")


def _word_count_boundary(span, source):
    raw = _span(span, source)
    def word_character(character):
        category = unicodedata.category(character) if character else ""
        return bool(character) and (category[:1] in ("L", "M", "N") or category == "Pc"
                                    or character in ("\u200c", "\u200d"))
    start, end = span["start"], span["end"]
    left = raw[start - 1] if start else ""
    right = raw[end] if end < len(raw) else ""
    _need(not word_character(left) and not word_character(right), "word count requires a whole source token")
    apostrophes = ("'", "’", "ʼ")
    _need(not (left in apostrophes and start > 1 and word_character(raw[start - 2]))
          and not (right in apostrophes and end + 1 < len(raw) and word_character(raw[end + 1])),
          "word count requires a whole source token")


def _facts(rows, source, citations):
    facts = _index(rows, MAX_FACTS)
    for fact in facts.values():
        _row_evidence(fact, source, citations, whole=True)
        binding = fact["binding"]
        _need(binding["kind"] in ("ingredient-total", "method-use"), "quantity use scope")
        _text(binding["sourceId"], 256)
        amount = fact["amount"]
        _need(type(amount) is dict and amount.get("state") in ("stated", "not-stated", "qualitative"),
              "known amount must remain a tagged source fact")
        if amount["state"] == "not-stated":
            _need(not {"form", "lexeme", "span"}.intersection(amount), "unstated amount cannot hide a known literal")
        elif amount["state"] == "qualitative":
            _need("form" not in amount, "qualitative source text cannot assert a numeric form")
        if amount["state"] != "not-stated":
            lexeme = _text(amount.get("lexeme"), MAX_AMOUNT_BYTES)
            span = amount["span"]
            _span(span, source)
            _need(span["text"] == lexeme and _inside(span, fact["sourceSpans"]), "amount source binding")
            if amount["state"] == "stated":
                form = amount.get("form")
                valid = ((form in ("integer", "relative-part") and re.fullmatch(r"[0-9]{1,9}", lexeme))
                         or (form == "fraction" and re.fullmatch(r"[¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|[0-9]{1,9}/[1-9][0-9]{0,8}", lexeme))
                         or (form == "range" and re.fullmatch(r"[0-9]{1,9}\s*(?:-|–|—|to)\s*[0-9]{1,9}", lexeme))
                         or (form == "word-count" and lexeme.lower() == "one"))
                _need(bool(valid), "unsupported literal amount form")
                _numeric_boundary(span, source)
                if form == "word-count":
                    _word_count_boundary(span, source)
                _need("unit" in fact, "stated source unit required")
        if "unit" in fact:
            unit = fact["unit"]
            _text(unit["lexeme"], 128); _span(unit["span"], source)
            _need(unit["span"]["text"] == unit["lexeme"] and _inside(unit["span"], fact["sourceSpans"]),
                  "unit source binding")
        for qualifier in fact.get("qualifiers", []):
            _span(qualifier, source)
            _need(_inside(qualifier, fact["sourceSpans"]), "qualifier source binding")
        for use in fact.get("useMentions", []):
            _need(use["kind"] == "ordinal", "source use kind")
            _span(use["span"], source)
            _need(use["lexeme"] == use["span"]["text"], "ordinal source binding")
    return facts


def _events(rows, source, citations):
    events = _index(rows, MAX_EVENTS)
    previous = None
    for event in events.values():
        _row_evidence(event, source, citations)
        verb = event["verb"]
        _span(verb["span"], source)
        _need(verb["lexeme"] == verb["span"]["text"] and _inside(verb["span"], event["sourceSpans"]),
              "source event lexeme binding")
        actor = event["actor"]
        _need(actor["kind"] in ("explicit", "unspecified"), "source actor kind")
        if actor["kind"] == "explicit":
            _span(actor["span"], source)
            _need(actor["lexeme"] == actor["span"]["text"] and _inside(actor["span"], event["sourceSpans"]),
                  "source actor binding")
        else:
            _need("lexeme" not in actor and "span" not in actor, "unspecified actor cannot assert a source actor")
        if event.get("membership") is None:
            _need(previous is None or _source_order(previous, verb["span"], source), "event source order")
            previous = verb["span"]
    return events


def _groups(record, source, citations, facts, events):
    relative = _index(record["relativeGroups"], MAX_GROUPS)
    alternatives = _index(record["alternativeGroups"], MAX_GROUPS)
    _need(len(relative) + len(alternatives) <= MAX_GROUPS and not set(relative) & set(alternatives), "group count/ID limit")
    parts = set()
    for group in relative.values():
        _need(group["kind"] == "relative-volume" and _same(group["sourceScope"], record["sourceScope"]), "relative source scope")
        _row_evidence(group, source, citations)
        members = _ids(group["factIds"], facts, minimum=2, maximum=MAX_BRANCHES)
        _need(not parts.intersection(members), "duplicate relative part")
        _need([i for i in facts if i in members] == members, "relative part source order")
        previous = None
        for fid in members:
            fact = facts[fid]
            _need(fact["amount"].get("form") == "relative-part" and fact["unit"]["lexeme"] in ("volume", "volumes")
                  and fact.get("membership") is None, "relative part kind/unit/choice")
            _need(re.fullmatch(r"[1-9][0-9]{0,8}", fact["amount"]["lexeme"])
                  and all(_inside(s, group["sourceSpans"]) for s in fact["sourceSpans"]),
                  "positive relative part source closure")
            span = fact["amount"]["span"]
            _need(previous is None or _source_order(previous, span, source), "relative part source order")
            previous = span
        parts.update(members)
    _need(parts == {i for i, f in facts.items() if f["amount"].get("form") == "relative-part"}, "relative pair closure")
    fact_members, event_members = {}, {}
    branch_ids = {}
    for group in alternatives.values():
        _need(group["kind"] in ("quantity-choice", "ingredient-choice", "method-choice", "service-choice", "optional-context")
              and _same(group["sourceScope"], record["sourceScope"]), "alternative source kind/scope")
        _need(group["selection"] is None, "source choice must stay unselected")
        _row_evidence(group, source, citations)
        branches = _index(group["branches"], MAX_BRANCHES)
        _need(len(branches) >= (1 if group["kind"] == "optional-context" else 2), "complete alternative branches required")
        branch_ids[group["id"]] = list(branches)
        for branch in branches.values():
            _row_evidence(branch, source, citations)
            _need(all(_inside(s, group["sourceSpans"]) for s in branch["sourceSpans"]), "branch source closure")
            membership = {"groupId": group["id"], "branchId": branch["id"]}
            for fid in _ids(branch["factIds"], facts):
                _need(fid not in fact_members and _same(facts[fid].get("membership"), membership), "quantity branch closure")
                fact_members[fid] = membership
                amount = facts[fid]["amount"]
                if amount["state"] == "stated":
                    _need(_inside(amount["span"], branch["sourceSpans"])
                          and _inside(facts[fid]["unit"]["span"], branch["sourceSpans"]), "quantity branch span")
            prior = None
            for eid in _ids(branch["eventIds"], events):
                _need(eid not in event_members and _same(events[eid].get("membership"), membership), "event branch closure")
                event_members[eid] = membership
                event = events[eid]
                _need(all(_inside(s, branch["sourceSpans"]) for s in event["sourceSpans"]), "event outside branch")
                span = event["verb"]["span"]
                _need(prior is None or _source_order(prior, span, source), "branch event source order")
                prior = span
    _need({k: f.get("membership") for k, f in facts.items() if f.get("membership") is not None} == fact_members,
          "undeclared quantity membership")
    _need({k: e.get("membership") for k, e in events.items() if e.get("membership") is not None} == event_members,
          "undeclared event membership")
    return relative, alternatives, branch_ids


def build_source_recipe_literal_facts(record, *, qualified_context):
    """Return a source-only companion, or an atomic bounded rejection.

    External JSON must pass parse_json first. Unknown finite fields survive as
    opaque data; none supplies authority or a higher-stage status.
    """
    try:
        _need(type(qualified_context) is QualifiedSourceFactContext, "caller-owned qualified context required")
        raw = {"record": record, "context": {"binding": qualified_context.binding,
               "review": qualified_context.review, "custody": qualified_context.custody,
               "artifacts": qualified_context.artifacts}}
        frozen = json.loads(_bounded(raw, MAX_INPUT_BYTES))
        record, ctx = frozen["record"], frozen["context"]
        _need(type(record) is dict, "one source record object required")
        binding, native = _qualified(record, ctx)
        original = _source(record)
        citations = _citations(record, binding)
        facts = _facts(record["literalFacts"], original, citations)
        events = _events(record["sourceEvents"], original, citations)
        _need(facts or events, "source facts or events required")
        contexts = _index(record["mandatoryContexts"], MAX_FACTS)
        for context in contexts.values():
            _row_evidence(context, original, citations, whole=True)
        relative, alternatives, branch_ids = _groups(record, original, citations, facts, events)
        coverage = {"literalFactIds": list(facts), "knownAmountFactIds": [k for k, f in facts.items() if f["amount"]["state"] == "stated"],
                    "eventIds": list(events), "contextIds": list(contexts),
                    "relativeGroupMembers": {k: v["factIds"] for k, v in relative.items()},
                    "alternativeGroupBranches": branch_ids,
                    "explicitActors": {k: e["actor"]["lexeme"] for k, e in events.items() if e["actor"]["kind"] == "explicit"}}
        _need(_same(coverage, binding["coverage"]), "independently reviewed full coverage mismatch")
        known = {"purpose", "sourceScope", "source", "citations", "literalFacts", "relativeGroups",
                 "alternativeGroups", "sourceEvents", "mandatoryContexts"}
        output = {"outcome": "source-facts-qualified", "purpose": PURPOSE,
                  "sourceFactQualification": {"status": "qualified", "recordSHA256": binding["recordSHA256"],
                                               "sourceSHA256": binding["sourceSHA256"]},
                  "normalizedInstructionAvailability": native,
                  "executableSuitability": {"status": "not-qualified", "actualSelection": "unobserved", "currentStateFit": None},
                  "nutritionCompleteness": {"status": "not-qualified", "actualRecipeComposition": None,
                                            "globalProductFitAcceptance": False, "metricNormalization": None},
                  "sourceReference": {k: v for k, v in record["source"].items() if k != "rawText"},
                  "sourceScope": record["sourceScope"], "literalFacts": record["literalFacts"],
                  "relativeGroups": record["relativeGroups"], "alternativeGroups": record["alternativeGroups"],
                  "sourceEvents": record["sourceEvents"], "mandatoryContexts": record["mandatoryContexts"],
                  "citations": record["citations"], "uninterpretedRecordFields": {k: v for k, v in record.items() if k not in known},
                  "qualification": {"binding": binding, "review": ctx["review"], "custody": ctx["custody"]},
                  "restrictions": ["source facts only; no allocation, conversion or branch selection",
                                   "native availability requires its separate qualified receipt",
                                   "no executable, nutrition, safety, serving, yield or runtime grant"]}
        _bounded(output, MAX_OUTPUT_BYTES)
        return output
    except (SourceFactError, InvalidInput, Held, KeyError, IndexError, TypeError, ValueError) as exc:
        return {"outcome": "rejected", "reason": str(exc)[:160],
                "sourceFactQualification": {"status": "held"},
                "normalizedInstructionAvailability": {"status": "not-supplied"},
                "executableSuitability": {"status": "not-qualified"},
                "nutritionCompleteness": {"status": "not-qualified", "actualRecipeComposition": None,
                                          "globalProductFitAcceptance": False}}
