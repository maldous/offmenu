import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import survey
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('survey_dispatch',ROOT/'scripts/dispatch-foo-job.py')
jobs=importlib.util.module_from_spec(spec);spec.loader.exec_module(jobs)


def fixture_report():
    countries={}
    for country in survey.COUNTRIES:
        folder='norway' if country=='NO' else 'ciqual'
        blobs={survey.ASSETS[key][0].split('/')[-1]:(ROOT/'tests/fixtures'/folder/survey.ASSETS[key][0].split('/')[-1]).read_bytes() for key in survey.COUNTRIES[country]['raw']}
        mod=survey._module(country)
        result=mod.sanitize_report(mod.survey(blobs))
        countries[country]={'country':country,'sourceId':survey.COUNTRIES[country]['sourceId'],'releaseId':survey.COUNTRIES[country]['releaseId'],'status':result['status'],'inputPinsVerified':True,'readOnlyViewVerified':True,'sourceBodiesSubmitted':len(blobs),'errorCode':None,'survey':result}
    value={'schemaVersion':survey.SCHEMA,'operationId':'a'*32,'status':'held' if any(x['status']=='held' for x in countries.values()) else 'surveyed','surveyComplete':all(x['survey']['evidenceComplete'] for x in countries.values()),'codeFingerprint':'b'*64,'selectionSha256':survey.sha(survey.canonical(survey.ASSETS)),'inputPins':survey.input_lock(),'runtime':survey.runtime(),'boundaries':dict(survey.BOUNDARIES),'countries':countries}
    return survey.sanitize_report(value)


class FooSurveyTests(unittest.TestCase):
    def test_profile_is_fixed_and_has_no_dataset_global_gate_or_normalizer(self):
        request={'schemaVersion':1,'jobId':'schema-survey-test-001','profile':'national-schema-survey'}
        self.assertEqual(jobs.parse_request(json.dumps(request).encode()),request)
        steps=jobs.profile_steps('national-schema-survey',ROOT)
        self.assertEqual([x[0] for x in steps],['readiness','schema-survey-tests','schema-survey'])
        self.assertEqual(steps[2][1],['readiness','schema-survey-tests'])
        self.assertIn('survey-selected',steps[2][2])
        self.assertNotIn('replay',str(steps))
        self.assertNotIn('--input-root',str(steps))

    def test_combined_fixture_survey_and_closed_export_keeps_dictionary_labels(self):
        report=fixture_report()
        self.assertTrue(report['surveyComplete'])
        safe=jobs.safe_evidence(survey.canonical(report))
        self.assertEqual(safe['schemaSurvey'],report)
        self.assertIn('Energy (kcal/100g)',json.dumps(safe,ensure_ascii=False))
        self.assertLess(len(survey.canonical(report)),jobs.MAX_SURVEY_EVIDENCE)
        changed=copy.deepcopy(report);changed['countries']['FR']['survey']['foodName']='private food'
        clean=jobs.safe_evidence(survey.canonical(changed))
        self.assertNotIn('schemaSurvey',clean)
        self.assertNotIn('private food',json.dumps(clean))

    def test_cli_completeness_and_dispatch_profile_outcome(self):
        from offmenu.refresh.__main__ import main
        report=fixture_report()
        with patch.object(survey,'survey_selected',return_value=report), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['survey-selected','--workspace','/srv/offmenu-refresh/outputs/schema-surveys']),0)
        self.assertEqual(json.loads(out.getvalue()),report)
        result={'status':'passed','exitCode':0,'durationSeconds':0.1,'evidence':{'schemaSurvey':report}}
        with patch.object(jobs,'run_child',return_value=result):
            self.assertEqual(jobs.run_step('schema-survey',[],ROOT)['status'],'passed')
        held={'status':'failed','exitCode':2,'durationSeconds':0.1,'evidence':{'schemaSurvey':{'status':'held','surveyComplete':False}}}
        with patch.object(jobs,'run_child',return_value=held):
            self.assertEqual(jobs.run_step('schema-survey',[],ROOT)['status'],'blocked')
        invalid={'status':'passed','exitCode':0,'durationSeconds':0.1,'evidence':{}}
        with patch.object(jobs,'run_child',return_value=invalid):
            self.assertEqual(jobs.run_step('schema-survey',[],ROOT)['status'],'failed')

    def test_large_report_cap_is_fixed_profile_only(self):
        value={'profile':'national-schema-survey','test':'x'*(40*1024)}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'survey.json';jobs.atomic_json(p,value)
            self.assertGreater(p.stat().st_size,jobs.MAX_REPORT)
            value['profile']='smoke'
            with self.assertRaises(jobs.JobError):jobs.atomic_json(Path(tmp)/'smoke.json',value)
        self.assertEqual(jobs.report_limit({'profile':'anything-else'}),32768)

    def test_survey_holds_do_not_claim_acceptance_or_source_complete(self):
        def child(command,code,timeout=240):
            if 'survey-selected' in command:
                return {'status':'failed','exitCode':2,'durationSeconds':0,'evidence':{'schemaSurvey':{'status':'held','surveyComplete':False}}}
            return {'status':'passed','exitCode':0,'durationSeconds':0,'evidence':{}}
        request={'schemaVersion':1,'jobId':'schema-survey-test-002','profile':'national-schema-survey'}
        with patch.object(jobs,'run_child',side_effect=child):
            report=jobs.run_profile(request,'a'*40,ROOT,'1','1')
        self.assertEqual(report['status'],'incomplete')
        self.assertFalse(report['candidateGenerationEnabled'])
        self.assertFalse(report['corpusAcceptanceEstablished'])
        self.assertTrue(report['structuralDictionaryLabelsIncluded'])


if __name__=='__main__':unittest.main()
