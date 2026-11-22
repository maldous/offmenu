"""Generated records only. No corpus, network, real profile, or runtime fixtures."""
import copy
import hashlib
import json
import unittest

from offmenu.retained_context_consumers import CODEC, PROVIDERS, RefusedContext, consume_context


def digest(c):
    return hashlib.sha256(c.encode()).hexdigest()


def make(provider="off", en="Test Food", name="Test Food", co=114):
    release, rights = PROVIDERS[provider]
    b = dict(provider=provider, release=release, rights_sha256=rights,
             queue=digest("fake queue"), shard=f"cohort-{co:03d}/chunk-00001", row_ordinal=7,
             assignment_sha256=digest("fake assignment"), parser_sha256=digest("fake parser"),
             stage_wire_sha256=digest("fake stage"), shard_sha256=digest("fake compressed"),
             input_database_sha256=digest("fake source"), stage_record_id="offmenu:product:"+"a"*24)
    sb = dict(sourceId=provider,releaseId=release,recordId="00123",nativeRecordId=provider+":product:00123",
              sourceObservationSha256=digest("obs"),sourceDocumentSha256=digest("doc"),
              inputDatabaseSha256=b["input_database_sha256"],sourceQualificationSha256=rights)
    a = dict(sourceBinding=copy.deepcopy(sb),sourceProductContext={
        "schema":"offmenu-source-product-context/1","sourceEvidence":copy.deepcopy(sb),"fields":{}})
    row = dict(stageRecordId=b["stage_record_id"],stageRecordWireSha256=b["stage_wire_sha256"],
               sourceBinding=sb,sourceAdapterInput=a,sourceRights={"visibility":"source-staging",
               "license":"Fixture terms", "attribution":"Synthetic publisher"},
               retainedSource={"cohort":co,"recordShard":b["shard"],"compressedShardSha256":b["shard_sha256"]},
               literalProjectedFields={},identifiers=[{"system":"barcode","value":"0012345678905"}])
    def field(role, key, value):
        raw=json.dumps(value,ensure_ascii=False,separators=(",",":")).encode()
        cell=dict(state="null" if value is None else "empty" if value in ("",{}) else "present",
                  originalValue=copy.deepcopy(value),sourcePointer=("/data/" if provider=="off" else "/0/data/")+key,
                  projectedValueCommitmentVerified=True,valueSha256=hashlib.sha256(raw).hexdigest(),evidenceBytes=len(raw),evidenceEncoding=CODEC)
        a["sourceProductContext"]["fields"][role]=cell
        row["literalProjectedFields"][key]=copy.deepcopy(value)
    field("name","name",name)
    if provider=="off":
        field("names","names",{"en":en,"ar":"اختبار"} if en is not None else {"ar":"اختبار"})
    else:
        field("ingredientDeclaration","ingredientsText","   1/2  OZ   +  ٢  g ")
        field("dataType","dataType","Test category")
    return row,b


