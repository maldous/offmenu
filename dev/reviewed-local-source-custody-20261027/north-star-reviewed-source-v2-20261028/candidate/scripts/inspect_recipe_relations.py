#!/usr/bin/env python3
"""Finite SQL-backed consumer diagnostics for selected normalized recipe assets.

No text matching, culinary identity decision, source admission or remote lookup.
This preserves originals and stores the query index only in a disjoint local
derived directory. Only aggregate results/hashes may leave the confined host.
"""
import argparse
import collections
import gzip
import hashlib
import io
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote
from inspect_north_star_sample import selected_file, sha


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def inspect(package, manifest_sha, schema_package, output, asset_prefix=None, existing_index=None):
    manifest_bytes = (package / "manifest.json").read_bytes()
    if sha(manifest_bytes) != manifest_sha:
        raise ValueError("manifest bytes differ")
    manifest = json.loads(manifest_bytes)
    schema = (schema_package / "schema.json").read_bytes()
    if sha(schema) != "89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c":
        raise ValueError("selected package schema differs")
    try:
        import jsonschema_rs
        validator = jsonschema_rs.Draft202012Validator(json.loads(schema), validate_formats=True)
        validator_engine = 'jsonschema_rs'
    except ImportError:
        import jsonschema
        validator = jsonschema.Draft202012Validator(json.loads(schema), format_checker=jsonschema.FormatChecker())
        validator_engine = 'jsonschema'
    if asset_prefix not in {None,'recipes/'}:raise ValueError('unsupported asset selection')
    files = [f for f in manifest["files"] if f["key"].endswith(".jsonl.gz") and "packets" in f]
    if asset_prefix:files=[f for f in files if f['key'].startswith(asset_prefix)]
    if not files: raise ValueError("no manifest-declared normalized packet assets")
    if output.exists(): raise ValueError("immutable output exists")
    output.mkdir(parents=True)
    db_path = existing_index if existing_index is not None else output / "relation-query-index.sqlite"
    original_index_sha=file_sha(db_path) if existing_index is not None else None
    db = sqlite3.connect('file:'+quote(str(db_path.resolve()),safe='/')+'?mode=ro&immutable=1',uri=True) if existing_index is not None else sqlite3.connect(db_path)
    db.execute('PRAGMA cache_size=-32768')
    # Bound this index below the caller's 2GiB total-output reservation, leaving
    # room for the largest selected-asset transaction journal and report.
    if existing_index is None:
        db.execute('PRAGMA max_page_count=491520')
        db.executescript("""
    CREATE TABLE resources(id TEXT PRIMARY KEY, type TEXT NOT NULL, identity_status TEXT NOT NULL, scope TEXT NOT NULL);
    CREATE TABLE relations(id TEXT PRIMARY KEY, subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL, status TEXT NOT NULL, source_path TEXT NOT NULL, evidence_sha256 TEXT NOT NULL, scope TEXT NOT NULL);
    CREATE TABLE facts(id TEXT PRIMARY KEY, subject TEXT NOT NULL, property TEXT NOT NULL, status TEXT NOT NULL, numeric_value REAL, value_kind TEXT NOT NULL, boolean_value INTEGER, unit TEXT, scope TEXT NOT NULL, evidence_sha256 TEXT NOT NULL);
    CREATE INDEX edge_subject ON relations(subject,predicate,status);
    CREATE INDEX fact_subject ON facts(subject,property,status);
    """)
    else:db.execute('PRAGMA query_only=ON')
    projected=collections.Counter(resources=0,relations=0,facts=0)
    def index_row(table,values):
        projected[table]+=1
        if existing_index is None:
            db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in values)+')',values)
        elif db.execute('SELECT * FROM '+table+' WHERE id=?',(values[0],)).fetchone()!=tuple(values):
            raise ValueError('existing index projection differs from exact selected input')
    types = collections.Counter(); predicates = collections.Counter(); statuses = collections.Counter(); packets = 0
    for entry in files:
        observed = 0
        b = selected_file(package, entry)
        with gzip.GzipFile(fileobj=io.BytesIO(b)) as stream:
            for line in stream:
                packet = json.loads(line); validator.validate(packet); observed += 1; packets += 1
                citation_map = {c["id"]: c for c in packet["citations"]}
                for key in ("resources", "assertions", "relations"):
                    for row in packet[key]:
                        if any(c not in citation_map for c in row["citationIds"]): raise ValueError("unresolved citation")
                        if row["scope"].get("visibility") != "public": raise ValueError("not selected public-normalized scope")
                        if not row["citationIds"] or any(citation_map[c]["scope"] != row["scope"] for c in row["citationIds"]):
                            raise ValueError("citation scope differs from selected row")
                for r in packet["resources"]:
                    index_row('resources',(r["id"],r["type"],r["identityStatus"],json.dumps(r["scope"],sort_keys=True)))
                    types[r["type"]] += 1
                for r in packet["relations"]:
                    index_row('relations',(r["id"],r["subjectId"],r["predicateId"],r["objectId"],r["status"],r["sourcePath"],sha(json.dumps([r,[citation_map[c] for c in r["citationIds"]]],sort_keys=True).encode()),json.dumps(r["scope"],sort_keys=True)))
                    predicates[r["predicateId"]] += 1
                for a in packet["assertions"]:
                    v = a["value"]; number = v.get("value") if v.get("kind") in {"quantity","number"} and type(v.get("value")) in {int,float} else None
                    boolean = int(v["value"]) if v.get("kind") == "boolean" else None
                    index_row('facts',(a["id"],a["subjectId"],a["propertyId"],a["status"],number,v["kind"],boolean,v.get("unitId"),json.dumps(a["scope"],sort_keys=True),sha(json.dumps([a,[citation_map[c] for c in a["citationIds"]]],sort_keys=True).encode())))
                    statuses[a["status"]] += 1
        if observed != entry["packets"]: raise ValueError("asset packet reconciliation")
        db.commit()
    db.commit()
    if any(db.execute('SELECT count(*) FROM '+table).fetchone()[0]!=count for table,count in projected.items()):
        raise ValueError('existing index extent differs from selected input')
    R="urn:offmenu:relation:";P="urn:offmenu:property:";T="urn:offmenu:type:"
    queries = {
        "recipeVariants": ("SELECT count(*) FROM resources WHERE type=?",[T+"RecipeVariant"]),
        "ingredientMentions": ("SELECT count(*) FROM resources WHERE type=?",[T+"IngredientMention"]),
        "recipeIngredientMentionsResolved": ("SELECT count(*) FROM relations e JOIN resources r ON r.id=e.subject JOIN resources i ON i.id=e.object WHERE e.predicate=? AND r.type=? AND i.type=? AND r.scope=i.scope AND e.scope=r.scope AND e.status NOT IN ('superseded','conflicting','needs-transcription','unknown')",[R+"usesIngredient",T+"RecipeVariant",T+"IngredientMention"]),
        "ingredientQuantityJoins": ("SELECT count(*) FROM relations e JOIN resources r ON r.id=e.subject JOIN resources i ON i.id=e.object JOIN facts q ON q.subject=i.id WHERE e.predicate=? AND r.type=? AND i.type=? AND q.property=? AND q.value_kind='quantity' AND e.scope=r.scope AND r.scope=i.scope AND i.scope=q.scope AND e.status NOT IN ('superseded','conflicting','needs-transcription','unknown') AND q.status NOT IN ('superseded','conflicting','needs-transcription')",[R+"usesIngredient",T+"RecipeVariant",T+"IngredientMention",P+"requiredQuantity"]),
        "ingredientUnknownQuantities": ("SELECT count(*) FROM facts WHERE property=? AND value_kind='quantity' AND numeric_value IS NULL",[P+"requiredQuantity"]),
        "ingredientZeroQuantities": ("SELECT count(*) FROM facts WHERE property=? AND value_kind='quantity' AND numeric_value=0",[P+"requiredQuantity"]),
        "sourceRecipeStepJoins": ("SELECT count(*) FROM relations e JOIN resources r ON r.id=e.subject JOIN resources s ON s.id=e.object WHERE e.predicate=? AND r.type=? AND s.type=? AND e.scope=r.scope AND r.scope=s.scope AND e.status NOT IN ('superseded','conflicting','needs-transcription','unknown')",[R+"hasStep",T+"RecipeVariant",T+"RecipeStep"]),
        "stepIngredientJoins": ("SELECT count(*) FROM relations e JOIN resources s ON s.id=e.subject JOIN resources i ON i.id=e.object WHERE e.predicate=? AND s.type=? AND i.type=? AND e.scope=s.scope AND s.scope=i.scope AND e.status NOT IN ('superseded','conflicting','needs-transcription','unknown')",[R+"usesIngredient",T+"RecipeStep",T+"IngredientMention"]),
        "ingredientIdentityCandidates": ("SELECT count(*) FROM relations WHERE predicate=? AND status='candidate'",[R+"candidateMatch"]),
        "reviewedExactIngredientIdentityLinks": ("SELECT count(*) FROM relations e JOIN resources s ON s.id=e.subject WHERE e.predicate=? AND e.status IN ('reviewed','verified') AND s.type=?",[R+"exactMatch",T+"IngredientMention"]),
        "knownSourceYieldAssertions": ("SELECT count(*) FROM facts WHERE property=? AND value_kind='quantity' AND numeric_value>0",[P+"yield"]),
        "automaticPlanningEligibleTrueAssertions": ("SELECT count(*) FROM facts WHERE property=? AND boolean_value=1",[P+"automaticPlanningEligible"]),
        "automaticPlanningEligibleFalseAssertions": ("SELECT count(*) FROM facts WHERE property=? AND boolean_value=0",[P+"automaticPlanningEligible"]),
        "recipeNutrientObservationEdges": ("SELECT count(*) FROM relations e JOIN resources s ON s.id=e.subject WHERE e.predicate=? AND s.type=?",[R+"hasNutrientObservation",T+"RecipeVariant"]),
    }
    results = {name:{"sql":sql,"parameters":params,"count":db.execute(sql,params).fetchone()[0]} for name,(sql,params) in queries.items()}
    db.close()
    if original_index_sha is not None and file_sha(db_path)!=original_index_sha:raise ValueError('read-only input index changed')
    result = {"schemaVersion":"offmenu-north-star-recipe-consumer-exercise/1","status":"selected-normalized-package-queries-exercised",
              "manifestByteSha256":manifest_sha,"releaseId":manifest.get("releaseId"),"selectedAssets":files,
              "packetsSchemaValidated":packets,"assetPrefix":asset_prefix,"validatorEngine":validator_engine,"resourceTypes":dict(types),"predicateCounts":dict(predicates),"assertionStatuses":dict(statuses),
              "rowCitationScopesVerified":True,
              "queries":results,"queryIndexSha256":file_sha(db_path),"queryIndexBytes":db_path.stat().st_size,
              "queryIndexMode":"exact-source-reverified-read-only-existing" if existing_index is not None else "new-projection",
              "selectedSchemaSha256":sha(schema),"sourceCodeSha256":sha(Path(__file__).read_bytes()),
              "fullNorthStarComplete":False,"servedAppQueriesExercised":0,"identityAdmissionGranted":False,
              "originalsModified":False,"limits":"Counts apply only to selected manifest-listed common/1 recipe assets. SQL joins preserve asserted/candidate statuses; missing edges are not synthesized. No live app or nutritional/culinary qualification claimed."}
    (output/'report.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({"status":result['status'],"packets":packets,"queries":{k:v['count'] for k,v in results.items()}}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('manifest_sha');p.add_argument('schema_package',type=Path);p.add_argument('output',type=Path);p.add_argument('--asset-prefix',choices=['recipes/']);p.add_argument('--existing-index',type=Path);a=p.parse_args();inspect(a.package,a.manifest_sha,a.schema_package,a.output,a.asset_prefix,a.existing_index)
