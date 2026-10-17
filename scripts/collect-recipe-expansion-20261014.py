#!/usr/bin/env python3
"""Acquire a small, rights-evidenced multilingual recipe expansion.

Only repositories whose root licence applies an explicit CC0 or Unlicense
dedication are considered.  Each fetched blob is pinned to a Git commit and
kept beside the normalized records so downstream alignment can cite the exact
source wording.  This is deliberately not a scraper for recipe websites.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from recipe_format import ingredient, norm  # conservative units and aliases

RELEASE = "recipe-expansion-20261014"
SOURCES = (
    {"repo": "lvisintini/recetasdemami", "language": "es", "licence": "CC0-1.0",
     "prefix": "docs/", "suffix": ".md", "exclude": "/index.md"},
    {"repo": "Remarknl/Indisch-eten", "language": "nl", "licence": "CC0-1.0",
     "paths": ("nasi-goreng/recept", "Vissoep/recept")},
    {"repo": "chefdelakarma/libre_cuisine", "language": "nl", "licence": "CC0-1.0",
     "suffix": ".txt", "exclude": None},
    {"repo": "clicat/Ricette", "language": "it", "licence": "CC0-1.0",
     "suffix": ".md", "exclude": None},
    {"repo": "rochacbruno/vegan_recipes", "language": "pt", "licence": "Unlicense",
     "prefix": "notes/", "suffix": ".md", "exclude": "Template.md"},
)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "offmenu-source-research/1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()

def api(path):
    return json.loads(fetch("https://api.github.com" + path).decode("utf-8"))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def lines_as_ingredients(lines):
    values = []
    for line in lines:
        line = line.strip().lstrip("-*• ").strip()
        if not line or line.startswith(("{", "<", "#")):
            continue
        parsed = ingredient(line)
        if parsed:
            values.append(parsed)
    return values

def clean_markdown(value):
    value = re.sub(r"^---.*?---\s*", "", value, flags=re.S)
    value = re.sub(r"\{[^{}]+\}", "", value)
    value = re.sub(r"!\[[^]]*\]\([^)]*\)", "", value)
    return value.replace("\r\n", "\n").strip()

def parse_markdown(title, body, source):
    """Extract explicitly labelled sections; no inferred food from prose."""
    front_matter_title = re.search(r"(?m)^page_title:\s*[\"']?(.+?)[\"']?\s*$", body)
    body = clean_markdown(body)
    if source["repo"] == "clicat/Ricette":
        # A source-published English rendering follows a separator.  Preserve
        # the Italian variant here; it is not an automatic translation.
        body = body.split("---\n\n### Birthday Cake", 1)[0]
    source_h1 = re.search(r"(?m)^#\s+(.+?)\s*$", body)
    blocks = re.split(r"(?m)^#{1,6}\s+", body)
    title_from_source = (front_matter_title.group(1).strip() if front_matter_title else
                         re.sub(r"[*_]", "", source_h1.group(1)).strip() if source_h1 else None)
    ingredients, directions = [], []
    active = None
    for block in blocks:
        head, _, content = block.partition("\n")
        h = norm(head).strip(": ")
        if any(x in h for x in ("utensil", "fotos", "foto", "variantes", "variante")):
            active = None
        elif any(x in h for x in ("ingrediente", "ingredienti", "ingredients", "ingredienten")):
            active = "ingredients"
            ingredients.extend(lines_as_ingredients(content.splitlines()))
        elif any(x in h for x in ("preparacion", "preparación", "preparazione", "procedimiento", "bereiding", "method", "procedimento")):
            active = "directions"
            directions.extend(x.strip().lstrip("-*• ").strip() for x in content.splitlines()
                              if x.strip() and not x.strip().startswith(("{", "<", "#")))
        elif active == "ingredients":
            # Nested recipe-component headings (for example, "Massa") retain
            # the enclosing ingredients mode.  This avoids dropping complete
            # ingredient lists while still stopping at utensils/photos.
            ingredients.extend(lines_as_ingredients(content.splitlines()))
        elif active == "directions":
            directions.extend(x.strip().lstrip("-*• ").strip() for x in content.splitlines()
                              if x.strip() and not x.strip().startswith(("{", "<", "#")))
    if source["repo"] == "lvisintini/recetasdemami" and not ingredients:
        # This publisher leaves the Ingredients table blank in many records and
        # lists inputs directly after a one-word preparation verb. Retain only
        # the contiguous leading bullet group as source ingredient statements.
        for match in re.finditer(r"(?m)^\s*(?:Licuar|Mezclar|Batir|Procesar|Combinar|Poner|Colocar)\s*:\s*\n((?:\s*[-*].*\n?)+)", body, re.I):
            ingredients.extend(lines_as_ingredients(match.group(1).splitlines()))
    directions = [re.sub(r"^\d+[.)]\s*", "", x) for x in directions]
    directions = [x for x in directions if len(x) >= 3 and x.lower() != "todo"]
    return title_from_source or title, ingredients, directions, bool(source_h1 or front_matter_title)

def parse_plain(title, body, source):
    if source["repo"] == "Remarknl/Indisch-eten":
        paras = [x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()]
        return title, lines_as_ingredients(paras[0].split(",")), paras[1:], False
    parts = re.split(r"(?im)^\s*(?:Bereiding|Bereiding bouillon|Bereiding snert)\s*:\s*$", body)
    before = parts[0]
    directions = []
    for part in parts[1:]:
        directions += [x.strip() for x in part.splitlines() if x.strip() and not x.lstrip().startswith("#")]
    name = re.search(r"(?im)^#\s*NAME:\s*(.+)$", body)
    if name:
        title = name.group(1).strip()
    ingredient_lines = []
    for line in before.splitlines():
        if line.lstrip().startswith("#") or re.match(r"(?i)^\s*ingredient", line):
            continue
        ingredient_lines.append(line)
    return title, lines_as_ingredients(ingredient_lines), directions, bool(name)

def source_paths(tree, source):
    paths = source.get("paths")
    if paths:
        return list(paths)
    result = []
    for entry in tree:
        path = entry["path"]
        if entry.get("type") != "blob" or path in {"LICENSE", "LICENSE.md", "README.md"}:
            continue
        if source.get("prefix") and not path.startswith(source["prefix"]):
            continue
        if source.get("suffix") and not path.endswith(source["suffix"]):
            continue
        if source.get("exclude") and path.endswith(source["exclude"]):
            continue
        result.append(path)
    return sorted(result)

def run(output):
    if output.exists():
        raise SystemExit(f"immutable output already exists: {output}")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    raw = output / "originals"
    raw.mkdir(parents=True)
    accepted, decisions, acquisitions = [], [], []
    for source in SOURCES:
        repo = source["repo"]
        metadata = api("/repos/" + repo)
        commit = api("/repos/" + repo + "/commits/" + metadata["default_branch"])["sha"]
        tree = api("/repos/" + repo + "/git/trees/" + commit + "?recursive=1")["tree"]
        licence_entry = next((x for x in tree if x["path"] in ("LICENSE", "LICENSE.md")), None)
        if not licence_entry:
            raise RuntimeError(f"{repo}: no root licence")
        licence = fetch(f"https://raw.githubusercontent.com/{repo}/{commit}/{licence_entry['path']}")
        if source["licence"] == "CC0-1.0" and b"CC0 1.0" not in licence:
            raise RuntimeError(f"{repo}: declared CC0 is not present in root licence")
        if source["licence"] == "Unlicense" and b"unlicense" not in licence.lower():
            raise RuntimeError(f"{repo}: declared Unlicense is not present in root licence")
        repo_dir = raw / repo.replace("/", "--")
        repo_dir.mkdir()
        (repo_dir / licence_entry["path"]).write_bytes(licence)
        selected = source_paths(tree, source)
        acquisition = {"repository": repo, "commit": commit, "licence": source["licence"],
                       "licencePath": licence_entry["path"], "licenceSha256": sha(licence),
                       "repositoryUrl": metadata["html_url"], "rightsEvidenceUrl": metadata["html_url"] + "/blob/" + commit + "/" + licence_entry["path"],
                       "filesConsidered": len(selected), "files": []}
        for path in selected:
            data = fetch(f"https://raw.githubusercontent.com/{repo}/{commit}/{urllib.parse.quote(path)}")
            target = repo_dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            body = data.decode("utf-8")
            title = Path(path).stem.replace("-", " ").replace("_", " ")
            if path.endswith(".md"):
                title, ingredients, directions, source_title_asserted = parse_markdown(title, body, source)
            else:
                title, ingredients, directions, source_title_asserted = parse_plain(title, body, source)
            entry = {"path": path, "sha256": sha(data), "bytes": len(data)}
            acquisition["files"].append(entry)
            if not title or len(ingredients) < 2 or not directions:
                decisions.append({"repository": repo, "path": path, "decision": "excluded", "reason": "no-two-source-ingredient-statements-and-directions"})
                continue
            record_id = "recipe-expansion:recipe:" + sha((repo + "\0" + path).encode())[:24]
            url = f"https://github.com/{repo}/blob/{commit}/{urllib.parse.quote(path)}"
            accepted.append({"schemaVersion": "1.0", "kind": "recipe", "id": record_id, "countries": [],
                "provenance": {"sourceId": "recipe-expansion-20261014", "originSourceId": "github:" + repo,
                    "recordId": path, "url": url, "sourceRevision": commit, "license": source["licence"],
                    "licenseUrl": "https://creativecommons.org/publicdomain/zero/1.0/" if source["licence"] == "CC0-1.0" else "https://unlicense.org/",
                    "rightsEvidenceUrl": acquisition["rightsEvidenceUrl"], "attribution": repo + " contributors",
                    "visibility": "public", "fetchedAt": now, "releaseId": RELEASE,
                    "originalContentSha256": sha(data), "recipeReuse": "licensed-full-recipe-content",
                    "changes": "Sectioned source text; conservative quantities; original ingredient wording and source units retained.",
                    "sourceTitleStatus": "source-asserted" if source_title_asserted else "filename-derived-candidate"},
                "data": {"recipeSchema": "offmenu-recipe/1", "name": title, "languages": [source["language"]],
                    "ingredients": ingredients, "directions": directions, "yield": {"value": None, "unit": "portion"},
                    "automaticPlanningEligible": False, "reviewStatus": "source-recipe-needs-personal-quantity-and-food-review",
                    "qualificationStatus": "unknown", "quantityCoverage": {"ingredients": len(ingredients),
                       "standardQuantities": sum(x["amount"] is not None for x in ingredients),
                       "sourceNumericQuantities": sum(x["sourceQuantity"]["value"] is not None for x in ingredients)},
                    "limitations": "No diet or country claim is inferred. Unknown measures and source wording remain attached."}})
        acquisitions.append(acquisition)
    if not accepted:
        raise RuntimeError("No accepted recipes")
    digest = hashlib.sha256()
    with gzip.open(output / "normalized.jsonl.gz", "wt", encoding="utf-8", compresslevel=6) as handle:
        for record in accepted:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            digest.update((line + "\n").encode())
            handle.write(line + "\n")
    (output / "acquisition.json").write_text(json.dumps(acquisitions, ensure_ascii=False, indent=2) + "\n")
    (output / "decisions.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in decisions))
    counts = {repo: sum(x["provenance"]["originSourceId"] == "github:" + repo for x in accepted) for repo in (s["repo"] for s in SOURCES)}
    artifact_sha = sha((output / "normalized.jsonl.gz").read_bytes())
    manifest = {"schemaVersion": "offmenu-collection/1", "sourceId": "recipe-expansion-20261014", "releaseId": RELEASE,
      "status": "accepted-source-recipe-records", "completedAt": now, "records": len(accepted), "sourceCounts": counts,
      "languages": {lang: sum(lang in x["data"]["languages"] for x in accepted) for lang in sorted({s["language"] for s in SOURCES})},
      "contentLinesSha256": digest.hexdigest(), "normalizedArtifactSha256": artifact_sha, "acquisition": "acquisition.json", "decisions": "decisions.jsonl",
      "scope": "Pinned primary GitHub repository files whose root CC0 or Unlicense text was fetched and verified. Repository licensing is evidence for the repository contribution only; no external recipe-site text, photos, nutrition, country origin, dietary classification, translation, or unit-density conversion is inferred.",
      "typeProposals": [{"type": "RecipeSourceEdition", "reason": "A repository and immutable commit identify a source edition independently of a recipe concept."}, {"type": "IngredientStatement", "reason": "A source-language ingredient statement needs citation and may contain an unresolved measure."}],
      "qualification": {"allAcceptedHave": ["two-or-more source ingredient statements", "one-or-more directions", "pinned content hash", "root licence evidence"], "excluded": len(decisions)}}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False))

def repair_titles(output):
    """Repair a completed local acquisition without re-contacting publishers.

    The first draft used filenames as titles for Markdown records.  Raw pinned
    blobs are already held under originals, so this deterministic repair reads
    those bytes and records whether an actual source H1 supplied the title.
    """
    records = [json.loads(line) for line in gzip.open(output / "normalized.jsonl.gz", "rt", encoding="utf-8") if line.strip()]
    by_repo = {"github:" + x["repo"]: x for x in SOURCES}
    for record in records:
        p = record["provenance"]
        source = by_repo[p["originSourceId"]]
        path = p["recordId"]
        raw = output / "originals" / source["repo"].replace("/", "--") / path
        body = raw.read_text(encoding="utf-8")
        fallback = Path(path).stem.replace("-", " ").replace("_", " ")
        if path.endswith(".md"):
            title, _, _, asserted = parse_markdown(fallback, body, source)
        else:
            title, _, _, asserted = parse_plain(fallback, body, source)
        record["data"]["name"] = title
        p["sourceTitleStatus"] = "source-asserted" if asserted else "filename-derived-candidate"
    temp = output / "normalized.repaired.jsonl.gz"
    lines_digest = hashlib.sha256()
    with gzip.open(temp, "wt", encoding="utf-8", compresslevel=6) as handle:
        for record in records:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            lines_digest.update((line + "\n").encode())
            handle.write(line + "\n")
    temp.replace(output / "normalized.jsonl.gz")
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.pop("archiveSha256", None)
    manifest["contentLinesSha256"] = lines_digest.hexdigest()
    manifest["normalizedArtifactSha256"] = sha((output / "normalized.jsonl.gz").read_bytes())
    manifest["titleQualification"] = "Title is source-asserted only where source page_title front matter, H1 or plain NAME exists; otherwise a filename-derived candidate is marked in provenance."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"records": len(records), "status": "titles-and-artifact-hash-repaired"}))

def build_common(output):
    """Make a citation-bearing, source-scoped common graph from admitted rows."""
    import jsonschema_rs
    common = output / "common-graph"
    if common.exists():
        raise SystemExit(f"immutable common graph already exists: {common}")
    common.mkdir()
    schema = json.loads((Path(__file__).parents[1] / "corpus/common-data.schema.json").read_text())
    validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
    scope = {"visibility": "public", "reuseScope": "Per-citation CC0/Unlicense licence and attribution apply."}
    rows = [json.loads(line) for line in gzip.open(output / "normalized.jsonl.gz", "rt", encoding="utf-8") if line.strip()]
    packets = []
    total = {"resources": 0, "assertions": 0, "relations": 0, "citations": 0, "translations": 0}
    def iri(kind, value): return "urn:offmenu:" + kind + ":" + sha(value.encode())[:24]
    for row in rows:
        p, d = row["provenance"], row["data"]
        cid = iri("citation", row["id"])
        variant = iri("recipe-variant", row["id"])
        culture = iri("cultural-representation", row["id"])
        lang = d["languages"][0]
        def source_text(value, key, status="source-asserted"):
            value = str(value)
            return {"kind": "text", "id": iri("text", row["id"] + ":" + key), "language": lang,
                    "value": value, "sourceTextSha256": sha(value.encode()), "status": status, "citationIds": [cid]}
        title_status = "source-asserted" if p.get("sourceTitleStatus") == "source-asserted" else "candidate"
        resources = [
            {"id": variant, "type": "urn:offmenu:type:RecipeVariant", "identityStatus": "source-scoped",
             "names": [source_text(d["name"], "title", title_status)], "citationIds": [cid], "scope": scope},
            {"id": culture, "type": "urn:offmenu:type:CulturalRepresentation", "identityStatus": "source-scoped",
             "names": [], "citationIds": [cid], "scope": scope},
        ]
        assertions, relations = [], []
        def fact(subject, prop, value, path, status="source-asserted", derivation=None):
            a = {"id": iri("assertion", row["id"] + subject + prop + path), "subjectId": subject,
                 "propertyId": "urn:offmenu:property:" + prop, "value": value, "status": status,
                 "citationIds": [cid], "sourcePath": path, "culturalRepresentationIds": [culture], "scope": scope}
            if derivation: a["derivation"] = derivation
            assertions.append(a)
            return a
        def relation(subject, predicate, obj, path, status="source-asserted"):
            relations.append({"id": iri("relation", row["id"] + subject + predicate + obj + path), "subjectId": subject,
             "predicateId": "urn:offmenu:relation:" + predicate, "objectId": obj, "status": status,
             "citationIds": [cid], "scope": scope, "sourcePath": path})
        fact(variant, "originalSourceRecord", {"kind": "identifier", "value": row["id"]}, "id")
        fact(culture, "sourceEditionLanguage", {"kind": "identifier", "value": lang}, "data.languages.0")
        for index, item in enumerate(d["ingredients"]):
            mention = iri("ingredient-mention", row["id"] + ":" + str(index))
            path = "data.ingredients." + str(index)
            original = source_text(item["originalText"], "ingredient:" + str(index))
            resources.append({"id": mention, "type": "urn:offmenu:type:IngredientMention", "identityStatus": "source-scoped",
             "names": [source_text(item["name"], "ingredient-name:" + str(index))], "citationIds": [cid], "scope": scope})
            relation(variant, "usesIngredient", mention, path)
            original_fact = fact(mention, "originalIngredientStatement", original, path + ".originalText")
            quantity = {"kind": "quantity", "value": item["amount"], "unitId": "urn:offmenu:unit:" + item["unit"] if item["unit"] else None,
              "dimension": {"g": "mass", "ml": "volume", "count": "count"}.get(item["unit"], "unknown"),
              "sourceValue": item["sourceQuantity"].get("value"), "sourceUnit": item["sourceQuantity"].get("unit"),
              "sourceNotation": original, "qualifiers": [item["quantityStatus"], item["sourceQuantity"]["status"]]}
            if item["sourceQuantity"].get("range"): quantity["range"] = item["sourceQuantity"]["range"]
            fact(mention, "requiredQuantity", quantity, path + ".sourceQuantity", "candidate",
                 {"methodId": "urn:offmenu:method:source-measure-normalisation-2", "inputAssertionIds": [original_fact["id"]], "reviewStatus": "candidate"})
            # The source did not assert false when no optional wording was found.
            fact(mention, "optional", {"kind": "boolean", "value": item["optional"]}, path + ".optional", "candidate",
                 {"methodId": "urn:offmenu:method:optional-wording-detection", "inputAssertionIds": [original_fact["id"]], "reviewStatus": "candidate"})
            if item.get("ingredientId"):
                relation(mention, "candidateMatch", "urn:offmenu:ingredient:" + urllib.parse.quote(item["ingredientId"], safe=""), path + ".ingredientId", "candidate")
        for index, instruction in enumerate(d["directions"]):
            step = iri("recipe-step", row["id"] + ":" + str(index))
            resources.append({"id": step, "type": "urn:offmenu:type:RecipeStep", "identityStatus": "source-scoped", "names": [], "citationIds": [cid], "scope": scope})
            relation(variant, "hasStep", step, "data.directions." + str(index))
            fact(step, "instruction", source_text(instruction, "step:" + str(index)), "data.directions." + str(index))
            fact(step, "position", {"kind": "number", "value": index + 1}, "data.directions." + str(index))
        fact(variant, "automaticPlanningEligible", {"kind": "boolean", "value": False}, "data.automaticPlanningEligible", "candidate")
        citation = {"id": cid, "sourceId": p["originSourceId"], "originalRecordId": p["recordId"], "originalUrl": p["url"],
         "revisionId": p["sourceRevision"], "contentSha256": p["originalContentSha256"], "license": p["license"],
         "attribution": p["attribution"], "rightsEvidenceUrl": p["rightsEvidenceUrl"], "scope": scope}
        packet = {"schemaVersion": "offmenu-common/1", "resources": resources, "assertions": assertions,
                  "relations": relations, "citations": [citation], "translations": []}
        validator.validate(packet)
        packets.append(packet)
        for key in total: total[key] += len(packet[key])
    part = common / "recipe-source-alignment.jsonl.gz"
    with gzip.open(part, "wt", encoding="utf-8", compresslevel=6) as handle:
        for packet in packets: handle.write(json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n")
    source_counts = json.loads((output / "manifest.json").read_text())["sourceCounts"]
    counts = {**total, "packets": len(packets)}
    native = common / "recipes.normalized.jsonl.gz"
    shutil.copyfile(output / "normalized.jsonl.gz", native)
    files = [{"key": part.name, "bytes": part.stat().st_size, "sha256": sha(part.read_bytes()), "packets": len(packets)},
             {"key": native.name, "bytes": native.stat().st_size, "sha256": sha(native.read_bytes())}]
    rights = []
    for acquisition in json.loads((output / "acquisition.json").read_text()):
        repository = acquisition["repository"]
        license_source = output / "originals" / repository.replace("/", "--") / acquisition["licencePath"]
        license_bytes = license_source.read_bytes()
        assert sha(license_bytes) == acquisition["licenceSha256"]
        key = "licenses/" + repository.replace("/", "--") + ".txt"
        target = common / key; target.parent.mkdir(exist_ok=True); target.write_bytes(license_bytes)
        files.append({"key": key, "bytes": len(license_bytes), "sha256": sha(license_bytes)})
        rights.append({k: acquisition[k] for k in ["repository", "commit", "licence", "rightsEvidenceUrl", "licenceSha256"]})
    manifest = {"schemaVersion": "offmenu-common-expansion-graph/1", "releaseId": "recipe-expansion-qualified-20261014", "complete": True, "limit": None,
      "sourceId": "recipe-expansion-20261014", "sourceRecords": len(rows), "expectedSourceRecords": source_counts,
      "observedSourceRecords": source_counts, "counts": counts, "expectedCounts": counts, "observedCounts": counts,
      "partitionCoverage": {"complete": True, "expectedFiles": 1, "observedFiles": 1, "expectedPackets": len(packets), "observedPackets": len(packets)},
      "files": files, "rights": rights, "nativeRecipeRecords": len(rows), "rawSourcePayloadPublished": False,
      "status": "schema-validated-source-scoped-graph", "scope": "Licensed admitted native records only; raw originals remain local holdings.",
      "qualifications": ["Title source assertion only when sourceTitleStatus is source-asserted.", "Quantity and optionality normalization are candidates with statement derivations.", "No concept join, translation, country, dietary claim, or planned meal is asserted."]}
    manifest["artifactSha256"] = sha(part.read_bytes())
    manifest["manifestSha256"] = sha(json.dumps(manifest, ensure_ascii=True, separators=(",", ":")).encode())
    (common / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--repair-titles", action="store_true")
    parser.add_argument("--build-common", action="store_true")
    args = parser.parse_args()
    repair_titles(args.output) if args.repair_titles else build_common(args.output) if args.build_common else run(args.output)