class ConsumerTest(unittest.TestCase):
    def test_off_publisher_language_not_machine_translation(self):
        r,b=make(); old=copy.deepcopy(r)
        res=consume_context("off",r,binding=b)
        self.assertEqual(res["selectedEnglishName"],"Test Food")
        self.assertEqual(res["selectedPointer"],"/data/names/en")
        self.assertEqual(res["disposition"],"exact-source-agreement")
        self.assertFalse(res["translationPerformed"])
        self.assertFalse(res["goldAdmitted"])
        self.assertEqual(old,r)
        self.assertEqual(res["sourceBinding"]["recordId"],"00123")
        self.assertEqual(res["sourceRights"],r["sourceRights"])
        res["fields"]["names"]["originalValue"]["en"]="mutated"
        self.assertEqual(old,r)
        self.assertEqual(consume_context("off",r,binding=b)["selectedEnglishName"],"Test Food")

    def test_exact_language_selection_states(self):
        for en,name,expected in ((None,"English-looking","english-field-unknown"),
            ("Test Food","OTHER","source-fields-disagree"),("Test Food",None,"english-field-present-generic-name-unknown"),
            ("","English-looking","english-field-unknown")):
            with self.subTest(expected=expected):
                r,b=make(en=en,name=name)
                result=consume_context("off",r,binding=b)
                self.assertEqual(result["disposition"],expected)
                self.assertEqual(result["selectedEnglishName"],en or None)

    def test_usda_lexical_only_keeps_original_numerals_and_unknown_semantics(self):
        r,b=make("usda-files",name="CAFE\u0301   No 1.20",co=112)
        o=consume_context("usda-files",r,binding=b)
        self.assertEqual(o["fields"]["name"]["normalizedLexicalValue"],"café no 1.20")
        self.assertEqual(o["fields"]["name"]["originalValue"],"CAFE\u0301   No 1.20")
        self.assertEqual(o["fields"]["ingredientDeclaration"]["normalizedLexicalValue"],"1/2 oz + ٢ g")
        self.assertIsNone(o["fields"]["dataType"]["normalizedLexicalValue"])
        self.assertEqual(o["semanticResolution"]["status"],"unresolved")
        self.assertFalse(o["languageInferred"])
        self.assertFalse(o["normalizationComplete"])

    def test_unknown_empty_and_null_are_distinct_from_zero(self):
        for n,state in ((None,"null"),("","empty"),("0","present")):
            r,b=make("usda-files",name=n)
            self.assertEqual(consume_context("usda-files",r,binding=b)["fields"]["name"]["state"],state)
        r,b=make("usda-files",name=None)
        cell=r["sourceAdapterInput"]["sourceProductContext"]["fields"]["name"]
        cell.update(state="unknown",evidenceBytes=None,valueSha256=None,projectedValueCommitmentVerified=False)
        o=consume_context("usda-files",r,binding=b)
        self.assertEqual(o["fields"]["name"]["state"],"unknown")
        self.assertIsNone(o["fields"]["name"]["normalizedLexicalValue"])

    def test_no_runtime_data_grants_or_language_fallback(self):
        r,b=make(en=None)
        r["callerSemanticApproval"]={"accepted":True,"value":"invented"}
        o=consume_context("off",r,binding=b)
        self.assertFalse(o["goldAdmitted"])
        self.assertIsNone(o["selectedEnglishName"])
        self.assertNotIn("callerSemanticApproval",o)

    def test_exact_field_wire_uses_source_order_not_sorted_alternative(self):
        r,b=make()
        names=r["sourceAdapterInput"]["sourceProductContext"]["fields"]["names"]
        self.assertEqual(list(names["originalValue"]),["en","ar"])
        o=consume_context("off",r,binding=b)
        self.assertEqual(o["fieldOrigins"]["/selectedEnglishName"]["inputValueSha256"],names["valueSha256"])
        self.assertEqual(o["fieldOrigins"]["/selectedEnglishName"]["memberPointer"],"/en")
        names["originalValue"]=dict(sorted(names["originalValue"].items()))
        with self.assertRaises(RefusedContext):consume_context("off",r,binding=b)
        for misflag in (False,None,1):
            r,b=make()
            r["sourceAdapterInput"]["sourceProductContext"]["fields"]["names"]["projectedValueCommitmentVerified"]=misflag
            with self.assertRaises(RefusedContext):consume_context("off",r,binding=b)

    def test_lexical_output_retains_field_and_transform_pins(self):
        r,b=make("usda-files");o=consume_context("usda-files",r,binding=b)
        f=o["fieldOrigins"]["/fields/ingredientDeclaration/normalizedLexicalValue"]
        self.assertEqual(f["sourcePointer"],"/0/data/ingredientsText")
        self.assertEqual(f["method"],"NFC+casefold+whitespace")
        self.assertEqual(f["policySha256"],b["parser_sha256"])
        self.assertEqual(f["inputValueSha256"],o["fields"]["ingredientDeclaration"]["valueSha256"])

    def test_absent_fields_cannot_pass_unbound_metadata_or_positive_proof(self):
        for key,v in (("sourcePointer","/data/other"),("sourcePointer",{"private":"do not echo"}),
                      ("evidenceEncoding",["other"]),("projectedValueCommitmentVerified",True)):
            r,b=make("usda-files",name=None)
            f=r["sourceAdapterInput"]["sourceProductContext"]["fields"]["name"]
            f.update(state="missing",evidenceBytes=None,valueSha256=None,
                     projectedValueCommitmentVerified=False)
            f[key]=v
            with self.assertRaises(RefusedContext) as err:consume_context("usda-files",r,binding=b)
            self.assertNotIn("do not echo",str(err.exception))

    def test_blank_language_label_retained_but_not_selected(self):
        r,b=make(en="  \t ",name="  \t ")
        o=consume_context("off",r,binding=b)
        self.assertEqual(o["fields"]["names"]["originalValue"]["en"], "  \t ")
        self.assertIsNone(o["selectedEnglishName"])
        self.assertIsNone(o["selectedPointer"])
        self.assertEqual(o["disposition"],"english-field-unknown")

    def test_operation_pins_and_disjoint_queues(self):
        for key,new in (("rights_sha256",digest("wrong")),("input_database_sha256",digest("another")),
            ("queue",None),("shard","../chunk"),("provider","other"),("parser_sha256","no"),("row_ordinal",True),
            ("row_ordinal",-1),("stage_record_id","offmenu:product:"+"b"*24),("shard_sha256",digest("cross")),
            ("stage_wire_sha256",digest("badwire")),("assignment_sha256",""),("release","new version")):
            with self.subTest(key=key):
                r,b=make();b[key]=new
                with self.assertRaises(RefusedContext):consume_context("off",r,binding=b)
        for co in (9,112,114):
            r,b=make(co=co)
            self.assertEqual(consume_context("off",r,binding=b)["operation"]["shard"],b["shard"])

    def test_cross_subject_private_and_wrong_source(self):
        mutations = [
            (["sourceBinding","nativeRecordId"],"off:product:DIFFERENT"),(["memberId"],"no-output"),
            (["sourceRights","rights"],{"rule":{"decision":"denied"}}),
            (["sourceAdapterInput","sourceBinding","sourceObservationSha256"],digest("other")),
            (["sourceRights","visibility"],"private"),(["sourceRights","license"],""),
            (["sourceRights","rights"],{"rules":[{"processingAllowed":False}]}),
            (["sourceAdapterInput","sourceProductContext","sourceEvidence","sourceQualificationSha256"],digest("other")),
            (["sourceAdapterInput","sourceProductContext","stageRecordId"],"wrong"),
            (["retainedSource","recordShard"],"cohort-001/chunk-00001"),
            (["literalProjectedFields","name"],"different"),
            (["sourceAdapterInput","names"],{"en":"unbacked"}),(["schema"],"offmenu-household-domain/1"),
            (["sourceAdapterInput","fieldEvidence"],{"name":{"state":"present","pointer":"/other"}})]
        for path,value in mutations:
            with self.subTest(path=path):
                r,b=make(); node=r
                for k in path[:-1]:node=node[k]
                node[path[-1]]=value
                with self.assertRaises(RefusedContext) as err:consume_context("off",r,binding=b)
                self.assertNotIn("no-output",str(err.exception))

    def test_typed_cells_require_exact_evidence(self):
        for key,value in (("evidenceBytes",True),("valueSha256","a"*64),
                          ("sourcePointer","/data/secret"),("evidenceEncoding","unsupported"),
                          ("state","unknown"),("state","empty"),("originalValue",3)):
            with self.subTest(key=key):
                r,b=make();r["sourceAdapterInput"]["sourceProductContext"]["fields"]["name"][key]=value
                with self.assertRaises(RefusedContext):consume_context("off",r,binding=b)
        r,b=make("usda-files")
        r["sourceAdapterInput"]["sourceProductContext"]["fields"]["name"]["sourcePointer"]="/data/name"
        with self.assertRaises(RefusedContext):consume_context("usda-files",r,binding=b)

    def test_bad_input_fails_closed_without_echo_or_io(self):
        for r in (None,[],{"secret":"PRIVATE_TEST_MARKER"},object()):
            with self.assertRaises(RefusedContext) as err:consume_context("off",r,binding=make()[1])
            self.assertNotIn("PRIVATE_TEST_MARKER",str(err.exception))
        r,b=make()
        r["sourceAdapterInput"]["adapter"]=r
        with self.assertRaises(RefusedContext):consume_context("off",r,binding=b)


if __name__=="__main__":
    unittest.main()
